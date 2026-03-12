# ============================================================================
# MULTI-STRATEGY TRADING SYSTEM CONFIGURATION
# ============================================================================
# This configuration supports multiple trading strategies:
# 1. POI/FVG Strategy - Points of Interest with Fair Value Gaps
# 2. CRT Strategy - Change of Retail Tendency (ICT Concept)
# 3. SR Channel Strategy - Support/Resistance with Liquidity Traps
#
# Each strategy can be enabled/disabled independently
# Each strategy can have auto-trading enabled/disabled independently
# ============================================================================

# ============================================================================
# TELEGRAM SETTINGS
# ============================================================================
TELEGRAM_BOT_TOKEN = "7022439090:AAGIJo3K-o85isgUL-1CkzNwwSzFYyjMD8U"
TELEGRAM_CHAT_ID = "5252531829"

# ============================================================================
# TRADING PAIRS TO MONITOR
# ============================================================================
# Choose between static pairs or dynamic pair selection

# Static vs Dynamic Pair Selection
USE_DYNAMIC_PAIRS = True             # True = Auto-select volatile pairs daily
                                      # False = Use PAIRS list below (static)

# Static Pairs (used when USE_DYNAMIC_PAIRS = False)
PAIRS = ["PHAUSDT","FIOUSDT","FORMUSDT","SIGNUSDT","BARDUSDT","HUMAUSDT","KITEUSDT","SAHARAUSDT","AIXBTUSDT","KAVAUSDT","AGLDUSDT","LAUSDT","GUNUSDT","RESOLVUSDT","ALICEUSDT","COOKIEUSDT","PHBUSDT","ALLOUSDT","ORCAUSDT","PLUMEUSDT","EULUSDT","EDENUSDT","GIGGLEUSDT","BANANAUSDT","KNCUSDT","FLOWUSDT","RPLUSDT","ICXUSDT","BICOUSDT","MIRAUSDT","MUBARAKUSDT","BREVUSDT","NILUSDT","KMNOUSDT","MLNUSDT","HOOKUSDT","INITUSDT","ENSOUSDT","BABYUSDT","NEARUSDT","MOVRUSDT","EPICUSDT","BANKUSDT","RLCUSDT","FIDAUSDT","DYDXUSDT","SCRUSDT","METISUSDT","HFTUSDT","CGPTUSDT","PENGUUSDT","PEOPLEUSDT","MITOUSDT","HOLOUSDT","SAPIENUSDT","JUPUSDT","MORPHOUSDT","ENAUSDT","SCRTUSDT","PARTIUSDT","NTRNUSDT","MBOXUSDT","RDNTUSDT","COWUSDT","AAVEUSDT","BBUSDT","EIGENUSDT","KSMUSDT","DEXEUSDT","IOUSDT","HOMEUSDT","CVXUSDT","MAGICUSDT","PNUTUSDT","ASTRUSDT","HAEDALUSDT","DASHUSDT","NEWTUSDT","BIOUSDT","SAGAUSDT","KAITOUSDT","DUSKUSDT","RONINUSDT","OXTUSDT","DOGEUSDT","KERNELUSDT","ALTUSDT","APEUSDT","SNXUSDT","RENDERUSDT","ACEUSDT","IMXUSDT","BELUSDT","ORDIUSDT","ARKMUSDT","ARUSDT","LRCUSDT","COTIUSDT","AVNTUSDT","RAREUSDT","CHRUSDT","ARPAUSDT","LDOUSDT","DYMUSDT","CTSIUSDT","MAVUSDT","CTKUSDT","BATUSDT","SOLUSDT","PENDLEUSDT","CVCUSDT","CHZUSDT","ROSEUSDT","2ZUSDT","ENSUSDT","SHELLUSDT","ACTUSDT","ARBUSDT","ONTUSDT","LUMIAUSDT","BANDUSDT","SKYUSDT","C98USDT","EGLDUSDT","ONDOUSDT","ETHUSDT","GMTUSDT","ATUSDT","PYTHUSDT","NFPUSDT","CETUSUSDT","SANDUSDT","MASKUSDT","CFXUSDT","REDUSDT","APTUSDT","ILVUSDT","JTOUSDT","OPUSDT","CELOUSDT","ETHFIUSDT","CRVUSDT","MANTAUSDT","POLUSDT","ADAUSDT","AXSUSDT","METUSDT","AEVOUSDT","PROMUSDT","NMRUSDT","ICPUSDT","NEOUSDT","HEMIUSDT","CYBERUSDT","AUSDT","BIGTIMEUSDT","PROVEUSDT","LINKUSDT","AXLUSDT","AVAUSDT","DOTUSDT","LQTYUSDT","1INCHUSDT","GMXUSDT","BERAUSDT","FLUXUSDT","LISTAUSDT","GLMUSDT","CUSDT","MTLUSDT","MMTUSDT","MANAUSDT","ACXUSDT","RUNEUSDT","PORTALUSDT","LPTUSDT","BLURUSDT","HEIUSDT","MOVEUSDT","DOLOUSDT","ARKUSDT","EDUUSDT","SKLUSDT","BNTUSDT","POWRUSDT","LSKUSDT","QNTUSDT","ENJUSDT","DIAUSDT","INJUSDT","OGNUSDT","ETCUSDT","QTUMUSDT","OPENUSDT","BMTUSDT","POLYXUSDT","SEIUSDT","HIGHUSDT","FILUSDT","IOTAUSDT","MINAUSDT","CATIUSDT","GRTUSDT","AVAXUSDT","SFPUSDT","BTCUSDT","ASTERUSDT","HBARUSDT","MEUSDT","ASRUSDT","COMPUSDT","0GUSDT","HIVEUSDT","ALGOUSDT","OGUSDT","API3USDT","AUCTIONUSDT","AWEUSDT","GASUSDT","ATOMUSDT","HYPERUSDT","NXPCUSDT","KAIAUSDT","JSTUSDT","CAKEUSDT","FFUSDT","ERAUSDT","ONGUSDT","LTCUSDT","ALPINEUSDT","IDUSDT","BNBUSDT"]

# Dynamic Pair Scanner Settings (used when USE_DYNAMIC_PAIRS = True)
VOLATILITY_THRESHOLD = 2.0            # Minimum 24h price change % to qualify
                                      # Higher = fewer, more volatile pairs
                                      # Lower = more pairs, less volatile
                                      # Recommended: 2.0 - 5.0

MAX_DYNAMIC_PAIRS = 100                # Maximum pairs to track
                                      # Top N most volatile pairs selected
                                      # Recommended: 30-50 for good coverage

RESCAN_TIME = "00:00"                 # When to rescan pairs daily (HH:MM)
                                      # Uses your computer's local time
                                      # "00:00" = midnight, "09:00" = 9 AM
                                      # Rescans automatically each day

# How it works when USE_DYNAMIC_PAIRS = True:
# 1. At startup (or daily at RESCAN_TIME): Scans Bybit + Binance
# 2. Finds all USDT pairs listed on BOTH exchanges
# 3. Calculates average 24h volatility for each pair
# 4. Selects top MAX_DYNAMIC_PAIRS above VOLATILITY_THRESHOLD
# 5. Uses these pairs for all strategies until next rescan
# 6. Rescans daily to adapt to changing market conditions

# ============================================================================
# BINANCE API SETTINGS
# ============================================================================
BINANCE_API_BASE = "https://api.binance.com/"
KLINES_LIMIT = 100  # Number of candles to fetch

# ============================================================================
# BYBIT API SETTINGS (FOR AUTO-TRADING)
# ============================================================================
BYBIT_API_KEY = "EHgJI02LmFspJeDh5m"
BYBIT_API_SECRET = "d0D7KjfQN2xsWfpTwH9o771FAa6pBXZG6wkB"
BYBIT_TESTNET = False  # False = LIVE TRADING! True = Testnet

# Global Trading Parameters (applies to all strategies with auto-trade enabled)
USE_MAX_LEVERAGE = False
FIXED_LEVERAGE = 10
ORDER_VALUE_MULTIPLIER = 1.0
USE_PERCENTAGE_OF_BALANCE = False
PERCENTAGE_OF_BALANCE = 10.0
MAX_CONCURRENT_TRADES = 5
MARKET_ORDER = True
SLIPPAGE_TOLERANCE = 0.001

# ============================================================================
# STRATEGY 1: POI/FVG STRATEGY
# ============================================================================
# Points of Interest + Fair Value Gap detection
# Monitors liquidity swings and FVG confirmation after sweeps

ENABLE_POI_STRATEGY = True  # Master switch for POI/FVG strategy
POI_AUTO_TRADE = False       # Auto-trade POI signals (OFF by default)

# Daily Trend Detection
POI_ENABLE_DAILY_TREND = True
POI_TREND_LOOKBACK_DAYS = 2
POI_SKIP_PAIRS_WITHOUT_TREND = True

# Swing Detection
POI_TIMEFRAME = "15m"
POI_PIVOT_LOOKBACK = 14
POI_SWING_AREA = "Wick Extremity"  # "Wick Extremity" or "Full Range"

# Liquidity Filter
POI_FILTER_BY = "Count"  # "Count" or "Volume"
POI_FILTER_VALUE = 0     # Minimum threshold (count > 0 = all swings)

# FVG Detection
POI_ENABLE_FVG = True
POI_FVG_LOOKBACK_CANDLES = 20

# Display Settings
POI_SHOW_SWING_HIGH = True
POI_SHOW_SWING_LOW = True

# ============================================================================
# STRATEGY 2: CRT STRATEGY
# ============================================================================
# Change of Retail Tendency - ICT Smart Money Concept
# Detects liquidity sweeps with close back in range on 4H

ENABLE_CRT_STRATEGY = True  # Master switch for CRT strategy
CRT_AUTO_TRADE = True        # Auto-trade CRT signals (ON by default)

# CRT Detection Settings
CRT_TIMEFRAME = "4h"
CRT_MAX_BODY_RATIO = 40.0  # Max body ratio % for quality filter

# Higher Timeframe Alignment
CRT_REQUIRE_HTF_ALIGNMENT = True
CRT_HTF_TIMEFRAME = "1d"  # "1d" = Daily, "1w" = Weekly
CRT_HTF_LOOKBACK = 20

# Signal Freshness
CRT_MAX_SIGNAL_AGE_MINUTES = 245  # 4H + 5min buffer

# Debug/Visualization
CRT_INCLUDE_CHART_IN_TELEGRAM = True  # Include ASCII chart in Telegram alerts
                                      # Shows candle details, sweep amounts
                                      # Helps verify pattern validity
                                      # Set to False to reduce message size

# ============================================================================
# STRATEGY 3: SR CHANNEL STRATEGY (NEW)
# ============================================================================
# Support/Resistance Channel with Institutional Liquidity Traps
# Professional SR channel trading with fake breakout detection

ENABLE_SR_STRATEGY = True   # Master switch for SR Channel strategy
SR_AUTO_TRADE = False        # Auto-trade SR signals (OFF by default)

# Channel Detection Settings
SR_TIMEFRAME = "15m"         # Execution timeframe
SR_HTF_TIMEFRAME = "4h"      # Higher timeframe for context
SR_MIN_TOUCHES = 5           # Minimum total touches to validate channel
SR_MIN_TOUCHES_PER_SIDE = 2  # Minimum touches on each side

# Channel Quality Filters
SR_MIN_CHANNEL_WIDTH = 0.5   # Minimum channel width as % of price (0.5% = 0.005)
SR_MAX_CHANNEL_WIDTH = 5.0   # Maximum channel width as % of price
SR_BALANCE_TOLERANCE = 0.3   # Max imbalance between touches (30% tolerance)

# Entry Rules
SR_REQUIRE_REJECTION_WICK = True    # Must have clear rejection wick
SR_MIN_WICK_RATIO = 0.4             # Wick must be >= 40% of candle range
SR_REQUIRE_MOMENTUM_SLOW = True     # Momentum must slow before entry
SR_CONFIRMATION_CANDLES = 1         # Candles needed for confirmation

# Liquidity Trap Detection
SR_DETECT_LIQUIDITY_TRAPS = True    # Enable liquidity sweep detection
SR_TRAP_THRESHOLD = 0.1             # % beyond level to qualify as trap (0.1% = 0.001)
SR_REQUIRE_QUICK_RETURN = True      # Price must return quickly after sweep
SR_MAX_CANDLES_AFTER_SWEEP = 3      # Max candles for return after sweep

# Fake Breakout Detection  
SR_DETECT_FAKE_BREAKOUTS = True     # Enable fake breakout filter
SR_MIN_BREAKOUT_BODY_RATIO = 0.6    # Breakout candle body must be >= 60% of range
SR_REQUIRE_VOLUME_EXPANSION = False # Require volume increase (if volume data available)
SR_ALLOW_RETEST_ENTRY = True        # Allow entry on retest after breakout

# Risk Management
SR_TARGET_MID_CHANNEL = True        # First target at mid-channel
SR_MIN_RR_RATIO = 2.0               # Minimum Risk:Reward ratio

# Signal Freshness
SR_MAX_SIGNAL_AGE_MINUTES = 60      # Maximum age for SR signals

# ============================================================================
# SR CHANNEL ADVANCED SETTINGS (Institutional Improvements)
# ============================================================================
# All settings below are OPTIONAL - they have defaults if not specified
# These implement professional-grade improvements for higher win rates

# ATR-Based Dynamic Zones (replaces fixed % tolerance)
SR_USE_ATR_ZONES = True              # Use ATR instead of fixed 3% zones
SR_ATR_ZONE_MULTIPLIER = 0.5         # Zone tolerance = ATR(14) * 0.5
                                     # Smaller = tighter zones, Larger = wider zones
                                     # Recommended range: 0.3 - 0.7

# Volume Confirmation
SR_REQUIRE_VOLUME = True              # Require volume spike confirmation
SR_VOLUME_SPIKE = 1.5                 # Volume must be > average * 1.5
                                     # Higher = stricter (fewer signals, better quality)

# Channel Quality Scoring (0-5 scale)
SR_MIN_QUALITY_SCORE = 3              # Minimum quality score to trade
                                     # 5 = perfect channel (rare)
                                     # 3 = good channel (recommended)
                                     # 2 = acceptable channel (more signals)
                                     # Scoring: symmetry, touches, wicks, volume, width

# Trend Filter (avoid mean reversion in trends)
SR_ENABLE_TREND_FILTER = True         # Skip channels during strong trends
SR_MAX_TREND_STRENGTH = 0.015         # Max allowed EMA50-200 spread (1.5%)
                                     # Based on: abs(EMA50-EMA200)/price
                                     # Smaller = stricter (only trade tight ranges)

# Signal Management
SR_SIGNAL_EXPIRY_CANDLES = 2          # Cancel signals after N candles
SR_MAX_CHANNEL_AGE = 200              # Invalidate channels after N candles
                                     # Old channels lose reliability

# Reversal Quality
SR_REQUIRE_REVERSAL_STRENGTH = True   # Require strong reversals
SR_MIN_REVERSAL_ATR = 0.6             # Min reversal strength = ATR * 0.6
                                     # Reversal must be aggressive

# Trade Frequency Control
SR_MAX_TRADES_PER_CHANNEL = 2         # Max bounces per channel
                                     # After N trades, channel likely breaks

# ============================================================================
# PROFIT TARGET MANAGEMENT
# ============================================================================
# Override strategy TP levels with a fixed % profit target (ROE-based)
# Much more efficient than monitoring - TP is set when order is placed

USE_PERCENTAGE_PROFIT_TARGET = True   # Override TP with % profit target
PERCENTAGE_PROFIT_TARGET = 5.0        # Set TP at 5% ROE (as shown on ByBit)
                                      # If True, ignores strategy TP levels
                                      # If False, uses strategy TP1/TP2

# IMPORTANT: This is ROE% (Return on Equity), not price change%!
# ByBit shows ROE% which accounts for leverage:
#   ROE% = Price Change% × Leverage
#
# Examples with 10x leverage:
#   5% ROE target  → Price needs to move 0.5% (5% / 10)
#   3% ROE target  → Price needs to move 0.3% (3% / 10)
#   10% ROE target → Price needs to move 1.0% (10% / 10)
#
# This matches what you see on ByBit app: "11.15%", "4.16%", etc.
#
# How it works:
# - LONG: TP = entry × (1 + target_roe% / leverage / 100)
# - SHORT: TP = entry × (1 - target_roe% / leverage / 100)
# - Set once when placing order
# - ByBit automatically closes at TP (guaranteed!)
# - No monitoring needed

# ============================================================================
# GLOBAL SCANNER SETTINGS
# ============================================================================
SCAN_INTERVAL = 60  # Seconds between scans
MAX_WORKERS = 10    # Concurrent API requests
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
LOG_LEVEL = "INFO"  # "DEBUG", "INFO", "WARNING", "ERROR"

# ============================================================================
# STRATEGY PRIORITY (When multiple signals occur)
# ============================================================================
# Higher number = higher priority when conflicts occur
STRATEGY_PRIORITIES = {
    "CRT": 3,        # Highest priority (most reliable)
    "SR_CHANNEL": 2, # Medium priority
    "POI_FVG": 1     # Lower priority (more experimental)
}

# ============================================================================
# ALERT GROUPING
# ============================================================================
# Group multiple signals from same pair into single alert
GROUP_ALERTS_BY_PAIR = True
MAX_ALERTS_PER_MESSAGE = 5  # Max signals in one Telegram message
