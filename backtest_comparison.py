import lightgbm as lgb
import numpy as np
import pandas as pd
import os
import glob

# Use absolute path
BASE_DIR = "/home/add/Desktop/Git/qlib_mql5_bot"
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "history_data")
OUTPUT_CSV = os.path.join(BASE_DIR, "backtest_results_summary.csv")

SYMBOL_MAPPING = {
    "DAXEUR": "GER40",
    "NDXUSD": "NAS100",
    "DJIUSD": "US30",
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "XAUUSD": "XAUUSD"
}

def load_local_data(raw_symbol):
    files = [f for f in os.listdir(DATA_DIR) if f.startswith(raw_symbol) and f.endswith(".csv")]
    if not files: return None
    file_path = os.path.join(DATA_DIR, files[0])
    try:
        df = pd.read_csv(file_path, sep='\t')
        df.columns = [col.replace('<', '').replace('>', '').title() for col in df.columns]
        df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        df.set_index('Datetime', inplace=True)
        if 'Tickvol' in df.columns: df.rename(columns={'Tickvol': 'Volume'}, inplace=True)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception: return None

def run_comparison_backtest(raw_symbol, model_name):
    model_path = os.path.join(MODEL_DIR, f"{model_name}_lgbm_model.txt")
    if not os.path.exists(model_path): return None

    model = lgb.Booster(model_file=model_path)
    df = load_local_data(raw_symbol)
    if df is None or len(df) < 500: return None

    df['ema_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['trend_filter'] = (df['Close'] > df['ema_200']).astype(int)
    df['prev_high'] = df['High'].shift(1)
    df['prev_low'] = df['Low'].shift(1)
    df['bullish_sweep'] = ((df['Low'] < df['prev_low']) & (df['Close'] > df['prev_low'])).astype(int)
    df['bearish_sweep'] = ((df['High'] > df['prev_high']) & (df['Close'] < df['prev_high'])).astype(int)
    df['hour_of_day'] = df.index.hour
    
    features = ['Open', 'High', 'Low', 'Close', 'Volume', 'trend_filter', 'bullish_sweep', 'bearish_sweep', 'hour_of_day']
    X = df[features].values
    probs = model.predict(X)
    raw_signals = np.argmax(probs, axis=1)
    confidences = np.max(probs, axis=1)

    CONF_LIMIT = 0.55
    trades_n, trades_p, trades_t = [], [], []

    for i in range(len(df) - 100):
        if confidences[i] < CONF_LIMIT: continue
        raw_sig = raw_signals[i]
        b_sweep = df['bullish_sweep'].iloc[i]
        s_sweep = df['bearish_sweep'].iloc[i]
        entry = df['Close'].iloc[i]
        t_type = None
        if raw_sig == 2 and b_sweep == 1: t_type = "BUY"
        elif raw_sig == 0 and s_sweep == 1: t_type = "SELL"
            
        if t_type:
            sl = df['Low'].iloc[i] - (abs(entry - df['Low'].iloc[i]) * 0.1) if t_type == "BUY" else df['High'].iloc[i] + (abs(df['High'].iloc[i] - entry) * 0.1)
            risk = abs(entry - sl)
            if risk <= 0: continue
            
            # 1. Normal (1:2)
            tp_n = entry + (risk * 2) if t_type == "BUY" else entry - (risk * 2)
            for j in range(i + 1, len(df)):
                h, l = df['High'].iloc[j], df['Low'].iloc[j]
                if (t_type == "BUY" and l <= sl) or (t_type == "SELL" and h >= sl): trades_n.append(-1.0); break
                if (t_type == "BUY" and h >= tp_n) or (t_type == "SELL" and l <= tp_n): trades_n.append(2.0); break

            # 2. PRO (Partial + 1:3)
            tp_part = entry + risk if t_type == "BUY" else entry - risk
            tp_final = entry + (risk * 3) if t_type == "BUY" else entry - (risk * 3)
            p_sl, p_hit = sl, False
            for j in range(i + 1, len(df)):
                h, l = df['High'].iloc[j], df['Low'].iloc[j]
                if not p_hit:
                    if (t_type == "BUY" and l <= p_sl) or (t_type == "SELL" and h >= p_sl): trades_p.append(-1.0); break
                    if (t_type == "BUY" and h >= tp_part) or (t_type == "SELL" and l <= tp_part): p_hit = True; p_sl = entry
                else:
                    if (t_type == "BUY" and l <= entry) or (t_type == "SELL" and h >= entry): trades_p.append(0.5); break
                    if (t_type == "BUY" and h >= tp_final) or (t_type == "SELL" and l <= tp_final): trades_p.append(2.0); break

            # 3. Trailing TSL
            t_sl, t_hit = sl, False
            trail_dist = risk * 1.5
            for j in range(i + 1, len(df)):
                h, l = df['High'].iloc[j], df['Low'].iloc[j]
                if not t_hit:
                    if (t_type == "BUY" and l <= t_sl) or (t_type == "SELL" and h >= t_sl): trades_t.append(-1.0); break
                    if (t_type == "BUY" and h >= tp_part) or (t_type == "SELL" and l <= tp_part): t_hit = True; t_sl = entry
                else:
                    if t_type == "BUY":
                        new_sl = h - trail_dist
                        if new_sl > t_sl: t_sl = new_sl
                        if l <= t_sl: trades_t.append(0.5 + 0.5 * ((t_sl - entry)/risk)); break
                    else:
                        new_sl = l + trail_dist
                        if (new_sl < t_sl or t_sl == entry):
                            if t_sl == entry: t_sl = new_sl
                            elif new_sl < t_sl: t_sl = new_sl
                        if h >= t_sl: trades_t.append(0.5 + 0.5 * ((entry - t_sl)/risk)); break

    def get_stats(trades, strategy_name):
        if not trades: return None
        wins = [t for t in trades if t > 0]
        return {
            "Symbol": model_name,
            "Strategy": strategy_name,
            "Total Trades": len(trades),
            "Win Rate (%)": round(len(wins)/len(trades)*100, 2),
            "Net Return (%)": round(sum(trades), 2)
        }

    return [get_stats(trades_n, "Normal (1:2)"), get_stats(trades_p, "PRO (1:3)"), get_stats(trades_t, "Trailing SL")]

if __name__ == "__main__":
    all_res = []
    for raw, std in SYMBOL_MAPPING.items():
        res = run_comparison_backtest(raw, std)
        if res: all_res.extend([r for r in res if r])
    
    df_results = pd.DataFrame(all_res)
    df_results.to_csv(OUTPUT_CSV, index=False)
    print(f"CSV saved at: {OUTPUT_CSV}")
    print(df_results.to_string(index=False))
