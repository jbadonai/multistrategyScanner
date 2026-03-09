# POI (Point of Interest) Mode - Advanced Trading Strategy

## 🎯 Overview

POI Mode is an advanced enhancement that transforms the scanner into a sophisticated intraday trading tool based on daily market structure. Instead of tracking ALL liquidity swings, it focuses ONLY on high-probability zones (POIs) based on daily trend analysis.

## 📊 How It Works

### Step 1: Daily Trend Detection
The scanner analyzes the **previous 2-3 completed days** (excluding today) to determine market structure:

**Uptrend Detection:**
- Each day's LOW is NOT taken out by subsequent days
- Higher lows structure
- Previous candles' lows are being respected

**Downtrend Detection:**
- Each day's HIGH is NOT taken out by subsequent days
- Lower highs structure
- Previous candles' highs are being respected

```
Example Uptrend:
Day 1: Low = 100
Day 2: Low = 105 (didn't break 100) ✓
Day 3: Low = 110 (didn't break 105) ✓
→ UPTREND confirmed
```

### Step 2: Identify Protected Level
Based on the detected trend, identify the level that SHOULD NOT be broken:

**Uptrend:**
- Protected Level = **Previous Day's LOW**
- Logic: In uptrend, we expect price to respect previous lows (higher lows)
- Breaking below previous day's low invalidates the uptrend

**Downtrend:**
- Protected Level = **Previous Day's HIGH**
- Logic: In downtrend, we expect price to respect previous highs (lower highs)
- Breaking above previous day's high invalidates the downtrend

### Step 3: Define POI Zone
The POI zone is the range between two key levels:

**Daily Open:** Previous day's **close price** (in 24/7 crypto markets, this is where today starts)
**Protected Level:** Previous day's low (uptrend) or high (downtrend)

**Upper Bound:** Max(Daily Open, Protected Level)  
**Lower Bound:** Min(Daily Open, Protected Level)

All liquidity swings detected **within this zone** become Points of Interest (POIs).

```
Example in Uptrend:
Day 3 (Yesterday): High = 52,000 | Low = 51,000 | Close = 51,500
Protected (Prev Day Low): 51,000
Daily Open (Prev Day Close): 51,500
POI Zone: 51,000 - 51,500

Any liquidity swing between these levels = POI
```

### Step 4: Monitor POI Mitigation
The scanner only monitors these specific POIs for:
- Building liquidity (revisit count/volume)
- Price mitigation (sweep)

When a POI is mitigated, you receive a Telegram alert showing:
- Which POI was hit
- Complete list of ALL POIs in the zone
- Their status (Active vs Mitigated)

## 🧠 Trading Logic

### Why This Works

**1. Trend Alignment**
- Only trading in the direction of the daily structure
- Higher probability setups

**2. Protected Levels**
- These are levels institutions defend
- Previous day's extremes often act as inflection points

**3. Liquidity Zones**
- POIs represent areas where stops and orders accumulate
- Between open and protected level = prime hunting ground

**4. Intraday Precision**
- Daily context provides the bias
- Intraday liquidity swings provide the entries/exits

### Real Trading Example

**Setup: BTC UPTREND**

```
Day 1: High = $51,800, Low = $50,200, Close = $51,000
Day 2: High = $52,500, Low = $51,000, Close = $51,800 (low above Day 1 low ✓)
Day 3: High = $53,200, Low = $51,500, Close = $52,500 (low above Day 2 low ✓)

→ UPTREND detected (higher lows)

Protected Level: $51,500 (Day 3 LOW - should not break)
Day 4 Opens at: $52,500 (Day 3 CLOSE = today's open)
POI Zone: $51,500 - $52,500 (between protected LOW and open)

Scanner detects 3 liquidity swing highs in this zone:
POI 1: $51,650 (5 touches, 2.5M volume)
POI 2: $51,900 (3 touches, 1.8M volume)  
POI 3: $52,300 (2 touches, 1.2M volume)

Price dips and hits POI 1 at $51,600
→ 🚨 ALERT: POI 1 Mitigated!

Message shows:
- Trend: UPTREND
- Protected: $51,500 (Prev Day Low)
- Daily Open: $52,500 (Prev Day Close)
- All 3 POIs listed
- POI 1 marked as "JUST MITIGATED"

Trading Opportunity:
- Bounce from POI 1 = Long opportunity (buying the dip)
- Watch for sweeps of POI 2 and POI 3
- Protected level at $51,500 = invalidation (stop loss)
- Breaking below $51,500 invalidates uptrend
```

## ⚙️ Configuration

### Enable POI Mode

```python
# In config.py

# Enable POI detection
ENABLE_DAILY_TREND = True

# Trend detection settings
TREND_LOOKBACK_DAYS = 3  # Analyze last 3 days
```

### Disable POI Mode (Revert to Standard)

```python
ENABLE_DAILY_TREND = False
# Scanner will track ALL liquidity swings (original behavior)
```

## 📱 Telegram Alert Format

### POI Mitigation Alert

```
🔔 Liquidity Swept 🔔

📊 Pair: BTCUSDT
📈 Trend: UPTREND
🛡️ Prev Day Low: 51500.00000000
🔓 Daily Open: 52500.00000000

📍 Type: Swing High POI MITIGATED
💰 Swing Zone: 51600.00000000 - 51650.00000000
🎯 Sweep Price: 51600.00000000
📈 Touches: 5
📦 Volume: 2,500,000.00
⏰ Swing Time: 2025-01-26 08:30:00
⏱️ Sweep Time: 2025-01-26 14:45:00

📍 POIs in UPTREND Zone:
   Between Open (52500.00000000) and Protected (51500.00000000)

   1. 🔴 High | 🚨 JUST MITIGATED 🚨
      Zone: 51600.00000000 - 51650.00000000
      Touches: 5 | Volume: 2,500,000
      Time: 08:30:00

   2. 🔴 High | ✅ Active
      Zone: 51850.00000000 - 51900.00000000
      Touches: 3 | Volume: 1,800,000
      Time: 10:15:00

   3. 🔴 High | ✅ Active
      Zone: 52250.00000000 - 52300.00000000
      Touches: 2 | Volume: 1,200,000
      Time: 12:00:00
```

## 📊 Console Output Examples

### POI Mode Active

```
============================================================
🔍 LIQUIDITY SWING SCANNER
============================================================
📊 Monitoring 3 pairs on 5m timeframe
⚙️  Pivot Lookback: 14
⚙️  Swing Area: Wick Extremity
⚙️  Filter By: Count (threshold: 1)

🎯 POI MODE ENABLED:
   • Daily Trend Detection: 3 days lookback
   • Only tracking liquidity between Daily Open & Protected Level
   • Protected = Prev Day HIGH (uptrend) or LOW (downtrend)

⏱️  Scan Interval: 60s
============================================================

📊 Scan #1 - 2025-01-26 14:30:00
============================================================
   📈 BTCUSDT (uptrend): 2H/1L POIs active, 1 mitigated
   📉 ETHUSDT (downtrend): 1H/2L POIs active, 0 mitigated
   ❌ ARUSDT: Trend unclear

📈 Scan Summary:
   ✅ Successful: 3/3
   ❌ Failed: 0/3
   🚨 Alerts: 0
   🎯 Pairs with Trend: 2/3
   💧 Active POIs: 6
   ❌ Mitigated Today: 1
```

## 🎓 Understanding the Strategy

### Market Structure Principle

**Higher Time Frame** (Daily) provides:
- Trend direction
- Protected levels (should hold)
- Directional bias

**Lower Time Frame** (5m) provides:
- Precise entry zones (liquidity swings)
- Risk management levels
- Exit points

### The POI Concept

A POI is NOT just any liquidity swing. It's a liquidity swing that:

1. ✅ Forms in a specific zone (between open and protected)
2. ✅ Aligns with daily market structure
3. ✅ Has accumulated touches/volume
4. ✅ Represents institutional order flow

### Why Between Open and Protected?

**The Open-to-Protected range is a battleground:**

- **Daily Open** = Starting point for the day's auction
- **Protected Level** = Line in the sand (prev day extreme)
- **In Between** = Where liquidity builds before expansion

Smart money often:
1. Sweeps liquidity in this zone
2. Uses POIs to accumulate positions
3. Defends the protected level
4. Expands beyond once ready

## 🔄 Comparison: POI Mode vs Standard Mode

### Standard Mode
```python
ENABLE_DAILY_TREND = False
```
- ✅ Tracks ALL liquidity swings
- ✅ No trend filtering
- ✅ More alerts (possibly noise)
- ✅ Good for: Learning, testing, high-frequency scanning
```

### POI Mode
```python
ENABLE_DAILY_TREND = True
```
- ✅ Tracks ONLY POIs in trend-aligned zones
- ✅ Daily trend filter
- ✅ Fewer, higher-quality alerts
- ✅ Good for: Trading, following smart money, precision entries

## 📈 Best Practices

### 1. Choose Appropriate Timeframes
```python
TIMEFRAME = "5m"  # Good for day trading
TIMEFRAME = "15m" # Good for swing trading POIs
```

### 2. Adjust Liquidity Filter
```python
# For tighter POI qualification:
FILTER_VALUE = 2  # Need 3+ touches

# For looser POI qualification:
FILTER_VALUE = 0  # Any touch qualifies
```

### 3. Monitor Multiple Pairs
- Different pairs may show different trends
- Some may be trending, others consolidating
- Focus on pairs with clear trend detection

### 4. Respect Protected Levels
- If protected level breaks, trend may be invalidating
- Watch for new trend formation
- Adjust bias accordingly

### 5. Use POIs for Entry, Not Direction
- Daily trend gives you directional bias
- POIs give you specific entry zones
- Don't fight the daily trend

## 🚨 Important Notes

### When Trend is Unclear
If the scanner can't detect a clear trend (mixed signals, consolidation):
- Pair shows "Trend unclear" in output
- No POIs tracked for that pair
- Reverts to watching overall price action

### Session Management
POIs are session-specific:
- New session starts each day
- POIs from previous sessions archived
- Fresh POI detection for new day

### Protected Level Breaks
If price breaks the protected level:
- It may signal trend reversal
- Scanner will reassess on next daily candle close
- Current session POIs still tracked until day ends

## 🎯 Quick Start with POI Mode

1. **Enable in Config:**
   ```python
   ENABLE_DAILY_TREND = True
   TREND_LOOKBACK_DAYS = 3
   ```

2. **Run Scanner:**
   ```bash
   python scanner.py
   ```

3. **Observe Output:**
   - Check which pairs have clear trends
   - Note the POI zones
   - Watch for mitigation alerts

4. **Interpret Alerts:**
   - Mitigated POI = Liquidity taken
   - Check remaining active POIs
   - Plan trades based on daily bias

---

**Pro Tip:** Start with POI mode on a few highly liquid pairs (BTC, ETH) to understand the pattern before scaling to 200+ pairs.
