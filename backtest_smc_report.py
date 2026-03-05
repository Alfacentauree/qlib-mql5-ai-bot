import lightgbm as lgb
import numpy as np
import pandas as pd
import os
import glob

MODEL_DIR = "models"
DATA_DIR = "history_data"

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

def run_smc_backtest_with_sl(symbol):
    model_path = os.path.join(MODEL_DIR, f"{symbol}_lgbm_model.txt")
    if not os.path.exists(model_path): return

    model = lgb.Booster(model_file=model_path)
    df = load_local_data(symbol)
    if df is None or len(df) < 300: return

    # Feature Engineering
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

    print(f"\n--- Advanced Backtest for {symbol} (SL: Sweep Candle, RR 1:2) ---")
    
    trades = []
    # RR Ratio
    RR = 2.0
    
    for i in range(len(df) - 50): # Leave some room at the end
        raw_sig = raw_signals[i]
        b_sweep = df['bullish_sweep'].iloc[i]
        s_sweep = df['bearish_sweep'].iloc[i]
        
        entry_price = df['Close'].iloc[i]
        signal_time = df.index[i]
        
        trade_type = None
        sl_price = 0
        tp_price = 0
        
        if raw_sig == 2 and b_sweep == 1:
            trade_type = "BUY"
            sl_price = df['Low'].iloc[i] - (abs(entry_price - df['Low'].iloc[i]) * 0.1) # Adding 10% buffer to risk
            risk = entry_price - sl_price
            if risk <= 0: continue
            tp_price = entry_price + (risk * RR)
            
        elif raw_sig == 0 and s_sweep == 1:
            trade_type = "SELL"
            sl_price = df['High'].iloc[i] + (abs(df['High'].iloc[i] - entry_price) * 0.1)
            risk = sl_price - entry_price
            if risk <= 0: continue
            tp_price = entry_price - (risk * RR)
            
        if trade_type:
            # Simulate trade outcome over next candles
            win = False
            lost = False
            for j in range(i + 1, len(df)):
                high = df['High'].iloc[j]
                low = df['Low'].iloc[j]
                
                if trade_type == "BUY":
                    if low <= sl_price:
                        lost = True
                        break
                    if high >= tp_price:
                        win = True
                        break
                else: # SELL
                    if high >= sl_price:
                        lost = True
                        break
                    if low <= tp_price:
                        win = True
                        break
            
            if win or lost:
                trades.append({'type': trade_type, 'result': 'WIN' if win else 'LOSS'})

    if not trades:
        print("No trades triggered.")
        return

    trade_df = pd.DataFrame(trades)
    win_rate = (len(trade_df[trade_df['result'] == 'WIN']) / len(trade_df)) * 100
    
    # Simple Return Calculation (Assuming 1% risk per trade)
    # Win = +2%, Loss = -1%
    total_return = 0
    for res in trade_df['result']:
        if res == 'WIN': total_return += RR
        else: total_return -= 1
        
    print(f"Total Trades: {len(trade_df)}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Estimated Strategy Return (1% Risk per trade): {total_return:.2f}%")

if __name__ == "__main__":
    assets = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    for symbol in assets:
        run_smc_backtest_with_sl(symbol)
