# Configuration for Liquidity Swing Scanner

# Telegram Settings
TELEGRAM_BOT_TOKEN = "7022439090:AAGIJo3K-o85isgUL-1CkzNwwSzFYyjMD8U"
TELEGRAM_CHAT_ID = "5252531829"

# Trading Pairs to Monitor
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT", "BTCUSDC", "ETHUSDC", "ADAUSDT", "LINKUSDT"]


# Binance API Settings
BINANCE_API_BASE = "https://api.binance.com/"
KLINES_LIMIT = 100  # Number of candles to fetch (should be > pivot_lookback * 2)

# Swing Detection Parameters
PIVOT_LOOKBACK = 14  # Pivot lookback period (same as Pine Script default)
SWING_AREA = "Wick Extremity"  # Options: "Wick Extremity" or "Full Range"

# DAILY TREND DETECTION (NEW FEATURE)
# Determines trend direction and identifies POI zones
ENABLE_DAILY_TREND = True  # Enable daily trend-based POI detection
TREND_LOOKBACK_DAYS = 2    # Number of previous days to analyze for trend (2-3 recommended)
                           # Looks at previous 2-3 completed days (excluding today)
                           # Uptrend: Previous lows not taken out (higher lows)
                           # Downtrend: Previous highs not taken out (lower highs)

# POI DETECTION MODE
# When ENABLE_DAILY_TREND = True:
#   - Only liquidity swings between daily open and protected level are tracked as POIs
#   - Protected level: Previous day's LOW (uptrend) or HIGH (downtrend)
#   - Uptrend: POIs are between prev day low and today's open (downside liquidity)
#   - Downtrend: POIs are between prev day high and today's open (upside liquidity)
#   - Only these POIs trigger alerts when mitigated
# When ENABLE_DAILY_TREND = False:
#   - All liquidity swings are monitored (original behavior)

# Behavior when trend is unclear (consolidation, mixed signals)
SKIP_PAIRS_WITHOUT_TREND = True  # True: Skip pairs with unclear trend (strict POI mode)
                                  # False: Fall back to standard mode for unclear pairs (mixed mode)

# FVG (FAIR VALUE GAP) DETECTION - ADVANCED CONFIRMATION
# After a liquidity sweep, scanner can detect FVG formation as confirmation
ENABLE_FVG_DETECTION = True  # True: Detect FVG after sweeps, False: Skip FVG detection
FVG_LOOKBACK_CANDLES = 20    # Number of candles to watch for FVG after sweep (default: 20)
                             # FVG Definition:
                             # - Gap between candle 1 high and candle 3 low (or vice versa)
                             # - Candle 2 in the middle must create the gap
                             # - Candle 3 must close within the range of candle 2
                             # - Candle 2 body must be at least 2x candle 3 body
                             # - Confirmed only when candle 3 closes (not while forming)

# CRT (CHANGE OF RETAIL TENDENCY) DETECTION - ICT CONCEPT
# Monitors 4-hour candles for liquidity sweep and close back in range
ENABLE_CRT_DETECTION = True  # True: Monitor for CRT patterns on 4H, False: Skip CRT
CRT_TIMEFRAME = "4h"         # Timeframe for CRT detection (recommended: 4h)
                             # CRT Pattern:
                             # - Candle 1 (previous): Establishes high/low range
                             # - Candle 2 (current): Sweeps high OR low of candle 1
                             # - Candle 2 MUST close back within candle 1 range
                             # - Bullish CRT: Sweeps low, closes back in range
                             # - Bearish CRT: Sweeps high, closes back in range
                             # - Signal sent only when candle 2 closes (confirmed)

# CRT Quality Filters
CRT_MAX_BODY_RATIO = 40.0    # Max body of sweep candle as % of range candle body (default: 40%)
                             # Sweep candle body should be <= 40% of range candle body
                             # Smaller sweep candle body = stronger reversal signal
                             # Set to 100 to disable this filter

# BYBIT AUTO-TRADING FOR CRT SIGNALS
ENABLE_AUTO_TRADE = True     # True: Auto-execute CRT signals on ByBit, False: Alerts only
BYBIT_API_KEY = "EHgJI02LmFspJeDh5m"           # Your ByBit API key
BYBIT_API_SECRET = "d0D7KjfQN2xsWfpTwH9o771FAa6pBXZG6wkB"        # Your ByBit API secret
BYBIT_TESTNET = False        # True: Use testnet, False: Use mainnet (REAL MONEY!)

# Signal Freshness
MAX_SIGNAL_AGE_MINUTES = 245  # Maximum age of signal in minutes (4 hours + 5 min buffer)
                              # Signals older than this are considered stale and ignored
                              # Set to slightly more than CRT_TIMEFRAME to allow detection
                              # within the current period (4H = 240 min + 5 min buffer = 245)
                              # This prevents acting on signals from previous 4H periods
                             
# Trading Parameters
USE_MAX_LEVERAGE = False      # True: Auto-detect and use max leverage, False: Use fixed leverage
FIXED_LEVERAGE = 10          # Used only if USE_MAX_LEVERAGE = False
ORDER_VALUE_MULTIPLIER = 1.0 # Multiplier for order size (1.0 = leverage value in USDT)
                             # Example: Max leverage = 50, order value = 50 * 1.0 = $50
                             # Set to 0.5 for half, 2.0 for double, etc.

# Risk Management
USE_PERCENTAGE_OF_BALANCE = False  # True: Use % of balance, False: Use leverage multiplier
PERCENTAGE_OF_BALANCE = 10.0       # % of account balance to risk per trade (if enabled)
MAX_CONCURRENT_TRADES = 5          # Maximum number of open positions at once

# Order Execution
MARKET_ORDER = True          # True: Market order (immediate), False: Limit order
SLIPPAGE_TOLERANCE = 0.001   # 0.1% slippage tolerance for limit orders

# LIQUIDITY FILTER - CRITICAL FOR IDENTIFYING LIQUIDITY ZONES
# Not all swing points are liquidity swings. A swing becomes a "liquidity zone" only when:
# - Price revisits the zone multiple times (Count filter), OR
# - Significant volume accumulates in the zone (Volume filter)
# This replicates how the Pine Script only displays/alerts swings that cross the filter threshold
FILTER_BY = "Count"  # Options: "Count" or "Volume"
FILTER_VALUE = 0     # Minimum threshold (uses GREATER THAN comparison):
                     # - Count: count MUST BE > FILTER_VALUE to qualify
                     # - Volume: volume MUST BE > FILTER_VALUE to qualify
                     # Set to 0 to track all swings (any count > 0 qualifies)
                     # Set to 1 to track swings with 2+ touches (count > 1)
                     # Set to 2 to track swings with 3+ touches (count > 2)
                     # Example: FILTER_VALUE = 1 means price must touch the zone at least 2 times total
                     # (initial swing formation + 1 revisit = count of 1, which is NOT > 1, so need 2 revisits)

# Timeframe Settings
TIMEFRAME = "15m"  # Timeframe for LIQUIDITY SWING/POI DETECTION
                  # This is used to detect pivot points and liquidity zones
                  # Examples: "1m", "5m", "15m", "30m", "1h", "4h"
                  # IMPORTANT: Daily ("1d") timeframe is used ONLY for trend detection,
                  # NOT for swing detection. Swings are always detected on this intraday timeframe.
SCAN_INTERVAL = 60  # Seconds between scans

# Performance Settings
MAX_WORKERS = 10  # Maximum concurrent API requests for parallel processing
REQUEST_TIMEOUT = 10  # Seconds for API request timeout
MAX_RETRIES = 3  # Maximum retry attempts for failed requests

# Display Settings
SHOW_SWING_HIGH = True
SHOW_SWING_LOW = True
LOG_LEVEL = "INFO"  # Options: "DEBUG", "INFO", "WARNING", "ERROR"
