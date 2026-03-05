import lightgbm as lgb
import numpy as np
import pandas as pd
import os
import glob

# Use absolute path to avoid directory issues
BASE_DIR = "/home/add/Desktop/Git/qlib_mql5_bot"
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "history_data")
os.makedirs(MODEL_DIR, exist_ok=True)

SYMBOL_MAPPING = {
    "DAXEUR": "GER40",
    "NDXUSD": "NAS100",
    "DJIUSD": "US30",  # Dow Jones Added
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "XAUUSD": "XAUUSD"
}

def load_local_data(raw_symbol):
    files = [f for f in os.listdir(DATA_DIR) if f.startswith(raw_symbol) and f.endswith(".csv")]
    if not files:
        print(f"Error: No CSV file found for {raw_symbol} in {DATA_DIR}")
        return None
    
    file_path = os.path.join(DATA_DIR, files[0])
    print(f"Reading data for {raw_symbol} from {file_path}")
    
    try:
        df = pd.read_csv(file_path, sep='\t')
        df.columns = [col.replace('<', '').replace('>', '').title() for col in df.columns]
        df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        df.set_index('Datetime', inplace=True)
        if 'Tickvol' in df.columns: df.rename(columns={'Tickvol': 'Volume'}, inplace=True)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def train_classification_model(raw_symbol, model_name):
    print(f"\n--- Training SMC Upgrade Model for {model_name} (Source: {raw_symbol}) ---")
    df = load_local_data(raw_symbol)
    if df is None or df.empty: return
    if len(df) < 300: return

    df['next_return'] = df['Close'].pct_change().shift(-1)
    df['ema_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['trend_filter'] = (df['Close'] > df['ema_200']).astype(int)
    df['prev_high'] = df['High'].shift(1)
    df['prev_low'] = df['Low'].shift(1)
    df['bullish_sweep'] = ((df['Low'] < df['prev_low']) & (df['Close'] > df['prev_low'])).astype(int)
    df['bearish_sweep'] = ((df['High'] > df['prev_high']) & (df['Close'] < df['prev_high'])).astype(int)
    df['hour_of_day'] = df.index.hour
    
    threshold = 0.0002
    df['label'] = 1 
    df.loc[df['next_return'] > threshold, 'label'] = 2
    df.loc[df['next_return'] < -threshold, 'label'] = 0
    df.dropna(inplace=True)
    
    features = ['Open', 'High', 'Low', 'Close', 'Volume', 'trend_filter', 'bullish_sweep', 'bearish_sweep', 'hour_of_day']
    X = df[features].values
    y = df['label'].values
    
    train_data = lgb.Dataset(X, label=y)
    params = {
        'objective': 'multiclass', 'num_class': 3, 'metric': 'multi_logloss',
        'verbosity': -1, 'learning_rate': 0.03, 'num_leaves': 31, 'num_threads': 4
    }
    
    model = lgb.train(params, train_data, num_boost_round=150)
    model.save_model(os.path.join(MODEL_DIR, f"{model_name}_lgbm_model.txt"))
    print(f"Successfully saved {model_name} model ({len(df)} candles)")

if __name__ == "__main__":
    for raw, standard in SYMBOL_MAPPING.items():
        train_classification_model(raw, standard)
