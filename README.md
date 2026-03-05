# Qlib MQL5 AI Bot

This project implements an AI-driven trading system using Microsoft Qlib and LightGBM models, integrated with MetaTrader 5 (MQL5).

## Components

- **MQL5 EA:** `AI_Qlib_Bot.mq5` - The MetaTrader 5 Expert Advisor that executes trades based on AI predictions.
- **AI Server:** `ai_server.py` - Flask-based server to provide real-time predictions to the MQL5 EA.
- **Model Training:** `train_qlib_model.py` - Script to train LightGBM models using Qlib datasets.
- **Validation & Backtesting:** Tools like `validate_model.py`, `backtest_comparison.py`, and `backtest_optimization.py` for performance analysis.
- **Models:** Pre-trained LightGBM models stored in the `models/` directory.

## Setup

1.  **Environment:**
    - Create a virtual environment: `python -m venv venv`
    - Install dependencies: `pip install -r requirements.txt`
2.  **Training:**
    - Run `python train_qlib_model.py` to train models for your desired pairs.
3.  **Deployment:**
    - Start the AI server: `python ai_server.py`
    - Compile and attach `AI_Qlib_Bot.mq5` to your charts in MetaTrader 5.

## Data

- Historical data is stored in `history_data/`.
- Live logs are recorded in `live_data_logs/`.

## Guides

- Detailed instructions can be found in `GUIDE.md` and `AI_SMC_BOT_GUIDE.md`.
