"""
CRT Scanner module - monitors 4H candles for CRT patterns
Runs independently alongside the main POI/FVG scanner
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from models import CRTAlert, MarketData
from crt_detector import CRTDetector
from htf_trend_analyzer import HTFTrendAnalyzer
import config


class CRTScanner:
    """Scans pairs for CRT patterns on 4H timeframe"""
    
    def __init__(self):
        self.crt_detector = CRTDetector()
        self.htf_analyzer = HTFTrendAnalyzer() if config.CRT_REQUIRE_HTF_ALIGNMENT else None
        self.timeframe = config.CRT_TIMEFRAME
        # Track last seen candle to avoid duplicate alerts
        self.last_candle_time: Dict[str, int] = {}
        # Signal freshness limit
        self.max_signal_age = timedelta(minutes=config.MAX_SIGNAL_AGE_MINUTES)
        # Cache HTF bias per pair
        self.htf_bias_cache: Dict[str, Optional[str]] = {}
    
    def initialize_pair(self, pair: str):
        """Initialize CRT tracking for a pair"""
        if pair not in self.last_candle_time:
            self.last_candle_time[pair] = 0
    
    def scan_pair(self, pair: str, candles: List[MarketData], 
                  htf_candles: Optional[List[MarketData]] = None) -> Optional[CRTAlert]:
        """
        Scan a pair for CRT pattern on COMPLETED candles only
        Ignores stale signals to prevent acting on old data
        
        Args:
            pair: Trading pair
            candles: List of 4H candles (need at least 3, most recent might be forming)
            htf_candles: Optional list of higher timeframe candles for trend alignment
            
        Returns:
            CRTAlert if pattern detected in completed candles, None otherwise
        """
        self.initialize_pair(pair)
        
        # Need at least 3 candles (to ensure we check completed ones)
        if len(candles) < 3:
            return None
        
        # Check the candle that just closed (candles[-2], not candles[-1] which might be forming)
        # This is the candle we're analyzing for CRT pattern
        completed_candle_time = candles[-2].timestamp
        completed_candle_datetime = datetime.fromtimestamp(completed_candle_time / 1000)
        
        # Debug: Show what we're checking
        if pair in ["BTCUSDT", "ETHUSDT"]:  # Debug for major pairs only
            print(f"   🔍 {pair} CRT check: Candle closed at {completed_candle_datetime.strftime('%Y-%m-%d %H:%M')}")
        
        # Check if we already sent an alert for this completed candle
        if completed_candle_time == self.last_candle_time.get(pair):
            # Already processed this candle
            if pair in ["BTCUSDT", "ETHUSDT"]:
                print(f"   ⏭️  {pair} already checked this candle, skipping")
            return None
        
        # Get HTF bias if HTF alignment is enabled
        htf_bias = None
        if config.CRT_REQUIRE_HTF_ALIGNMENT and self.htf_analyzer and htf_candles:
            htf_bias = self.htf_analyzer.get_trend_bias(htf_candles)
            # Cache the bias
            self.htf_bias_cache[pair] = htf_bias
        
        # Detect CRT pattern (detector now checks candles[-3] and candles[-2])
        crt = self.crt_detector.detect_crt(candles)
        
        if crt is None:
            # No CRT detected - DO NOT update last_candle_time
            # This allows us to check this candle again if pattern appears later
            if pair in ["BTCUSDT", "ETHUSDT"]:
                print(f"   ❌ {pair} no CRT pattern detected")
            return None
        
        # Check HTF alignment if required
        if config.CRT_REQUIRE_HTF_ALIGNMENT and self.htf_analyzer:
            if not self.htf_analyzer.is_crt_aligned(crt["type"], htf_bias):
                # CRT not aligned with HTF bias - reject
                htf_label = htf_bias if htf_bias else "neutral"
                print(f"   ⚠️  {pair} CRT ({crt['type']}) NOT aligned with HTF ({htf_label}) - rejected")
                return None
            else:
                htf_label = htf_bias if htf_bias else "neutral"
                if pair in ["BTCUSDT", "ETHUSDT"]:
                    print(f"   ✅ {pair} CRT ({crt['type']}) aligned with HTF ({htf_label})")
        
        # CHECK SIGNAL FRESHNESS - Critical for trading safety
        signal_time = crt["timestamp"]
        current_time = datetime.now()
        signal_age = current_time - signal_time
        
        if signal_age > self.max_signal_age:
            # Signal is stale - ignore it
            minutes_old = signal_age.total_seconds() / 60
            print(f"   ⏰ {pair} CRT signal is stale ({minutes_old:.1f} min old), ignoring")
            return None
        
        # Validate entry setup
        if not self.crt_detector.is_valid_entry_zone(crt):
            return None
        
        # Create CRT alert
        sweep_price = crt.get("sweep_low") if crt["type"] == "bullish" else crt.get("sweep_high")
        
        alert = CRTAlert(
            pair=pair,
            crt_type=crt["type"],
            candle_1_high=crt["candle_1_high"],
            candle_1_low=crt["candle_1_low"],
            candle_2_high=crt["candle_2_high"],
            candle_2_low=crt["candle_2_low"],
            candle_2_close=crt["candle_2_close"],
            candle_2_open=crt["candle_2_open"],
            sweep_price=sweep_price,
            timestamp=crt["timestamp"],
            candle_1_timestamp=crt["candle_1_timestamp"],
            timeframe=self.timeframe,
            body_ratio=crt.get("body_ratio", 0.0),
            htf_bias=htf_bias if htf_bias else "neutral"
        )
        
        # Log signal freshness for transparency
        minutes_fresh = signal_age.total_seconds() / 60
        print(f"   ✅ {pair} CRT signal is fresh ({minutes_fresh:.1f} min old)")
        
        # NOW update last candle time since we're sending an alert
        # This prevents duplicate alerts for the same CRT
        self.last_candle_time[pair] = completed_candle_time
        
        return alert
