//+------------------------------------------------------------------+
//|                                                 AI_Qlib_Bot.mq5  |
//|                              Copyright 2026, Quantitative Expert |
//+------------------------------------------------------------------+
#property copyright "Expert Quantitative Developer"
#property version   "5.00"
#property strict

#include <Trade\Trade.mqh>

//--- Input Parameters
input string   InpServerUrl       = "http://127.0.0.1:8000/predict";
input double   InpMinConfidence   = 0.55;   // Min AI Confidence to trade

//--- Position Sizing
enum ENUM_RISK_MODE { RISK_PERCENT, FIXED_LOT };
input ENUM_RISK_MODE InpRiskMode  = RISK_PERCENT;
input double   InpRiskPercent     = 1.0;    // % Risk per trade (if Risk mode)
input double   InpFixedLot        = 0.1;    // Fixed Lot (if Fixed mode)
input int      InpMagicNumber     = 554433;

//--- Strategy Management
input bool     InpUseEMAFilter    = true;   // Use EMA 200 Trend Filter
input bool     InpUsePartial      = true;   // Close 50% at 1:1 RR
input bool     InpMoveToBE        = true;   // Move SL to Entry at 1:1 RR
input double   InpTrailMult       = 1.5;    // Trailing Distance (Risk Multiplier)

// Global Handles
int handle_ema200;
CTrade trade;
datetime last_bar_time;
string label_name = "AI_Status_Label";

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit()
{
   last_bar_time = iTime(_Symbol, _Period, 0);
   trade.SetExpertMagicNumber(InpMagicNumber);
   handle_ema200 = iMA(_Symbol, _Period, 200, 0, MODE_EMA, PRICE_CLOSE);
   
   EventSetTimer(1);
   
   ObjectCreate(0, label_name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, label_name, OBJPROP_CORNER, CORNER_RIGHT_LOWER);
   ObjectSetInteger(0, label_name, OBJPROP_XDISTANCE, 180);
   ObjectSetInteger(0, label_name, OBJPROP_YDISTANCE, 40);
   ObjectSetString(0, label_name, OBJPROP_TEXT, "AI SMC BOT READY");
   ObjectSetInteger(0, label_name, OBJPROP_COLOR, clrAqua);
   
   Print("AI Qlib Bot V5.0 - Optimized SMC & TSL Loaded.");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectDelete(0, label_name);
}

//+------------------------------------------------------------------+
//| CalculateLotSize                                                 |
//+------------------------------------------------------------------+
double CalculateLotSize(double sl_dist_points)
{
   if(InpRiskMode == FIXED_LOT) return InpFixedLot;
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amount = balance * (InpRiskPercent / 100.0);
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   
   if(sl_dist_points <= 0 || tick_value <= 0) return InpFixedLot;
   
   // Lot = RiskAmount / (SL_Points * Value_of_Point)
   double lot = risk_amount / (sl_dist_points * (tick_value / (tick_size / _Point)));
   
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   lot = MathFloor(lot / SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP)) * SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   return MathMax(min_lot, MathMin(max_lot, lot));
}

//+------------------------------------------------------------------+
//| ManagePositions (BE, Partial, Trailing)                          |
//+------------------------------------------------------------------+
void ManagePositions()
{
   if(!PositionSelect(_Symbol)) return;
   if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) return;

   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double current_sl = PositionGetDouble(POSITION_SL);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double current_price = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? bid : ask;
   
   // Calculate Initial Risk for RR levels
   double initial_risk = MathAbs(entry - current_sl);
   if(initial_risk == 0) return; // Prevent division by zero

   // --- Phase 1: Break-Even & Partial Profit at 1:1 RR ---
   bool is_1_to_1 = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? (current_price >= entry + initial_risk) : (current_price <= entry - initial_risk);
   
   // Check if we haven't moved to BE yet
   bool sl_at_entry = MathAbs(current_sl - entry) < _Point * 2;
   
   if(is_1_to_1 && !sl_at_entry && current_sl != 0)
   {
      // Partial Profit (50% Lot)
      if(InpUsePartial)
      {
         double vol = PositionGetDouble(POSITION_VOLUME);
         if(vol >= SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN) * 2)
         {
            trade.PositionClosePartial(_Symbol, vol / 2.0);
            Print("AI: Partial Profit (50%) booked at 1:1 RR.");
         }
      }
      
      // Move to Break-Even
      if(InpMoveToBE)
      {
         trade.PositionModify(_Symbol, entry, 0);
         Print("AI: SL moved to Break-Even.");
      }
   }

   // --- Phase 2: Trailing SL (1.5x Risk Distance) ---
   // Only start trailing after BE or if price is in profit
   double trail_dist = initial_risk * InpTrailMult;
   if(is_1_to_1)
   {
      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
      {
         double new_sl = NormalizeDouble(bid - trail_dist, _Digits);
         if(new_sl > current_sl + (_Point * 10)) trade.PositionModify(_Symbol, new_sl, 0);
      }
      else
      {
         double new_sl = NormalizeDouble(ask + trail_dist, _Digits);
         if(new_sl < current_sl - (_Point * 10) || current_sl == 0 || current_sl == entry) 
         {
            if(current_sl == 0 || new_sl < current_sl) trade.PositionModify(_Symbol, new_sl, 0);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| OnTick                                                           |
//+------------------------------------------------------------------+
void OnTick()
{
   // 1. Manage existing positions first
   ManagePositions();

   // 2. New Candle Detection
   datetime current_bar_time = iTime(_Symbol, _Period, 0);
   if(current_bar_time == last_bar_time) return;
   last_bar_time = current_bar_time;

   // 3. Analyze Candle for SMC Sweep
   double o = iOpen(_Symbol, _Period, 1), h = iHigh(_Symbol, _Period, 1), l = iLow(_Symbol, _Period, 1), c = iClose(_Symbol, _Period, 1);
   long v = iVolume(_Symbol, _Period, 1);
   double prev_h = iHigh(_Symbol, _Period, 2), prev_l = iLow(_Symbol, _Period, 2);
   
   // Read actual EMA 200 value
   double ema200_buffer[];
   double ema200 = 0;
   if(CopyBuffer(handle_ema200, 0, 1, 1, ema200_buffer) > 0) ema200 = ema200_buffer[0];
   
   // Web Request to AI Server
   MqlDateTime dt; TimeCurrent(dt);
   string json = StringFormat("{\"symbol\":\"%s\",\"open\":%G,\"high\":%G,\"low\":%G,\"close\":%G,\"volume\":%lld,\"prev_high\":%G,\"prev_low\":%G,\"ema_200\":%G,\"hour\":%d}",
      _Symbol, o, h, l, c, v, prev_h, prev_l, ema200, dt.hour);

   char data[], result[]; string res_headers;
   StringToCharArray(json, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(ArraySize(data) > 0) ArrayResize(data, ArraySize(data)-1);
   
   ResetLastError();
   int timeout = 1000; // 1 second timeout for local server
   int res = WebRequest("POST", InpServerUrl, "Content-Type: application/json\r\nConnection: close\r\n", timeout, data, result, res_headers);
   
   if(res == -1) 
   {
      int err = _LastError;
      if(err == 4060) Print("AI Error: WebRequest is not allowed. Check MT5 Options > Expert Advisors > Allow WebRequest for URL.");
      else Print("AI Error: WebRequest failed. Error code: ", err, " | URL: ", InpServerUrl);
      return;
   }

   string response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   if(StringLen(response) == 0) {
      Print("AI Warning: Empty response from server.");
      return;
   }
   
   // Parse Signal & Confidence
   double confidence = 0.0;
   int conf_pos = StringFind(response, "\"confidence\":");
   if(conf_pos >= 0) confidence = StringToDouble(StringSubstr(response, conf_pos + 13, 5));

   if(confidence < InpMinConfidence) 
   {
      Print("AI Signal ignored. Confidence: ", confidence, " (Min: ", InpMinConfidence, ")");
      return;
   }

   bool has_position = PositionSelect(_Symbol);
   if(has_position && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber) return; // One trade at a time

   // 4. Execution Logic (Wick-based SL + EMA Filter)
   bool is_uptrend = (c > ema200);
   bool is_downtrend = (c < ema200);

   if(StringFind(response, "\"signal\":\"BUY\"") >= 0)
   {
      if(InpUseEMAFilter && !is_uptrend) {
         Print("AI: BUY signal filtered out by EMA 200 (Price is below EMA).");
         return;
      }
      double sl = l - (MathAbs(c - l) * 0.1); // Wick low with buffer
      double sl_points = MathAbs(c - sl) / _Point;
      double lots = CalculateLotSize(sl_points);
      trade.Buy(lots, _Symbol, SymbolInfoDouble(_Symbol, SYMBOL_ASK), sl, 0, "AI-SMC Buy");
   }
   else if(StringFind(response, "\"signal\":\"SELL\"") >= 0)
   {
      if(InpUseEMAFilter && !is_downtrend) {
         Print("AI: SELL signal filtered out by EMA 200 (Price is above EMA).");
         return;
      }
      double sl = h + (MathAbs(h - c) * 0.1); // Wick high with buffer
      double sl_points = MathAbs(sl - c) / _Point;
      double lots = CalculateLotSize(sl_points);
      trade.Sell(lots, _Symbol, SymbolInfoDouble(_Symbol, SYMBOL_BID), sl, 0, "AI-SMC Sell");
   }
}

//+------------------------------------------------------------------+
//| OnTimer (Status Update)                                          |
//+------------------------------------------------------------------+
void OnTimer()
{
   datetime candle_start = iTime(_Symbol, _Period, 0);
   long remaining = (long)(candle_start + PeriodSeconds(_Period)) - (long)TimeCurrent();
   if(remaining < 0) remaining = 0;
   
   string timer_text = StringFormat("AI ACTIVE | Close: %02d:%02d | Conf: %G", (int)(remaining/60), (int)(remaining%60), InpMinConfidence);
   ObjectSetString(0, label_name, OBJPROP_TEXT, timer_text);
   ObjectSetInteger(0, label_name, OBJPROP_COLOR, (remaining <= 10) ? clrOrange : clrLime);
}
