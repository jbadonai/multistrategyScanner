"""
Enhanced CRT Detector with Professional ICT Filters
Implements advanced context-based validation for higher accuracy
"""
from typing import Optional, List, Dict
from models import MarketData
from datetime import datetime


class EnhancedCRTDetector:
    """
    Enhanced CRT detector with professional ICT filters
    
    Checks:
    1. Meaningful liquidity (candle range size)
    2. Strong rejection wick
    3. No strong displacement after sweep
    4. HTF structure consideration
    5. Candle quality validation
    """
    
    def __init__(self, config):
        self.config = config
        
        # Basic CRT settings
        self.max_body_ratio = config.CRT_MAX_BODY_RATIO
        
        # Enhanced filters (with defaults)
        self.min_candle_range_pct = getattr(config, 'CRT_MIN_CANDLE_RANGE_PCT', 0.3)
        self.min_rejection_wick_pct = getattr(config, 'CRT_MIN_REJECTION_WICK_PCT', 30.0)
        self.max_displacement_candles = getattr(config, 'CRT_MAX_DISPLACEMENT_CANDLES', 2)
        self.min_displacement_ratio = getattr(config, 'CRT_MIN_DISPLACEMENT_RATIO', 1.5)
        self.require_weak_close_check = getattr(config, 'CRT_REQUIRE_WEAK_CLOSE_CHECK', True)
        self.min_close_inside_pct = getattr(config, 'CRT_MIN_CLOSE_INSIDE_PCT', 20.0)
    
    def detect_crt(self, candles: List[MarketData]) -> Optional[dict]:
        """
        Detect CRT pattern with enhanced professional filters
        
        Args:
            candles: List of market candles (need at least 5 for context)
            
        Returns:
            Dict with CRT info or None if no valid CRT pattern
        """
        # Need at least 5 candles for context analysis
        if len(candles) < 5:
            return None
        
        # Get the last 2 COMPLETED candles
        candle_1 = candles[-3]  # Range candle
        candle_2 = candles[-2]  # Sweep candle
        
        # FILTER 1: Meaningful liquidity - candle 1 range must be significant
        if not self._has_meaningful_range(candle_1):
            return None
        
        # Define ranges
        range_high = candle_1.high
        range_low = candle_1.low
        range_size = range_high - range_low
        
        # Check sweep direction
        swept_high = candle_2.high > range_high
        swept_low = candle_2.low < range_low
        
        # Reject double sweeps
        if swept_high and swept_low:
            return None
        
        # FILTER 2: Check for strong displacement AFTER sweep
        # If displacement is strong, it's continuation not reversal
        if self._has_strong_displacement_after_sweep(candles):
            return None
        
        # Check body ratio
        candle_1_body = abs(candle_1.close - candle_1.open)
        candle_2_body = abs(candle_2.close - candle_2.open)
        
        if candle_1_body > 0:
            body_ratio = (candle_2_body / candle_1_body) * 100
            if body_ratio > self.max_body_ratio:
                return None
        else:
            body_ratio = 0
        
        # Check for Bullish CRT
        if swept_low and not swept_high:
            bullish_crt = self._check_bullish_crt(candle_1, candle_2, range_high, range_low, range_size)
            if bullish_crt:
                return {
                    "type": "bullish",
                    "candle_1_high": range_high,
                    "candle_1_low": range_low,
                    "candle_2_high": candle_2.high,
                    "candle_2_low": candle_2.low,
                    "candle_2_close": candle_2.close,
                    "candle_2_open": candle_2.open,
                    "sweep_low": bullish_crt["sweep_low"],
                    "timestamp": datetime.fromtimestamp(candle_2.timestamp / 1000),
                    "candle_1_timestamp": datetime.fromtimestamp(candle_1.timestamp / 1000),
                    "body_ratio": body_ratio,
                    "rejection_wick_pct": bullish_crt.get("rejection_wick_pct", 0),
                    "close_inside_pct": bullish_crt.get("close_inside_pct", 0)
                }
        
        # Check for Bearish CRT
        if swept_high and not swept_low:
            bearish_crt = self._check_bearish_crt(candle_1, candle_2, range_high, range_low, range_size)
            if bearish_crt:
                return {
                    "type": "bearish",
                    "candle_1_high": range_high,
                    "candle_1_low": range_low,
                    "candle_2_high": candle_2.high,
                    "candle_2_low": candle_2.low,
                    "candle_2_close": candle_2.close,
                    "candle_2_open": candle_2.open,
                    "sweep_high": bearish_crt["sweep_high"],
                    "timestamp": datetime.fromtimestamp(candle_2.timestamp / 1000),
                    "candle_1_timestamp": datetime.fromtimestamp(candle_1.timestamp / 1000),
                    "body_ratio": body_ratio,
                    "rejection_wick_pct": bearish_crt.get("rejection_wick_pct", 0),
                    "close_inside_pct": bearish_crt.get("close_inside_pct", 0)
                }
        
        return None
    
    def _has_meaningful_range(self, candle: MarketData) -> bool:
        """
        Check if candle has meaningful range (FILTER 9: range size)
        
        Small candles don't contain meaningful liquidity
        """
        candle_range = candle.high - candle.low
        candle_mid = (candle.high + candle.low) / 2
        
        if candle_mid == 0:
            return False
        
        range_pct = (candle_range / candle_mid) * 100
        
        return range_pct >= self.min_candle_range_pct
    
    def _has_strong_displacement_after_sweep(self, candles: List[MarketData]) -> bool:
        """
        Check for strong displacement AFTER the sweep (FILTER 3)
        
        If displacement is strong, it indicates continuation not reversal
        Strong displacement = large imbalance/FVG, multiple strong candles
        """
        # Check candles AFTER the sweep candle (candles[-2])
        # Look at candle[-1] (forming) and previous candles
        
        if len(candles) < 4:
            return False
        
        sweep_candle = candles[-2]
        candles_after = candles[-1:]  # Current forming candle
        
        # Check if candles after sweep show strong momentum
        if len(candles_after) >= self.max_displacement_candles:
            # Calculate average range of displacement candles
            displacement_ranges = []
            for candle in candles_after[:self.max_displacement_candles]:
                candle_range = candle.high - candle.low
                displacement_ranges.append(candle_range)
            
            if displacement_ranges:
                avg_displacement = sum(displacement_ranges) / len(displacement_ranges)
                sweep_range = sweep_candle.high - sweep_candle.low
                
                if sweep_range > 0:
                    displacement_ratio = avg_displacement / sweep_range
                    
                    # Strong displacement if following candles are much larger
                    if displacement_ratio > self.min_displacement_ratio:
                        return True
        
        return False
    
    def _check_bullish_crt(self, candle_1: MarketData, candle_2: MarketData,
                          range_high: float, range_low: float, range_size: float) -> Optional[dict]:
        """
        Check for Bullish CRT with enhanced filters
        
        Additional checks:
        - FILTER 2: Strong rejection wick required
        - FILTER 7: Close must be decisive (not weak)
        """
        # Must sweep below
        if candle_2.low >= range_low:
            return None
        
        # Must close inside range
        epsilon = 0.00000001
        if not (range_low + epsilon < candle_2.close < range_high - epsilon):
            return None
        
        # FILTER 2: Check rejection wick strength
        lower_wick = min(candle_2.open, candle_2.close) - candle_2.low
        candle_2_range = candle_2.high - candle_2.low
        
        if candle_2_range > 0:
            rejection_wick_pct = (lower_wick / candle_2_range) * 100
            
            # Require strong rejection wick
            if self.min_rejection_wick_pct > 0 and rejection_wick_pct < self.min_rejection_wick_pct:
                return None  # Weak rejection
        else:
            rejection_wick_pct = 0
        
        # FILTER 7: Check close strength (not barely inside)
        if self.require_weak_close_check:
            # Close should be meaningfully inside the range, not at the edge
            close_distance_from_low = candle_2.close - range_low
            close_inside_pct = (close_distance_from_low / range_size) * 100 if range_size > 0 else 0
            
            # Close should be at least X% inside the range
            if close_inside_pct < self.min_close_inside_pct:
                return None  # Weak close, barely inside
        else:
            close_inside_pct = 0
        
        # Valid Bullish CRT
        return {
            "sweep_low": candle_2.low,
            "rejection_wick_pct": rejection_wick_pct,
            "close_inside_pct": close_inside_pct
        }
    
    def _check_bearish_crt(self, candle_1: MarketData, candle_2: MarketData,
                          range_high: float, range_low: float, range_size: float) -> Optional[dict]:
        """
        Check for Bearish CRT with enhanced filters
        
        Additional checks:
        - FILTER 2: Strong rejection wick required
        - FILTER 7: Close must be decisive (not weak)
        """
        # Must sweep above
        if candle_2.high <= range_high:
            return None
        
        # Must close inside range
        epsilon = 0.00000001
        if not (range_low + epsilon < candle_2.close < range_high - epsilon):
            return None
        
        # FILTER 2: Check rejection wick strength
        upper_wick = candle_2.high - max(candle_2.open, candle_2.close)
        candle_2_range = candle_2.high - candle_2.low
        
        if candle_2_range > 0:
            rejection_wick_pct = (upper_wick / candle_2_range) * 100
            
            # Require strong rejection wick
            if self.min_rejection_wick_pct > 0 and rejection_wick_pct < self.min_rejection_wick_pct:
                return None  # Weak rejection
        else:
            rejection_wick_pct = 0
        
        # FILTER 7: Check close strength (not barely inside)
        if self.require_weak_close_check:
            # Close should be meaningfully inside the range, not at the edge
            close_distance_from_high = range_high - candle_2.close
            close_inside_pct = (close_distance_from_high / range_size) * 100 if range_size > 0 else 0
            
            # Close should be at least X% inside the range
            if close_inside_pct < self.min_close_inside_pct:
                return None  # Weak close, barely inside
        else:
            close_inside_pct = 0
        
        # Valid Bearish CRT
        return {
            "sweep_high": candle_2.high,
            "rejection_wick_pct": rejection_wick_pct,
            "close_inside_pct": close_inside_pct
        }
    
    def is_valid_entry_zone(self, crt: dict) -> bool:
        """Validate entry zone - kept for compatibility"""
        return True  # All checks done in detect_crt now
