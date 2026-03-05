# AI SMC Trading Bot - User Guide

This guide explains how to start and maintain your upgraded AI Trading System with Smart Money Concepts (SMC) integration.

---

## 🚀 Step 1: Training the AI Model
Before trading, your AI needs to learn the market patterns (EMA 200, Sweeps, and Sessions).
1. Open your terminal in the `qlib_mql5_bot` folder.
2. Activate your virtual environment: `source venv/bin/activate` (if not already active).
3. Run the training script:
   ```bash
   python train_qlib_model.py
   ```
   *Note: This downloads 60 days of data from Yahoo Finance and saves the models in the `models/` folder.*

---

## 🧠 Step 2: Starting the AI Server
The server is the "Brain" of the bot. It must stay running during trading hours.
1. In the same terminal, run:
   ```bash
   python ai_server.py
   ```
2. You should see: `INFO: Uvicorn running on http://127.0.0.1:8000`.
3. Keep this window open. If you close it, the bot will stop receiving signals.

---

## 📊 Step 3: Setting Up MetaTrader 5
1. Open **MetaEditor** and open `AI_Qlib_Bot.mq5`.
2. Press **F7** to compile. Ensure there are **0 errors**.
3. In MT5, attach the EA to a chart (Recommended: **M15 Timeframe**).
4. Verify on the chart:
   - You see **"AI Qlib Bot V4.2"** in the Experts tab.
   - You see a **Countdown Timer** at the bottom-right corner.
   - The "Algo Trading" button in MT5 is **Green**.

---

## 🔍 Step 4: Monitoring & Rules
- **SMC Confirmation**: The bot will ONLY trade if a Liquidity Sweep is confirmed on a closed candle.
- **Trend Filter**: It only Buys above EMA 200 and Sells below EMA 200.
- **Confidence**: Check the Experts tab for the `confidence` score. Higher scores (0.75+) mean a stronger setup.

---

## 📈 Step 5: Backtesting (Performance Check)
To see how the bot performed over the last 60 days:
```bash
python backtest_smc_report.py
```
This will give you the Win Rate and Cumulative Returns for all pairs.

---

## 🛠 Maintenance (Zaroori Baatein)
1. **Weekend Retraining**: Every Sunday, run `python train_qlib_model.py` to keep the model updated with the latest market moves.
2. **Server Restart**: If you retrain your model, always restart `ai_server.py` so it loads the new files.
3. **Logs**: Check `live_data_logs/` to see the historical performance of live signals.

---

**System Status**: 🟢 Upgraded to SMC V4.2 (Ready for Trading)
