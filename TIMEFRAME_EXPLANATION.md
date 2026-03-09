# Timeframe Usage - Data Flow Diagram

## 📊 How Timeframes Work in POI Mode

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCANNER INITIALIZATION                        │
│                                                                  │
│  TIMEFRAME = "5m"  ← Your configured intraday timeframe         │
│  ENABLE_DAILY_TREND = True  ← POI mode enabled                  │
└─────────────────────────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FOR EACH PAIR                               │
└─────────────────────────────────────────────────────────────────┘
                               ▼
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
        ┌────────────────────┐  ┌────────────────────┐
        │  DAILY CANDLES     │  │  INTRADAY CANDLES  │
        │  (Timeframe: 1d)   │  │  (Timeframe: 5m)   │
        │                    │  │                    │
        │  Fetch: Last 4 days│  │  Fetch: Last 100   │
        │  Use: First 3 for  │  │  Use: Pivot detect │
        │       trend detect │  │       & POI detect │
        └────────┬───────────┘  └────────┬───────────┘
                 │                       │
                 ▼                       ▼
        ┌─────────────────┐    ┌──────────────────┐
        │ TREND ANALYSIS  │    │ SWING DETECTION  │
        │ (Daily TF)      │    │ (5m TF)          │
        │                 │    │                  │
        │ ✓ Detect trend  │    │ ✓ Pivot highs   │
        │ ✓ Get protected │    │ ✓ Pivot lows    │
        │ ✓ Get daily open│    │ ✓ Count touches │
        └────────┬────────┘    └────────┬─────────┘
                 │                      │
                 └──────────┬───────────┘
                            ▼
                 ┌────────────────────┐
                 │   POI FILTERING    │
                 │   (5m swings only) │
                 │                    │
                 │ Is swing between   │
                 │ open & protected?  │
                 │                    │
                 │ YES → POI          │
                 │ NO  → Ignore       │
                 └──────────┬─────────┘
                            ▼
                 ┌────────────────────┐
                 │ MONITOR POIs       │
                 │ (5m timeframe)     │
                 │                    │
                 │ Track mitigation   │
                 │ on each 5m candle  │
                 └──────────┬─────────┘
                            ▼
                 ┌────────────────────┐
                 │  TELEGRAM ALERT    │
                 │                    │
                 │ When POI mitigated │
                 └────────────────────┘
```

## 🔍 Detailed Timeframe Breakdown

### 1️⃣ Daily Timeframe (1d) - TREND CONTEXT ONLY

**Purpose:** Determine market structure and bias  
**Data Fetched:** Last 4 daily candles  
**Usage:**
- Analyze first 3 days to detect trend
- Get protected level from day 3 (previous day)
- Get today's opening price from day 4

**What it DOES NOT do:**
- ❌ Does NOT detect liquidity swings
- ❌ Does NOT identify pivot points
- ❌ Does NOT track price movements

### 2️⃣ Intraday Timeframe (5m, 15m, etc.) - SWING DETECTION

**Purpose:** Detect liquidity swings and POIs  
**Data Fetched:** Last 100 candles of configured timeframe  
**Usage:**
- Detect pivot highs using Pine Script logic
- Detect pivot lows using Pine Script logic
- Count how many times price touches zones
- Identify which swings are between open & protected
- Monitor for mitigation on each new candle

**What it DOES:**
- ✅ Detects ALL liquidity swings
- ✅ Filters for POIs based on daily context
- ✅ Tracks price movements in real-time

## 📈 Example Scenario

**Configuration:**
```python
TIMEFRAME = "15m"           # 15-minute candles
ENABLE_DAILY_TREND = True
TREND_LOOKBACK_DAYS = 3
```

**What Happens:**

### Daily Analysis (1d timeframe)
```
Day 1 (Jan 24): High = 52,500 | Low = 51,000 | Close = 51,500
Day 2 (Jan 25): High = 53,200 | Low = 51,500 | Close = 52,000
Day 3 (Jan 26): High = 53,800 | Low = 52,000 | Close = 53,000
Day 4 (Jan 27): (Today - in progress)

Analysis:
→ Days 1-3: Higher lows (51,000 → 51,500 → 52,000)
→ UPTREND detected ✓
→ Protected Level: 52,000 (Day 3 low)
→ Daily Open: 53,000 (Day 3 close = today's open)
→ POI Zone: 52,000 - 53,000
```

### Intraday Analysis (15m timeframe)
```
Scanner fetches last 100 candles of 15m data

15m Candles analyzed:
08:00 - Pivot high at 53,150
08:45 - Pivot high at 53,350
09:30 - Pivot high at 53,650
10:15 - Pivot low at 52,900 (below POI zone - ignored)

POIs Identified (in zone 53,000 - 53,800):
✓ POI 1: 53,150 (between 53,000 and 53,800)
✓ POI 2: 53,350 (between 53,000 and 53,800)
✓ POI 3: 53,650 (between 53,000 and 53,800)

Each 15m candle:
→ Check if any POI mitigated
→ Update touch counts
→ Send alert if mitigated
```

## 🎯 Key Points

### ✅ Correct Understanding

1. **Daily timeframe = Trend context ONLY**
   - Determines if uptrend or downtrend
   - Identifies protected level
   - Gets today's opening price

2. **Intraday timeframe = Swing/POI detection**
   - Detects pivot highs and lows
   - Identifies which ones are POIs
   - Monitors for mitigation

3. **POI = Intraday swing in daily context zone**
   - Swing detected on 5m/15m/30m (your config)
   - But only if it's between open and protected
   - Represents intraday liquidity in key zone

### ❌ Common Misconceptions

1. **WRONG:** "Daily candles are used to find swings"
   - **RIGHT:** Daily candles only provide context
   
2. **WRONG:** "POIs are daily swing points"
   - **RIGHT:** POIs are intraday swings in a daily-defined zone

3. **WRONG:** "I need to set TIMEFRAME = 1d for POI mode"
   - **RIGHT:** Keep TIMEFRAME = 5m/15m/etc. Daily is fetched automatically

## 🔧 Configuration Guide

### For Day Trading
```python
TIMEFRAME = "5m"            # Fast swing detection
ENABLE_DAILY_TREND = True   # Use daily bias
TREND_LOOKBACK_DAYS = 3     # 3 days for trend
```
**Result:** Detects swings on 5-minute candles, filters by daily trend

### For Swing Trading  
```python
TIMEFRAME = "1h"            # Slower swing detection
ENABLE_DAILY_TREND = True   # Use daily bias
TREND_LOOKBACK_DAYS = 3     # 3 days for trend
```
**Result:** Detects swings on 1-hour candles, filters by daily trend

### For Testing/Learning
```python
TIMEFRAME = "15m"           # Medium-speed detection
ENABLE_DAILY_TREND = False  # No daily filter
```
**Result:** Detects all swings on 15-minute candles, no filtering

## 📊 API Request Summary

**Per Pair, Per Scan:**

**POI Mode (ENABLE_DAILY_TREND = True):**
- 1 request for daily candles (4 candles)
- 1 request for intraday candles (100 candles at configured TF)
- **Total: 2 requests per pair**

**Standard Mode (ENABLE_DAILY_TREND = False):**
- 1 request for intraday candles (100 candles at configured TF)
- **Total: 1 request per pair**

## 💡 Summary

```
DAILY TIMEFRAME (1d)
└─ Purpose: Trend context
└─ Output: Trend direction, protected level, daily open
└─ Does NOT: Detect swings or POIs

INTRADAY TIMEFRAME (5m/15m/etc.)  ← YOUR CONFIGURED TIMEFRAME
└─ Purpose: Swing/POI detection
└─ Output: Liquidity swings, filtered as POIs if in zone
└─ Does: Everything related to swing detection

POI = Intraday swing (on YOUR timeframe) that falls in the zone 
      defined by daily analysis (between open and protected level)
```

---

**Remember:** You detect swings at whatever frequency you want (5m, 15m, 1h), but you use daily structure to filter which swings matter (POIs).
