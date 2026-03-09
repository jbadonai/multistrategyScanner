"""
Pivot detection module - implements Pine Script ta.pivothigh() and ta.pivotlow() logic
"""
from typing import List, Optional, Tuple
from models import MarketData


class PivotDetector:
    """Detects pivot highs and lows using the same logic as Pine Script"""
    
    def __init__(self, lookback: int):
        """
        Initialize pivot detector
        
        Args:
            lookback: Number of bars to look left and right for pivot detection
        """
        self.lookback = lookback
    
    def detect_pivot_high(self, data: List[MarketData], index: int) -> Optional[float]:
        """
        Detect pivot high at given index
        Pine Script: ta.pivothigh(length, length) checks if data[length] is highest
        in the window of [0, 2*length]
        
        Args:
            data: List of market data
            index: Current bar index to check (should be at lookback position from end)
            
        Returns:
            High price if pivot detected, None otherwise
        """
        # Need enough data on both sides
        if index < self.lookback or index >= len(data) - self.lookback:
            return None
        
        pivot_high = data[index].high
        
        # Check left side (lookback bars before)
        for i in range(index - self.lookback, index):
            if data[i].high > pivot_high:
                return None
        
        # Check right side (lookback bars after)
        for i in range(index + 1, index + self.lookback + 1):
            if data[i].high >= pivot_high:
                return None
        
        return pivot_high
    
    def detect_pivot_low(self, data: List[MarketData], index: int) -> Optional[float]:
        """
        Detect pivot low at given index
        Pine Script: ta.pivotlow(length, length) checks if data[length] is lowest
        in the window of [0, 2*length]
        
        Args:
            data: List of market data
            index: Current bar index to check (should be at lookback position from end)
            
        Returns:
            Low price if pivot detected, None otherwise
        """
        # Need enough data on both sides
        if index < self.lookback or index >= len(data) - self.lookback:
            return None
        
        pivot_low = data[index].low
        
        # Check left side (lookback bars before)
        for i in range(index - self.lookback, index):
            if data[i].low < pivot_low:
                return None
        
        # Check right side (lookback bars after)
        for i in range(index + 1, index + self.lookback + 1):
            if data[i].low <= pivot_low:
                return None
        
        return pivot_low
    
    def get_swing_zone(self, data: List[MarketData], index: int, 
                       swing_type: str, area_type: str) -> Optional[Tuple[float, float]]:
        """
        Calculate swing zone boundaries based on area type
        
        Args:
            data: List of market data
            index: Index of the pivot point
            swing_type: "high" or "low"
            area_type: "Wick Extremity" or "Full Range"
            
        Returns:
            Tuple of (top, bottom) prices, or None if invalid
        """
        if index >= len(data):
            return None
        
        candle = data[index]
        
        if swing_type == "high":
            top = candle.high
            if area_type == "Wick Extremity":
                # Bottom is the max of close and open (body top)
                btm = max(candle.close, candle.open)
            else:  # "Full Range"
                btm = candle.low
            return (top, btm)
        
        else:  # "low"
            btm = candle.low
            if area_type == "Wick Extremity":
                # Top is the min of close and open (body bottom)
                top = min(candle.close, candle.open)
            else:  # "Full Range"
                top = candle.high
            return (top, btm)
