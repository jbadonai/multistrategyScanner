# AUTOMATIC PROFIT TARGET FEATURE

## 🎯 What It Does

Monitors your open ByBit positions and **automatically closes them** when they hit your profit percentage target - just like you see on the ByBit app!

Instead of waiting for TP levels, this closes based on **unrealized profit %**.

---

## ⚙️ Configuration

### Enable/Disable
```python
# In config_new.py
ENABLE_PROFIT_TARGET = True   # Enable automatic profit taking
PROFIT_TARGET_PERCENTAGE = 5.0  # Close at 5% profit
CHECK_PROFIT_INTERVAL = 30      # Check every 30 seconds
```

### Settings Explained

**ENABLE_PROFIT_TARGET:**
- `True` = Monitor positions and close at profit target
- `False` = Use normal TP levels from strategies

**PROFIT_TARGET_PERCENTAGE:**
- Default: `5.0` (5% profit)
- Examples:
  - `3.0` = Close at 3% (quick scalps)
  - `10.0` = Close at 10% (bigger targets)
  - `2.5` = Close at 2.5% (very tight)

**CHECK_PROFIT_INTERVAL:**
- How often to check positions (in seconds)
- Default: `30` seconds
- Lower = more frequent checks (but more API calls)
- Higher = less frequent (but might miss exact target)

---

## 🔄 How It Works

```
1. Scanner places trade (e.g., BTCUSDT LONG at $50,000)

2. Position Monitor starts checking every 30 seconds:
   Entry: $50,000
   Current: $50,100 → Profit: 0.2% → Keep monitoring
   Current: $50,500 → Profit: 1.0% → Keep monitoring
   Current: $52,500 → Profit: 5.0% → CLOSE! 🎯

3. Automatically closes position at market

4. Sends Telegram notification:
   "💰 PROFIT TARGET HIT
    Pair: BTCUSDT
    Profit: 5.02%
    Entry: 50000, Exit: 52510"
```

---

## 📊 Calculation

### Long Positions
```python
profit_pct = ((current_price - entry_price) / entry_price) * 100
```

**Example:**
- Entry: $50,000
- Current: $52,500
- Profit: (52500 - 50000) / 50000 * 100 = **5%** ✅

### Short Positions
```python
profit_pct = ((entry_price - current_price) / entry_price) * 100
```

**Example:**
- Entry: $50,000 (short)
- Current: $47,500
- Profit: (50000 - 47500) / 50000 * 100 = **5%** ✅

---

## 🎯 Advantages Over TP Levels

| TP Levels (Strategy) | Profit % Target |
|---------------------|-----------------|
| Fixed price calculated from entry/channel | Dynamic - based on actual P&L % |
| Might be far from entry | Simple percentage |
| Different R:R ratios | Consistent profit % |
| Can be invalidated if price moves | Always valid |

**Use Case:**
- TP levels good for: Channel trading, swing trades
- Profit % good for: Scalping, quick profits, volatile markets

---

## 🚀 Startup Output

When enabled, you'll see:
```
============================================================
🎯 MULTI-STRATEGY SCANNER ENGINE
============================================================

💰 Profit Target Monitor: ENABLED
   Target: 5.0% profit
   Check interval: 30s

📊 Active Strategies:
   ✅ CRT             🤖 AUTO-TRADE ON
   ...

✅ Position monitor started
```

---

## 📱 Telegram Notifications

When profit target is hit:
```
💰 PROFIT TARGET HIT 💰

📊 Pair: BTCUSDT
📈 Direction: LONG
🎯 Profit: 5.02%

💵 Trade Details:
   • Entry: 50000.00000000
   • Exit: 52510.00000000
   • Target: 5.0%

✅ Position closed automatically
⏱️ Time: 2026-03-11 14:30:45
```

---

## 🛡️ Safety Features

1. **Duplicate Prevention:**
   - Tracks closed positions
   - Won't try to close same position twice

2. **Reduce Only:**
   - Uses `reduceOnly=True` on ByBit
   - Cannot accidentally open new positions

3. **Thread Safe:**
   - Uses Lock() for concurrent safety
   - No race conditions

4. **Error Handling:**
   - Continues monitoring if one position fails
   - Logs errors without crashing

---

## 💡 Usage Scenarios

### Scenario 1: Quick Scalps
```python
PROFIT_TARGET_PERCENTAGE = 2.0  # 2% quick profits
CHECK_PROFIT_INTERVAL = 15      # Check every 15s
```
**Use for:** Day trading, high volatility, many signals

### Scenario 2: Conservative
```python
PROFIT_TARGET_PERCENTAGE = 5.0  # 5% standard
CHECK_PROFIT_INTERVAL = 30      # Check every 30s
```
**Use for:** Standard trading, balanced approach

### Scenario 3: Big Targets
```python
PROFIT_TARGET_PERCENTAGE = 10.0  # 10% larger gains
CHECK_PROFIT_INTERVAL = 60       # Check every 60s
```
**Use for:** Swing trades, strong trends

---

## ⚠️ Important Notes

1. **Overrides Strategy TPs:**
   - When enabled, ignores TP1/TP2 from strategies
   - Closes at profit % instead

2. **Market Orders:**
   - Closes positions with market orders
   - Immediate execution
   - Small slippage possible

3. **All Positions:**
   - Monitors ALL open positions
   - Not just scanner-placed trades
   - Works for manual trades too!

4. **Runs Continuously:**
   - Background thread
   - Checks while scanner runs
   - Stops when scanner stops

---

## 🔧 Troubleshooting

**Monitor not starting:**
- Check `ENABLE_PROFIT_TARGET = True`
- Verify ByBit API connected
- Check logs for errors

**Positions not closing:**
- Verify profit target reached (check ByBit app %)
- Check `CHECK_PROFIT_INTERVAL` not too high
- Ensure position size > 0
- Check API permissions (need order placing)

**Wrong profit calculation:**
- Monitor uses mark price (same as ByBit app)
- Entry price from position avgPrice
- Should match ByBit app exactly

---

## 📊 Example Usage

```python
# In config_new.py

# Standard 5% profit target
ENABLE_PROFIT_TARGET = True
PROFIT_TARGET_PERCENTAGE = 5.0
CHECK_PROFIT_INTERVAL = 30

# Then just run the scanner normally:
# python scanner_multi_strategy.py
```

The monitor runs automatically in the background!

---

## ✅ Status Check

While running, the monitor silently watches positions.

**When profit target is hit:**
```
   🎯 Profit target hit for BTCUSDT!
      Side: Buy, Profit: 5.12%
   🔄 Closing BTCUSDT Buy position...
      Size: 0.5, Profit: 5.12%
   ✅ Position closed successfully
```

---

## 🎉 Result

**Set it and forget it!**
- Automatic profit taking at your target %
- Works 24/7 while scanner runs
- Telegram notifications when closed
- Consistent profit targets across all trades

Perfect for scalpers and active traders! 🚀
