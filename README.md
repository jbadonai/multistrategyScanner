# Liquidity Swing Scanner

A Python implementation of the LuxAlgo Liquidity Swings indicator that monitors cryptocurrency pairs on Binance and sends Telegram alerts when liquidity is swept.

## Overview

This scanner replicates the logic from the Pine Script "Liquidity Swings [LuxAlgo]" indicator to:
- Detect swing high and low points using pivot detection
- Track liquidity zones at these swing points
- Monitor when price sweeps through these zones
- Send real-time Telegram notifications

## Features

- ✅ **Accurate Pine Script Implementation**: Replicates `ta.pivothigh()` and `ta.pivotlow()` logic
- ✅ **Multi-Pair Monitoring**: Scan multiple cryptocurrency pairs concurrently
- ✅ **Real-time Alerts**: Telegram notifications when liquidity is swept
- ✅ **POI Mode (NEW!)**: Advanced daily trend-based Point of Interest detection
- ✅ **Dual Operating Modes**: Standard (all swings) or POI (trend-filtered zones)
- ✅ **Configurable Settings**: Easily customize all parameters via config file
- ✅ **Optimized Performance**: Concurrent API requests with threading
- ✅ **Modular Design**: Clean separation of concerns for maintainability

## Project Structure

```
liquidity-swing-scanner/
├── config.py              # Configuration settings
├── models.py              # Data models (SwingPoint, MarketData, SwingAlert)
├── pivot_detector.py      # Pivot high/low detection logic
├── trend_analyzer.py      # Daily trend detection (NEW)
├── poi_manager.py         # POI tracking and management (NEW)
├── binance_client.py      # Binance API client
├── telegram_notifier.py   # Telegram notification handler
├── swing_tracker.py       # Swing point tracking and management
├── scanner.py             # Main scanner orchestrator
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── POI_MODE_GUIDE.md     # POI mode documentation (NEW)
└── LIQUIDITY_EXPLAINED.md # Liquidity concepts explained
```

## Installation

1. **Clone or download the files**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure settings** in `config.py`:
   - Set your Telegram bot token and chat ID
   - Add trading pairs to monitor
   - Adjust swing detection parameters

## Configuration

Edit `config.py` to customize:

### Telegram Settings
```python
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
```

### Trading Pairs
```python
PAIRS = [
    "ETHUSDT",
    "BTCUSDT",
    "ARUSDT"
]
```

### Swing Detection Parameters
```python
PIVOT_LOOKBACK = 14          # Pivot lookback period (matches Pine Script)
SWING_AREA = "Wick Extremity" # "Wick Extremity" or "Full Range"
FILTER_BY = "Count"          # "Count" or "Volume"
FILTER_VALUE = 1             # Minimum threshold to track swings
```

### POI Mode (NEW - Advanced Feature)
```python
ENABLE_DAILY_TREND = True    # Enable POI mode
TREND_LOOKBACK_DAYS = 3      # Days to analyze for trend (2-3 recommended)

# When enabled:
# - Detects daily trend (uptrend/downtrend)  
# - Identifies protected level (prev day LOW for uptrend, HIGH for downtrend)
# - Only tracks liquidity swings between daily open and protected level
# - These become Points of Interest (POIs)
# - Alerts only on POI mitigation (not all swings)
```
See [POI_MODE_GUIDE.md](POI_MODE_GUIDE.md) for complete documentation.

### Timeframe Settings
```python
TIMEFRAME = "5m"             # Candlestick timeframe
SCAN_INTERVAL = 60           # Seconds between scans
```

## Usage

Run the scanner:
```bash
python scanner.py
```

The scanner will:
1. Initialize connections to Binance and Telegram
2. Validate all trading pairs
3. Start scanning at the specified interval
4. Display real-time status updates in console
5. Send Telegram alerts when liquidity is swept

### Console Output Example
```
============================================================
🔍 LIQUIDITY SWING SCANNER
============================================================
📊 Monitoring 3 pairs on 5m timeframe
⚙️  Pivot Lookback: 14
⚙️  Swing Area: Wick Extremity
⚙️  Filter By: Count (threshold: 0)
⏱️  Scan Interval: 60s
============================================================

🔄 Initializing connections...
📡 Testing Binance API connection... ✅ Connected
📱 Testing Telegram bot connection... ✅ Telegram bot connected

============================================================
📊 Scan #1 - 2025-01-26 14:30:00
============================================================
   ✅ ETHUSDT: Tracking 3H/2L swings
   🚨 BTCUSDT: 1 liquidity sweep(s) detected!
   ✅ ARUSDT: Tracking 1H/1L swings

📈 Scan Summary:
   ✅ Successful: 3/3
   ❌ Failed: 0/3
   🚨 Alerts: 1
   📍 Active Swings: 4 Highs, 3 Lows

⏳ Next scan in: 00:59
```

## How It Works

### 1. Pivot Detection
The scanner uses the same pivot detection logic as Pine Script's `ta.pivothigh()` and `ta.pivotlow()`:
- Looks for local highs/lows within a lookback window
- A pivot high is detected when the high at the center is higher than all surrounding bars
- A pivot low is detected when the low at the center is lower than all surrounding bars

### 2. Swing Zone Definition
Based on `SWING_AREA` setting:
- **Wick Extremity**: Zone from wick to candle body
  - Swing High: From high to max(open, close)
  - Swing Low: From low to min(open, close)
- **Full Range**: Entire candle range
  - Swing High: From high to low
  - Swing Low: From low to high

### 3. Liquidity Tracking
- Counts how many times price touches the swing zone
- Accumulates volume within the zone
- Only tracks swings that meet the filter threshold

### 4. Sweep Detection
A swing is considered "swept" when:
- Price closes above a swing high zone (for highs)
- Price closes below a swing low zone (for lows)
- The swing meets the minimum filter criteria

### 5. Alert Generation
When liquidity is swept:
- Creates a detailed alert with swing information
- Sends Telegram notification
- Removes the swept swing from tracking

## Optimization Features

### Concurrent Processing
- Uses `ThreadPoolExecutor` to scan multiple pairs simultaneously
- Configurable `MAX_WORKERS` for controlling concurrency

### Request Management
- Exponential backoff retry logic for failed requests
- Configurable timeout and retry settings
- Request rate limiting to respect API limits

### Memory Efficiency
- Removes swept swings from memory
- Only stores active (non-crossed) swing points
- Efficient data structures (sets for O(1) lookups)

## Extending to 200+ Pairs

The scanner is optimized for large-scale monitoring:

1. **Increase MAX_WORKERS** in config.py (e.g., 20-50)
2. **Adjust SCAN_INTERVAL** to avoid rate limits (e.g., 120s)
3. **Monitor API usage** - Binance free tier has limits
4. **Consider symbol filtering** - Focus on high-volume pairs

Example config for 200+ pairs:
```python
MAX_WORKERS = 30
SCAN_INTERVAL = 120
REQUEST_TIMEOUT = 15
```

## Pine Script Logic Mapping

| Pine Script | Python Implementation |
|-------------|----------------------|
| `ta.pivothigh(length, length)` | `PivotDetector.detect_pivot_high()` |
| `ta.pivotlow(length, length)` | `PivotDetector.detect_pivot_low()` |
| Swing area calculation | `PivotDetector.get_swing_zone()` |
| Count/volume tracking | `SwingPoint.update_metrics()` |
| Crossed detection | `SwingPoint.is_swept()` |
| Zone intersection | `SwingPoint.is_in_zone()` |

## Troubleshooting

### "Failed to fetch data" errors
- Check internet connection
- Verify trading pair symbols are correct
- Increase `REQUEST_TIMEOUT` in config

### No Telegram alerts
- Verify bot token and chat ID are correct
- Check bot has permission to send messages
- Test with `telegram_notifier.test_connection()`

### High CPU/memory usage
- Reduce `MAX_WORKERS`
- Increase `SCAN_INTERVAL`
- Reduce number of monitored pairs

### Rate limit errors
- Increase `SCAN_INTERVAL`
- Reduce `MAX_WORKERS`
- Consider upgrading Binance API tier

## License

This implementation is based on the LuxAlgo Liquidity Swings indicator:
- Original indicator: CC BY-NC-SA 4.0
- Python implementation: For educational purposes

## Disclaimer

This software is for educational purposes only. Use at your own risk. Always verify signals manually before trading.
