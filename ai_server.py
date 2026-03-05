from fastapi import FastAPI, BackgroundTasks
import uvicorn
import lightgbm as lgb
import numpy as np
from pydantic import BaseModel
import os
import csv
from datetime import datetime

app = FastAPI(title="SMC AI Multi-Asset Trading Server")

MODELS = {}
BASE_DIR = "/home/add/Desktop/Git/qlib_mql5_bot"
MODEL_DIR = os.path.join(BASE_DIR, "models")
LOG_DIR = os.path.join(BASE_DIR, "live_data_logs")
os.makedirs(LOG_DIR, exist_ok=True)

def load_predefined_models():
    target_symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "GER40", "NAS100"]
    for symbol in target_symbols:
        model_path = os.path.join(MODEL_DIR, f"{symbol}_lgbm_model.txt")
        if os.path.exists(model_path):
            MODELS[symbol] = lgb.Booster(model_file=model_path)
            print(f"Loaded AI Model: {symbol}")

@app.on_event("startup")
async def startup_event():
    load_predefined_models()

class MarketData(BaseModel):
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    prev_high: float
    prev_low: float
    ema_200: float
    hour: int

def log_data_to_csv(data: MarketData, confidence: float, signal: str, original_signal: str, probs: list, trend: int, bull_sweep: int, bear_sweep: int):
    symbol = data.symbol.upper().split('.')[0]
    file_path = f"{LOG_DIR}/{symbol}_live_history.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "open", "high", "low", "close", "volume", 
                "trend_filter", "bullish_sweep", "bearish_sweep", "hour_of_day", 
                "confidence", "signal", "original_signal", "prob_sell", "prob_wait", "prob_buy"
            ])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.open, data.high, data.low, data.close, data.volume,
            trend, bull_sweep, bear_sweep, data.hour,
            confidence, signal, original_signal,
            f"{probs[0]:.4f}", f"{probs[1]:.4f}", f"{probs[2]:.4f}"
        ])

@app.post("/predict")
async def predict(data: MarketData, background_tasks: BackgroundTasks):
    raw_symbol = data.symbol.upper()
    
    # Mapping broker names to our trained model names
    symbol = raw_symbol.split('.')[0].split('+')[0].split('-')[0]
    if any(x in symbol for x in ["DE40", "DAX", "DE30", "DAXEUR", "GER40"]):
        symbol = "GER40"
    elif any(x in symbol for x in ["NAS100", "NDX", "USTEC", "NAS"]):
        symbol = "NAS100"
    
    if symbol not in MODELS:
        return {"status": "error", "message": f"Model for {symbol} not loaded. (Original: {raw_symbol})"}

    try:
        # Derived Features
        trend_filter = 1 if data.close > data.ema_200 else 0
        bullish_sweep = 1 if (data.low < data.prev_low and data.close > data.prev_low) else 0
        bearish_sweep = 1 if (data.high > data.prev_high and data.close < data.prev_high) else 0

        input_row = np.array([[
            data.open, data.high, data.low, data.close, data.volume,
            trend_filter, bullish_sweep, bearish_sweep, data.hour
        ]], dtype=np.float32)
        
        probs = MODELS[symbol].predict(input_row)[0].tolist()
        class_idx = np.argmax(probs)
        confidence = float(probs[class_idx])
        
        signals = {0: "SELL", 1: "WAIT", 2: "BUY"}
        original_signal = signals[class_idx]
        final_signal = original_signal

        # SMC OVERRIDE
        override_triggered = False
        if final_signal == "BUY" and bullish_sweep == 0: 
            final_signal = "WAIT"
            override_triggered = True
        elif final_signal == "SELL" and bearish_sweep == 0: 
            final_signal = "WAIT"
            override_triggered = True
        
        background_tasks.add_task(log_data_to_csv, data, confidence, final_signal, original_signal, probs, trend_filter, bullish_sweep, bearish_sweep)
            
        return {
            "status": "success",
            "symbol": symbol,
            "signal": final_signal,
            "original_signal": original_signal,
            "confidence": confidence,
            "probs": {
                "SELL": probs[0],
                "WAIT": probs[1],
                "BUY": probs[2]
            },
            "smc_override": override_triggered
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
