# Architecture & Implementation Details

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Scanner (Main Loop)                     │
│  - Orchestrates all components                              │
│  - Manages scan cycle and countdown                         │
│  - Handles initialization and error recovery                │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌───────────┐    ┌──────────────┐
│ Binance   │    │  Telegram    │
│ Client    │    │  Notifier    │
└─────┬─────┘    └──────┬───────┘
      │                 │
      │ Market Data     │ Alerts
      ▼                 ▼
┌─────────────────────────────┐
│      Swing Tracker          │
│  - Manages swing points     │
│  - Detects swept liquidity  │
│  - Filters by count/volume  │
└──────────┬──────────────────┘
           │
           │ Uses
           ▼
    ┌──────────────┐
    │    Pivot     │
    │   Detector   │
    │ (Pine Logic) │
    └──────────────┘
```

## 🔍 Component Breakdown

### 1. Config (`config.py`)
**Purpose**: Centralized configuration
**Key Settings**:
- Telegram credentials
- Trading pairs list
- Swing detection parameters
- Performance tuning

### 2. Models (`models.py`)
**Purpose**: Data structures
**Classes**:
- `SwingPoint`: Tracks individual swing highs/lows
- `MarketData`: OHLCV candle data
- `SwingAlert`: Alert message data

### 3. Pivot Detector (`pivot_detector.py`)
**Purpose**: Core Pine Script logic implementation
**Key Methods**:
- `detect_pivot_high()`: Finds local highs
- `detect_pivot_low()`: Finds local lows
- `get_swing_zone()`: Calculates swing boundaries

**Algorithm**:
```python
# Pivot High Detection (matches ta.pivothigh(length, length))
def is_pivot_high(data, index, lookback):
    pivot = data[index].high
    
    # Check lookback bars before
    for i in range(index - lookback, index):
        if data[i].high > pivot:
            return False
    
    # Check lookback bars after
    for i in range(index + 1, index + lookback + 1):
        if data[i].high >= pivot:
            return False
    
    return True
```

### 4. Binance Client (`binance_client.py`)
**Purpose**: API communication
**Features**:
- Kline data fetching
- Automatic retry with exponential backoff
- Connection testing
- Symbol validation

**Rate Limiting Strategy**:
- Exponential backoff: 1s, 2s, 4s
- Configurable timeout
- Concurrent request limiting via MAX_WORKERS

### 5. Telegram Notifier (`telegram_notifier.py`)
**Purpose**: Alert delivery
**Features**:
- Formatted message sending
- Connection validation
- Error handling

**Message Format**:
- Markdown for emphasis
- Price precision: 8 decimals
- Timestamp formatting
- Volume formatting

### 6. Swing Tracker (`swing_tracker.py`)
**Purpose**: State management
**Responsibilities**:
- Maintain active swing points
- Update touch counts and volume
- Detect swept liquidity
- Filter by threshold

**Data Flow**:
```
New Market Data
    ↓
Detect Pivots (at lookback position)
    ↓
Create SwingPoint objects
    ↓
Update counts for existing swings
    ↓
Check for swept swings
    ↓
Generate alerts
    ↓
Remove swept swings
```

### 7. Scanner (`scanner.py`)
**Purpose**: Main orchestrator
**Responsibilities**:
- Initialize all components
- Execute scan loop
- Coordinate concurrent requests
- Display status updates
- Handle graceful shutdown

## 🧠 Pine Script Logic Translation

### Pivot Detection
| Pine Script | Python |
|-------------|--------|
| `ph = ta.pivothigh(14, 14)` | `pivot_detector.detect_pivot_high(data, index)` |
| `pl = ta.pivotlow(14, 14)` | `pivot_detector.detect_pivot_low(data, index)` |
| Checks 28-bar window | Checks bars `[index-14, index+14]` |

### Swing Area Calculation
```python
# Pine Script:
ph_top := high[length]
ph_btm := switch area 
    'Wick Extremity' => math.max(close[length], open[length])
    'Full Range' => low[length]

# Python:
top = candle.high
if area == "Wick Extremity":
    btm = max(candle.close, candle.open)
else:
    btm = candle.low
```

### Crossed Detection
```python
# Pine Script:
ph_crossed := close > ph_top ? true : ph_crossed

# Python:
def is_swept(self, current_close):
    if self.swing_type == "high":
        return current_close > self.price_top
    else:
        return current_close < self.price_btm
```

### Count/Volume Tracking
```python
# Pine Script:
vol += low[length] < top and high[length] > btm ? volume[length] : 0
count += low[length] < top and high[length] > btm ? 1 : 0

# Python:
if swing.is_in_zone(candle.high, candle.low):
    swing.count += 1
    swing.volume += candle.volume
```

## ⚡ Performance Optimizations

### 1. Concurrent Processing
```python
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(scan_pair, pair): pair for pair in pairs}
```
**Benefit**: Scan N pairs in parallel instead of sequentially
**Scalability**: Can handle 200+ pairs with proper worker configuration

### 2. Efficient Data Structures
- `Set[SwingPoint]` for O(1) membership testing
- Dictionary lookup for pair-specific swings
- Automatic cleanup of swept swings

### 3. Memory Management
```python
# Remove swept swings immediately
for swing in to_remove:
    self.swing_points[pair].discard(swing)
```
**Benefit**: Prevents memory growth over time

### 4. Request Optimization
- Single API call per pair per scan
- Fetch only required candles (KLINES_LIMIT)
- Connection reuse within session

## 📊 Scaling to 200+ Pairs

### Configuration Adjustments
```python
# config.py for large-scale monitoring
MAX_WORKERS = 30              # Increase parallelism
SCAN_INTERVAL = 120           # Reduce request frequency
KLINES_LIMIT = 50             # Fetch fewer candles if possible
REQUEST_TIMEOUT = 15          # Allow more time for responses
```

### Expected Performance
- **200 pairs** with MAX_WORKERS=30: ~10-15 seconds per scan
- **Memory**: ~50-100 MB (depending on active swings)
- **Network**: ~200 requests per scan cycle

### Rate Limit Considerations
Binance limits:
- **Weight**: 1200/minute
- **Raw requests**: 6000/5min

With 200 pairs:
- Scan weight: ~200 (1 per pair)
- Can scan every 10-15 seconds safely
- Recommended: 60-120 second interval for safety margin

## 🔐 Error Handling Strategy

### Connection Errors
```python
try:
    response = requests.get(endpoint, timeout=timeout)
except requests.exceptions.RequestException:
    # Retry with exponential backoff
    time.sleep(2 ** attempt)
```

### Invalid Data
- Validate pair symbols on startup
- Check data length before pivot detection
- Skip pairs with persistent errors

### Graceful Degradation
- Failed pairs don't stop other scans
- Partial results still generate alerts
- Status logging for debugging

## 🎯 Key Design Decisions

### Why Threading (not AsyncIO)?
- Simpler for blocking HTTP requests
- Better compatibility with requests library
- Easier to understand and maintain

### Why Sets for Swing Storage?
- O(1) membership testing
- Automatic deduplication
- Easy add/remove operations

### Why Separate Config File?
- Easy customization without code changes
- Version control of settings
- Clear separation of concerns

### Why No Database?
- Stateless operation (fresh scan each cycle)
- Reduced complexity
- No historical data needed

## 🧪 Testing Strategy

### Unit Tests (`test_scanner.py`)
- Model instantiation and methods
- Pivot detection algorithm
- Swing zone calculation
- API connectivity

### Integration Testing
- Run with single pair first
- Verify Telegram alerts
- Check console output
- Monitor for errors over time

### Performance Testing
```bash
# Test with increasing pair counts
PAIRS = ["BTCUSDT"]  # Baseline
PAIRS = 10 pairs     # Light load
PAIRS = 50 pairs     # Medium load
PAIRS = 200 pairs    # Full scale
```

## 📝 Maintenance Guidelines

### Adding New Pairs
1. Add to `PAIRS` in config.py
2. Restart scanner
3. Validation happens automatically

### Changing Detection Logic
1. Modify `pivot_detector.py`
2. Run `test_scanner.py`
3. Verify against Pine Script behavior

### Updating Dependencies
```bash
pip install --upgrade requests
pip freeze > requirements.txt
```

### Monitoring Health
Watch for:
- Increasing failed scans
- Missing alerts (compare with TradingView)
- Memory growth
- Network errors

## 🔮 Future Enhancement Ideas

1. **Historical Backtesting**: Store and analyze swept swings
2. **Multi-Timeframe**: Scan multiple timeframes simultaneously
3. **Advanced Filters**: ML-based swing quality scoring
4. **Web Dashboard**: Real-time visualization
5. **Database Integration**: Long-term trend analysis
6. **Alert Customization**: User-defined alert conditions
7. **Risk Management**: Position sizing suggestions

---

**Last Updated**: January 26, 2025
**Version**: 1.0
**Author**: Based on LuxAlgo Liquidity Swings indicator
