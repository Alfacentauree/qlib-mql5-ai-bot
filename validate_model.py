import yfinance as yf
import lightgbm as lgb
import numpy as np
import pandas as pd
import os
from datetime import datetime

# Use absolute path
BASE_DIR = "/home/add/Desktop/Git/qlib_mql5_bot"
MODEL_DIR = os.path.join(BASE_DIR, "models")

def validate_model(symbol, ticker):
    model_path = os.path.join(MODEL_DIR, f"{symbol}_lgbm_model.txt")
    if not os.path.exists(model_path):
        print(f"Model not found for {symbol}")
        return

    model = lgb.Booster(model_file=model_path)
    print(f"\n--- Validating {symbol} (Ticker: {ticker}) ---")
    
    # Download 60 days of data to have enough for EMA 200
    df = yf.download(ticker, period="60d", interval="15m", progress=False)
    if df.empty:
        print("No data downloaded.")
        return

    # Multi-index fix for some yfinance versions
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Feature Engineering (Must match train_qlib_model.py)
    df['ema_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['trend_filter'] = (df['Close'] > df['ema_200']).astype(int)
    df['prev_high'] = df['High'].shift(1)
    df['prev_low'] = df['Low'].shift(1)
    df['bullish_sweep'] = ((df['Low'] < df['prev_low']) & (df['Close'] > df['prev_low'])).astype(int)
    df['bearish_sweep'] = ((df['High'] > df['prev_high']) & (df['Close'] < df['prev_high'])).astype(int)
    df['hour_of_day'] = df.index.hour
    
    # Label for evaluation
    df['next_return'] = df['Close'].pct_change().shift(-1)
    threshold = 0.0002
    df['actual_label'] = 1 
    df.loc[df['next_return'] > threshold, 'actual_label'] = 2
    df.loc[df['next_return'] < -threshold, 'actual_label'] = 0
    
    df.dropna(inplace=True)
    
    features = ['Open', 'High', 'Low', 'Close', 'Volume', 'trend_filter', 'bullish_sweep', 'bearish_sweep', 'hour_of_day']
    X = df[features].values
    y_true = df['actual_label'].values
    
    # Predict probabilities
    probs = model.predict(X)
    y_pred = np.argmax(probs, axis=1)
    
    # Metrics
    hit_rate = np.mean(y_pred == y_true) * 100
    
    # Filter only for non-WAIT signals (BUY/SELL)
    trade_mask = (y_pred != 1)
    if np.any(trade_mask):
        trade_accuracy = np.mean(y_pred[trade_mask] == y_true[trade_mask]) * 100
        trade_count = np.sum(trade_mask)
    else:
        trade_accuracy = 0
        trade_count = 0

    print(f"Sample Size: {len(X)} candles")
    print(f"Overall Accuracy: {hit_rate:.2f}%")
    print(f"Trade Accuracy (BUY/SELL only): {trade_accuracy:.2f}%")
    print(f"Total Trades Predicted: {trade_count} (out of {len(X)})")
    
    # Distribution of predictions
    unique, counts = np.unique(y_pred, return_counts=True)
    dist = dict(zip(unique, counts))
    print(f"Prediction Distribution: 0(SELL):{dist.get(0,0)}, 1(WAIT):{dist.get(1,0)}, 2(BUY):{dist.get(2,0)}")

if __name__ == "__main__":
    assets = {
        "EURUSD": "EURUSD=X", 
        "GBPUSD": "GBPUSD=X", 
        "USDJPY": "JPY=X", 
        "XAUUSD": "GC=F",
        "GER40": "^GDAXI",
        "NAS100": "^IXIC"
    }
    for symbol, ticker in assets.items():
        validate_model(symbol, ticker)
