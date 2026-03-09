"""
Trend analyzer module for detecting market structure and trend direction
"""
from typing import List, Optional, Tuple
from models import MarketData
from datetime import datetime


class TrendAnalyzer:
    """Analyzes daily trend and identifies protected levels"""
    
    def __init__(self, lookback_days: int = 3):
        """
        Initialize trend analyzer
        
        Args:
            lookback_days: Number of days to look back for trend detection (2-3 recommended)
        """
        self.lookback_days = lookback_days
    
    def detect_trend(self, daily_candles: List[MarketData]) -> Optional[str]:
        """
        Detect trend by analyzing if previous highs/lows are being respected
        
        Uptrend: Previous lows are not taken out (higher lows)
        Downtrend: Previous highs are not taken out (lower highs)
        
        Args:
            daily_candles: List of daily candles (most recent last, excluding today)
            
        Returns:
            "uptrend", "downtrend", or None if unclear
        """
        if len(daily_candles) < self.lookback_days:
            return None
        
        # Get the last 2-3 days (excluding today)
        recent_days = daily_candles[-self.lookback_days:]
        
        # Check for uptrend: Each candle should not take out the previous candle's low
        # This means lows are being respected (higher lows structure)
        uptrend = True
        downtrend = True
        
        for i in range(1, len(recent_days)):
            current = recent_days[i]
            previous = recent_days[i-1]
            
            # If current low breaks previous low, not an uptrend
            if current.low < previous.low:
                uptrend = False
            
            # If current high breaks previous high, not a downtrend
            if current.high > previous.high:
                downtrend = False
        
        # Determine trend
        if uptrend and not downtrend:
            return "uptrend"
        elif downtrend and not uptrend:
            return "downtrend"
        else:
            # Mixed signals or consolidation
            return None
    
    def get_protected_level(self, daily_candles: List[MarketData], 
                           trend: str) -> Optional[float]:
        """
        Get the protected level based on trend
        
        Uptrend: Previous day's LOW (should not be broken downward)
        Downtrend: Previous day's HIGH (should not be broken upward)
        
        Args:
            daily_candles: List of daily candles (most recent last, excluding today)
            trend: "uptrend" or "downtrend"
            
        Returns:
            Protected level price or None
        """
        if len(daily_candles) == 0:
            return None
        
        previous_day = daily_candles[-1]  # Most recent completed day
        
        if trend == "uptrend":
            # In uptrend, previous day's LOW is protected (shouldn't break down)
            return previous_day.low
        elif trend == "downtrend":
            # In downtrend, previous day's HIGH is protected (shouldn't break up)
            return previous_day.high
        else:
            return None
    
    def get_daily_open(self, daily_candles: List[MarketData]) -> Optional[float]:
        """
        Get the opening price of the current day
        Uses previous day's close as today's open (correct for 24/7 crypto markets)
        
        Args:
            daily_candles: Daily candles (excluding today, most recent is yesterday)
            
        Returns:
            Opening price of today (previous day's close) or None
        """
        if len(daily_candles) == 0:
            return None
        
        # Previous day's close = Today's open (24/7 markets)
        previous_day = daily_candles[-1]
        return previous_day.close
    
    def is_between_open_and_protected(self, price_top: float, price_btm: float,
                                     daily_open: float, protected: float,
                                     trend: str) -> bool:
        """
        Check if a swing zone is between the daily open and protected level
        
        Args:
            price_top: Swing zone top
            price_btm: Swing zone bottom
            daily_open: Today's opening price
            protected: Protected level (prev day high/low)
            trend: "uptrend" or "downtrend"
            
        Returns:
            True if swing is in the POI zone
        """
        if trend == "uptrend":
            # In uptrend, we're looking for swings BELOW the open but ABOVE protected low
            # Wait, re-reading: "unmitigated liquidity swings between opening and protected"
            # Uptrend: protected = prev day HIGH (above), open = today's open (below)
            # So POIs are between open (lower) and protected high (upper)
            # We want swing highs in this zone that can provide resistance
            lower_bound = min(daily_open, protected)
            upper_bound = max(daily_open, protected)
            
        else:  # downtrend
            # Downtrend: protected = prev day LOW (below), open = today's open (above)
            # POIs are between protected low (lower) and open (upper)
            # We want swing lows in this zone that can provide support
            lower_bound = min(daily_open, protected)
            upper_bound = max(daily_open, protected)
        
        # Swing is in POI zone if any part of it overlaps with the zone
        # The swing zone is [price_btm, price_top]
        # We check if there's any overlap
        return not (price_top < lower_bound or price_btm > upper_bound)
    
    def format_trend_info(self, trend: Optional[str], protected: Optional[float],
                         daily_open: Optional[float]) -> str:
        """
        Format trend information for display
        
        Returns:
            Formatted string describing the trend context
        """
        if trend is None:
            return "📊 Trend: Unclear/Consolidation"
        
        trend_emoji = "📈" if trend == "uptrend" else "📉"
        trend_name = trend.upper()
        
        # Correct labeling: uptrend protects LOW, downtrend protects HIGH
        protected_label = "Previous Day Low" if trend == "uptrend" else "Previous Day High"
        
        info = f"{trend_emoji} Trend: {trend_name}\n"
        if protected is not None:
            info += f"🛡️ Protected Level ({protected_label}): {protected:.8f}\n"
        if daily_open is not None:
            info += f"🔓 Daily Open: {daily_open:.8f}\n"
        
        return info
