# AI SMC Trading Bot V5.0 - Professional Guide 🚀

Yeh ek advanced Artificial Intelligence based trading system hai jo **Smart Money Concept (SMC)** aur **Liquidity Sweeps** par kaam karta hai. Isme LightGBM model ka use kiya gaya hai jo 0.55+ confidence par trades leta hai.

---

## 🛠 System Features (Key Inputs)

| Parameter | Function | Recommended Setting |
| :--- | :--- | :--- |
| **InpMinConfidence** | Minimum AI certainty to execute trade | **0.55** |
| **InpRiskMode** | Risk based on % Account or Fixed Lot | **RISK_PERCENT** |
| **InpRiskPercent** | % of Account Balance to risk per trade | **1.0%** |
| **InpUsePartial** | Close 50% lot at 1:1 Risk-to-Reward | **True** |
| **InpMoveToBE** | Move Stop Loss to Entry at 1:1 RR | **True** |
| **InpTrailMult** | Trailing SL distance (Risk Multiplier) | **1.5x** |
| **InpUseEMAFilter** | Use EMA 200 Trend Filter | **False (for SMC Reversals)** |

---

## 📊 Backtest Performance Summary (M15 Timeframe)

Hamare exhaustive backtesting ke baad, results kuch is tarah rahe:

| Symbol | Strategy Mode | Win Rate (%) | Net Return (%) | Quality |
| :--- | :--- | :--- | :--- | :--- |
| **EURUSD** | PRO (1:3) | **95.24%** | 15.0% | ⭐⭐⭐⭐⭐ |
| **GER40 (Dax)** | Trailing SL | **88.24%** | 16.3% | ⭐⭐⭐⭐⭐ |
| **USDJPY** | Trailing SL | **78.12%** | 29.5% | ⭐⭐⭐⭐ |
| **NAS100 (Nasdaq)** | PRO (1:3) | **72.73%** | 57.0% | ⭐⭐⭐⭐ |
| **XAUUSD (Gold)** | Normal (1:2) | **68.06%** | 33.0% | ⭐⭐⭐ |
| **US30 (Dow)** | Trailing SL | **61.29%** | 10.0% | ⭐⭐⭐ |

---

## 💡 Expert Recommendations (Asset Wise)

### **Mode 1: The Trend Catchers (GER40 & USDJPY)**
*   **Best Mode:** `Trailing SL` (ON).
*   **Why?** In assets mein bade impulsive moves aate hain. Trailing SL inhen pura capture karta hai.
*   **Settings:** Partial ON, BE ON, Trailing Distance 1.5x.

### **Mode 2: The Stability Mode (EURUSD & NAS100)**
*   **Best Mode:** `PRO (Fixed 1:3)` (ON).
*   **Why?** EURUSD mein 95% win rate mila hai partial profit ki wajah se. Nasdaq volatile hai, isliye 1:3 par exit karna safe hai.
*   **Settings:** Partial ON, BE ON.

---

## 🚀 Setup & Execution Guide

### **Step 1: AI Server Start Karein**
Terminal mein niche di gayi command run karein:
```bash
python3 ai_server.py
```
*Server http://127.0.0.1:8000 par active rahega.*

### **Step 2: MT5 EA Compile Karein**
1. MetaEditor mein `AI_Qlib_Bot.mq5` open karein.
2. `F7` (Compile) dabayein. Ensure karein **0 Errors** hain.

### **Step 3: Trading Start Karein**
1. EA ko M15 chart par lagayein.
2. Settings mein apna desired **Risk %** aur **Confidence Threshold (0.55)** set karein.
3. Symbols automatically map ho jayenge (DE40 -> GER40, DJI -> US30 etc).

---

## ⚠️ Important Notes
*   **Indices Tick Value:** EA automatically indices ke mahnge ticks ko handle karta hai, isliye risk calculation humesha account balance ke hisab se sahi hogi.
*   **Trade Frequency:** Hafte mein lagbhag **2-4 high-quality trades** milengi per symbol.
*   **AI Confidence:** 0.55 se niche ki trades "noise" hoti hain, unhe filter rakhna hi behtar hai.

---
**Happy Trading with AI SMC V5.0!** 📈
