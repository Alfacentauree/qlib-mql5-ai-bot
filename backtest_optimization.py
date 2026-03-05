import lightgbm as lgb
import numpy as np
import pandas as pd
import os
import glob

MODEL_DIR = "/home/add/Desktop/Git/qlib_mql5_bot/models"
DATA_DIR = "/home/add/Desktop/Git/qlib_mql5_bot/history_data"

def load_local_data(symbol):
    search_pattern = os.path.join(DATA_DIR, f"{symbol}*.csv")
    files = glob.glob(search_pattern)
    if not files: return None
    file_path = files[0]
    try:
        df = pd.read_csv(file_path, sep='\t')
        df.columns = [col.replace('<', '').replace('>', '').title() for col in df.columns]
        df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        df.set_index('Datetime', inplace=True)
        if 'Tickvol' in df.columns: df.rename(columns={'Tickvol': 'Volume'}, inplace=True)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception: return None

def run_triple_backtest(symbol):
    model_path = os.path.join(MODEL_DIR, f"{symbol}_lgbm_model.txt")
    if not os.path.exists(model_path): return

    model = lgb.Booster(model_file=model_path)
    df = load_local_data(symbol)
    if df is None or len(df) < 300: return

    # Features
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

    print(f"\n==================================================")
    print(f"   TRIPLE MODE COMPARISON: {symbol}")
    print(f"==================================================")
    
    def simulate_tsl(start_idx, t_type, entry, sl, risk):
        t_sl = sl; partial_hit = False
        tp_partial = entry + risk if t_type == "BUY" else entry - risk
        trailing_dist = risk * 1.5
        for j in range(start_idx + 1, len(df)):
            h, l = df['High'].iloc[j], df['Low'].iloc[j]
            if not partial_hit:
                if (t_type == "BUY" and l <= t_sl) or (t_type == "SELL" and h >= t_sl): return -1.0
                if (t_type == "BUY" and h >= tp_partial) or (t_type == "SELL" and l <= tp_partial):
                    partial_hit = True; t_sl = entry
            else:
                if t_type == "BUY":
                    new_sl = h - trailing_dist
                    if new_sl > t_sl: t_sl = new_sl
                    if l <= t_sl: return (0.5 + 0.5 * ((t_sl - entry)/risk))
                else:
                    new_sl = l + trailing_dist
                    if new_sl < t_sl or t_sl == entry:
                        if t_sl == entry: t_sl = new_sl
                        elif new_sl < t_sl: t_sl = new_sl
                    if h >= t_sl: return (0.5 + 0.5 * ((entry - t_sl)/risk))
        return 0.0

    trades_pro = []    # Conf > 0.55, No EMA
    trades_safe = []   # Conf > 0.55, EMA Filter ON
    trades_basic = []  # No Filters

    for i in range(len(df) - 50):
        raw_sig = raw_signals[i]
        b_sweep = df['bullish_sweep'].iloc[i]
        s_sweep = df['bearish_sweep'].iloc[i]
        entry_p = df['Close'].iloc[i]
        conf = confidences[i]
        ema = df['ema_200'].iloc[i]
        
        t_type = None
        if raw_sig == 2 and b_sweep == 1: t_type = "BUY"
        elif raw_sig == 0 and s_sweep == 1: t_type = "SELL"
            
        if t_type:
            sl_p = df['Low'].iloc[i] - (abs(entry_p - df['Low'].iloc[i]) * 0.1) if t_type == "BUY" else df['High'].iloc[i] + (abs(df['High'].iloc[i] - entry_p) * 0.1)
            risk_pts = abs(entry_p - sl_p)
            if risk_pts <= 0: continue
            
            # Basic Mode (No Filters)
            res = simulate_tsl(i, t_type, entry_p, sl_p, risk_pts)
            if res != 0: trades_basic.append(res)
            
            # Confidence Filter Applied
            if conf >= 0.55:
                # Pro Mode (No EMA)
                trades_pro.append(res)
                
                # Safe Mode (EMA Filter ON)
                is_uptrend = (entry_p > ema)
                if (t_type == "BUY" and is_uptrend) or (t_type == "SELL" and not is_uptrend):
                    trades_safe.append(res)

    def print_stats(trades, name):
        if not trades: 
            print(f"\n{name} Results: No trades found.")
            return
        wins = [t for t in trades if t > 0]
        print(f"\n{name} Stats:")
        print(f"  Total Trades: {len(trades)}")
        print(f"  Win Rate: {len(wins)/len(trades)*100:.1f}%")
        print(f"  Net Return: {sum(trades):.1f}%")

    print_stats(trades_basic, "BASIC (NO FILTERS)")
    print_stats(trades_pro, "PRO (CONF > 0.55)")
    print_stats(trades_safe, "SAFE (CONF + EMA)")

if __name__ == "__main__":
    for symbol in ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]:
        run_triple_backtest(symbol)
