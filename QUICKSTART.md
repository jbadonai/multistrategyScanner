# Quick Start Guide - Liquidity Swing Scanner

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure (Optional)
Edit `config.py` to customize:
- Trading pairs to monitor
- Swing detection parameters
- Scan interval

The scanner is pre-configured with your Telegram credentials and will work immediately.

### Step 3: Run
```bash
# Run the scanner
python scanner.py

# Or run tests first
python test_scanner.py
```

## 📊 What You'll See

The scanner will:
1. ✅ Connect to Binance API
2. ✅ Connect to Telegram Bot
3. ✅ Validate all trading pairs
4. 🔍 Start scanning every 60 seconds
5. 📱 Send Telegram alerts when liquidity is swept

## 🎯 Example Output

```
============================================================
🔍 LIQUIDITY SWING SCANNER
============================================================
📊 Monitoring 3 pairs on 5m timeframe
⚙️  Pivot Lookback: 14
⚙️  Swing Area: Wick Extremity
⏱️  Scan Interval: 60s
============================================================

📊 Scan #1 - 2025-01-26 14:30:00
   ✅ ETHUSDT: Tracking 3H/2L swings
   🚨 BTCUSDT: 1 liquidity sweep(s) detected!
   ✅ ARUSDT: Tracking 1H/1L swings

📈 Scan Summary:
   ✅ Successful: 3/3
   🚨 Alerts: 1
   📍 Active Swings: 4 Highs, 3 Lows
```

## 📱 Telegram Alert Example

When liquidity is swept, you'll receive:
```
🔔 Liquidity Swept 🔔

📊 Pair: BTCUSDT
📍 Type: Swing High
💰 Swing Zone: 51000.00000000 - 50500.00000000
🎯 Sweep Price: 51100.00000000
📈 Touches: 5
📦 Volume: 1,234.56
⏰ Swing Time: 2025-01-26 14:15:00
⏱️ Sweep Time: 2025-01-26 14:30:00
```

## ⚙️ Key Configuration Options

### Understanding Liquidity Filter (IMPORTANT!)
**Not all swings are liquidity swings!** The filter determines when a swing qualifies as a liquidity zone:

```python
FILTER_BY = "Count"   # Track by number of touches
FILTER_VALUE = 1      # Need count > 1 (so 2+ touches)

# This means:
# - Swing detected → count = 0 (not liquidity: 0 is NOT > 1)
# - Price revisits → count = 1 (not liquidity: 1 is NOT > 1)
# - Price revisits → count = 2 (NOW liquidity: 2 > 1 ✓)
# - Only NOW will it trigger alerts if swept
```

**Recommended Settings:**
- `FILTER_VALUE = 0` - All swings qualify (any count > 0)
- `FILTER_VALUE = 1` - Need 2+ touches (count > 1) - **recommended**
- `FILTER_VALUE = 2` - Need 3+ touches (count > 2) - strong liquidity only

### Add More Pairs
```python
PAIRS = [
    "ETHUSDT",
    "BTCUSDT",
    "SOLUSDT",  # Add new pairs here
    "BNBUSDT",
]
```

### Adjust Sensitivity
```python
PIVOT_LOOKBACK = 14  # Higher = fewer, stronger swings
FILTER_VALUE = 0     # Minimum touches before tracking
```

### Change Timeframe
```python
TIMEFRAME = "5m"  # Options: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d
```

## 🔧 Troubleshooting

### No alerts?
- Liquidity swings take time to form and get swept
- Try lowering `FILTER_VALUE` to 0
- Ensure pairs have sufficient volatility

### Rate limits?
- Increase `SCAN_INTERVAL` to 120 seconds
- Reduce number of pairs
- Lower `MAX_WORKERS`

### Connection errors?
- Check internet connection
- Verify Telegram credentials
- Try `python test_scanner.py`

## 📚 Full Documentation

See `README.md` for complete documentation including:
- Detailed logic explanation
- Pine Script mapping
- Optimization for 200+ pairs
- Advanced configuration

## 🛑 Stop Scanner

Press `Ctrl+C` to gracefully stop the scanner.

## ⚠️ Important Notes

1. **Market Data Delay**: Swing detection has a delay of 14 candles (70 minutes on 5m timeframe)
2. **Filter Threshold**: Set `FILTER_VALUE > 0` to only track swings with multiple touches
3. **API Limits**: Binance free tier has rate limits - adjust scan interval for many pairs
4. **Volume Filter**: Use `FILTER_BY = "Volume"` to track high-volume zones

---

**Need Help?** Check README.md or run `python test_scanner.py` to diagnose issues.
