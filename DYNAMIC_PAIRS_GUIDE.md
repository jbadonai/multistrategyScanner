# DYNAMIC PAIR SELECTION - AUTO-ADAPT TO MARKET

## 🎯 What It Does

**Automatically selects the most volatile (profitable) trading pairs and updates them daily.**

Instead of manually choosing pairs, the scanner:
1. **Scans** Bybit + Binance for all USDT pairs
2. **Calculates** 24h volatility for each
3. **Selects** top N most volatile pairs
4. **Rescans** daily at midnight to adapt

---

## ⚙️ Configuration

```python
# In config_new.py

# Enable/Disable
USE_DYNAMIC_PAIRS = False   # False = Static pairs (default)
                            # True = Auto-select volatile pairs

# Settings (when USE_DYNAMIC_PAIRS = True)
VOLATILITY_THRESHOLD = 2.0  # Min 24h change % (2% default)
MAX_DYNAMIC_PAIRS = 50      # Max pairs to track (50 default)
RESCAN_TIME = "00:00"       # Daily rescan time (midnight)
```

---

## 🔄 How It Works

### Startup (or Daily Rescan):

```
1. Fetch all USDT pairs from Bybit
   → Example: 500 pairs

2. Fetch all USDT pairs from Binance  
   → Example: 600 pairs

3. Find common pairs (listed on BOTH)
   → Example: 450 common pairs

4. Calculate average 24h volatility
   → Bybit: +5.2%, Binance: +5.8%
   → Average: 5.5%

5. Filter by threshold (e.g., 2.0%)
   → Keep: 5.5% ✅
   → Reject: 1.2% ❌

6. Sort by volatility (highest first)
   → BTCUSDT: 8.5%
   → ETHUSDT: 7.2%
   → SOLUSDT: 6.8%
   → ...

7. Select top MAX_DYNAMIC_PAIRS (e.g., 50)
   → Final list: 50 most volatile pairs

8. Use these pairs for all strategies
```

---

## 📊 Example Output

**At Startup:**
```
============================================================
🎯 MULTI-STRATEGY SCANNER ENGINE
============================================================

🔍 SCANNING FOR VOLATILE PAIRS
============================================================
📊 Bybit: 523 USDT pairs found
📊 Binance: 612 USDT pairs found
📊 Common pairs: 487
✅ Found 156 volatile pairs (≥2.0%)

🔥 Top 10 Most Volatile:
Rank   Pair            Bybit %   Binance %    Avg %
--------------------------------------------------------
1      BTCUSDT          8.45%      8.72%      8.59%
2      ETHUSDT          7.12%      7.38%      7.25%
3      SOLUSDT          6.84%      6.95%      6.90%
4      DOGEUSDT         6.23%      6.45%      6.34%
5      AVAXUSDT         5.98%      6.12%      6.05%
6      MATICUSDT        5.67%      5.89%      5.78%
7      LINKUSDT         5.45%      5.52%      5.49%
8      ADAUSDT          5.23%      5.41%      5.32%
9      DOTUSDT          5.12%      5.28%      5.20%
10     ATOMUSDT         4.98%      5.06%      5.02%

✅ Pair list updated: 50 pairs
============================================================

📊 Pair Mode: DYNAMIC (auto-selects volatile pairs)
   Monitoring: 50 pairs
   Rescans: Daily at 00:00
```

---

## 🕐 Daily Rescanning

**Every day at RESCAN_TIME (default 00:00 = midnight):**

```
⏰ Daily rescan triggered at 2026-03-13 00:00:05

🔍 SCANNING FOR VOLATILE PAIRS
============================================================
📊 Bybit: 527 USDT pairs found
📊 Binance: 615 USDT pairs found
📊 Common pairs: 491
✅ Found 142 volatile pairs (≥2.0%)

Changes from yesterday:
➕ Added: XRPUSDT, BNBUSDT (became volatile)
➖ Removed: SHIBUSDT, APTUSDT (volatility dropped)
✅ Pair list updated: 50 pairs
```

---

## 🎯 Benefits

| Static Pairs | Dynamic Pairs |
|-------------|---------------|
| ❌ Manual updates | ✅ Auto-updates daily |
| ❌ May miss opportunities | ✅ Always trades volatile pairs |
| ❌ Includes dead pairs | ✅ Drops low-volume pairs |
| ❌ Fixed forever | ✅ Adapts to market |
| ✅ Predictable | ⚠️ Pairs change daily |

**Use Dynamic When:**
- You want maximum opportunities
- Market changes frequently
- You trade many pairs
- Hands-off approach preferred

**Use Static When:**
- You prefer specific pairs
- Consistent tracking needed
- Trading few select pairs
- More control desired

---

## ⚙️ Configuration Examples

### Conservative (High Quality):
```python
USE_DYNAMIC_PAIRS = True
VOLATILITY_THRESHOLD = 5.0    # Very volatile only
MAX_DYNAMIC_PAIRS = 20        # Top 20 pairs
RESCAN_TIME = "00:00"
```

**Result:** ~15-20 extremely volatile pairs

---

### Balanced (Recommended):
```python
USE_DYNAMIC_PAIRS = True
VOLATILITY_THRESHOLD = 2.0    # Moderately volatile
MAX_DYNAMIC_PAIRS = 50        # Top 50 pairs
RESCAN_TIME = "00:00"
```

**Result:** ~40-50 good volatile pairs

---

### Aggressive (Maximum Coverage):
```python
USE_DYNAMIC_PAIRS = True
VOLATILITY_THRESHOLD = 1.0    # Any movement
MAX_DYNAMIC_PAIRS = 100       # Top 100 pairs
RESCAN_TIME = "00:00"
```

**Result:** ~80-100 pairs with any volatility

---

### Different Rescan Times:
```python
RESCAN_TIME = "09:00"   # 9 AM
RESCAN_TIME = "12:00"   # Noon
RESCAN_TIME = "18:00"   # 6 PM
RESCAN_TIME = "00:00"   # Midnight (default)
```

Uses **your computer's local time** (works on Windows & Linux)

---

## 📋 How Volatility is Calculated

**For Each Pair:**
```python
# Bybit 24h change
bybit_change = abs(price_24h_percent)

# Binance 24h change  
binance_change = abs(price_change_percent)

# Average
avg_volatility = (bybit_change + binance_change) / 2

# Filter
if avg_volatility >= VOLATILITY_THRESHOLD:
    selected_pairs.append(pair)
```

**Example:**
```
BTCUSDT:
- Bybit: +8.45%
- Binance: +8.72%
- Average: 8.59% ✅ (above 2.0% threshold)

SHIBUSDT:
- Bybit: +1.2%
- Binance: +1.4%
- Average: 1.3% ❌ (below 2.0% threshold)
```

---

## 🔍 What Happens During Scan

**API Calls Made:**
1. `GET https://api.bybit.com/v5/market/tickers?category=linear`
2. `GET https://fapi.binance.com/fapi/v1/ticker/24hr`

**Total:** 2 API calls per scan

**Scan Frequency:**
- At startup: Once
- Daily: Once at RESCAN_TIME
- Total: ~2 scans/day

**Very lightweight!** ✅

---

## 📱 Console Output Examples

### When Pair List Changes:
```
⏰ Daily rescan triggered at 2026-03-13 00:00:05

Changes detected:
➕ NEW: AVAXUSDT (6.5% volatility)
➕ NEW: MATICUSDT (5.8% volatility)
➖ REMOVED: SHIBUSDT (volatility dropped to 0.8%)
➖ REMOVED: APTUSDT (volatility dropped to 1.2%)
✔️ KEPT: 46 pairs (still volatile)
```

### When No Changes:
```
⏰ Daily rescan triggered at 2026-03-13 00:00:05

✅ No changes - pair list remains same (50 pairs)
All pairs still meet volatility threshold
```

---

## 🛡️ Safety Features

1. **Fallback:** If scan fails, uses previous pair list
2. **Thread-Safe:** Pairs updated atomically
3. **Exchange Verification:** Only pairs on BOTH Bybit + Binance
4. **Auto-Recovery:** Rescans continue even after errors
5. **Graceful Shutdown:** Stops cleanly with scanner

---

## ⚠️ Important Notes

### Pair Changes During Operation:
```
Scan #1 (00:00): Trading BTCUSDT, ETHUSDT, SOLUSDT...
Scan #100 (12:00): Still trading same pairs
Scan #200 (00:00 next day): New pairs! BTCUSDT, XRPUSDT, AVAXUSDT...
```

**Pairs only change during daily rescan!**

---

### Impact on Open Positions:
```
Day 1: CRT signal on SHIBUSDT → Trade opened
Day 2: SHIBUSDT removed from pair list (low volatility)
       → Open position UNAFFECTED
       → Just won't scan SHIBUSDT anymore
       → Existing trade continues
```

**Removing a pair doesn't close positions!**

---

### USDC Pairs Filtered:
```
Dynamic scanner finds: BTCUSDC, ETHUSDC
ByBit auto-trade: SKIPS USDC pairs (not supported)
Telegram alerts: Still sent for USDC pairs
```

**USDC pairs can be in list but won't auto-trade**

---

## 🎯 Recommended Setup

**For Most Users:**
```python
USE_DYNAMIC_PAIRS = True
VOLATILITY_THRESHOLD = 2.0
MAX_DYNAMIC_PAIRS = 50
RESCAN_TIME = "00:00"
```

**For Scalpers (Many Pairs):**
```python
USE_DYNAMIC_PAIRS = True
VOLATILITY_THRESHOLD = 1.5
MAX_DYNAMIC_PAIRS = 80
RESCAN_TIME = "00:00"
```

**For Quality Focus (Few Pairs):**
```python
USE_DYNAMIC_PAIRS = True
VOLATILITY_THRESHOLD = 4.0
MAX_DYNAMIC_PAIRS = 20
RESCAN_TIME = "00:00"
```

**For Manual Control:**
```python
USE_DYNAMIC_PAIRS = False
# Edit PAIRS list manually
```

---

## 🚀 How to Enable

### Step 1: Edit Config
```python
# In config_new.py
USE_DYNAMIC_PAIRS = True  # Change from False
```

### Step 2: Run Scanner
```bash
python scanner_multi_strategy.py
```

### Step 3: Watch Initial Scan
```
🔍 Performing initial pair scan...
[Scans Bybit and Binance]
✅ Pair list updated: 50 pairs
```

### Step 4: It Runs Forever
```
- Scans your chosen pairs every 60s
- Rescans pair list daily at midnight
- Adapts automatically
```

---

## ✅ Summary

**Dynamic pair selection:**
- ✅ Automatically finds volatile pairs
- ✅ Updates daily at midnight
- ✅ Adapts to market changes
- ✅ Works on Windows & Linux
- ✅ Very lightweight (2 API calls/day)
- ✅ Thread-safe pair updates
- ✅ Falls back gracefully on errors

**Perfect for hands-off trading that adapts to the market!** 🎯
