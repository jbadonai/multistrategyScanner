"""
Higher Timeframe (HTF) Trend Analyzer
Determines market bias on higher timeframes for CRT alignment
"""
from typing import Optional, List
from models import MarketData
import config


class HTFTrendAnalyzer:
    """Analyzes higher timeframe trend for CRT alignment"""
    
    def __init__(self):
        self.htf_timeframe = config.CRT_HTF_TIMEFRAME
        self.lookback = config.CRT_HTF_LOOKBACK
    
    def get_trend_bias(self, candles: List[MarketData]) -> Optional[str]:
        """
        Determine higher timeframe trend bias using reliable ICT/Smart Money methods
        
        Uses proven methods:
        1. Market Structure (Higher Highs/Higher Lows or Lower Highs/Lower Lows)
        2. Swing High/Low breaks
        3. Price action relative to key levels
        
        Args:
            candles: List of HTF candles (daily or weekly)
            
        Returns:
            "bullish", "bearish", or None if neutral/unclear
        """
        if not candles or len(candles) < 10:
            return None
        
        # Use recent candles for trend analysis
        recent_candles = candles[-self.lookback:] if len(candles) >= self.lookback else candles
        
        # Method 1: Market Structure (Most Reliable)
        structure_bias = self._analyze_market_structure(recent_candles)
        
        # Method 2: Higher High/Higher Low or Lower High/Lower Low pattern
        hl_pattern = self._analyze_hl_pattern(recent_candles)
        
        # Method 3: Trend from swing breaks
        swing_bias = self._analyze_swing_breaks(recent_candles)
        
        # Combine signals - need at least 2 out of 3 to confirm (conservative)
        bullish_votes = sum([
            structure_bias == "bullish",
            hl_pattern == "bullish",
            swing_bias == "bullish"
        ])
        
        bearish_votes = sum([
            structure_bias == "bearish",
            hl_pattern == "bearish",
            swing_bias == "bearish"
        ])
        
        # Require strong agreement (2 out of 3)
        if bullish_votes >= 2:
            return "bullish"
        elif bearish_votes >= 2:
            return "bearish"
        else:
            return None  # Neutral/unclear - don't trade counter-trend
    
    def _analyze_market_structure(self, candles: List[MarketData]) -> Optional[str]:
        """
        Analyze market structure properly using swing highs and swing lows
        
        Bullish Market Structure:
        - Series of higher swing highs AND higher swing lows
        - Most recent swing high > previous swing high
        - Most recent swing low > previous swing low
        
        Bearish Market Structure:
        - Series of lower swing highs AND lower swing lows
        - Most recent swing high < previous swing high
        - Most recent swing low < previous swing low
        
        Returns:
            "bullish", "bearish", or None
        """
        if len(candles) < 10:
            return None
        
        # Find swing highs (local peaks)
        swing_highs = []
        for i in range(2, len(candles) - 2):
            if (candles[i].high > candles[i-1].high and 
                candles[i].high > candles[i-2].high and
                candles[i].high > candles[i+1].high and 
                candles[i].high > candles[i+2].high):
                swing_highs.append((i, candles[i].high))
        
        # Find swing lows (local valleys)
        swing_lows = []
        for i in range(2, len(candles) - 2):
            if (candles[i].low < candles[i-1].low and 
                candles[i].low < candles[i-2].low and
                candles[i].low < candles[i+1].low and 
                candles[i].low < candles[i+2].low):
                swing_lows.append((i, candles[i].low))
        
        # Need at least 2 swing highs and 2 swing lows for comparison
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        # Compare most recent swing high to previous
        recent_sh = swing_highs[-1][1]
        prev_sh = swing_highs[-2][1]
        higher_highs = recent_sh > prev_sh
        lower_highs = recent_sh < prev_sh
        
        # Compare most recent swing low to previous
        recent_sl = swing_lows[-1][1]
        prev_sl = swing_lows[-2][1]
        higher_lows = recent_sl > prev_sl
        lower_lows = recent_sl < prev_sl
        
        # Determine trend
        if higher_highs and higher_lows:
            return "bullish"
        elif lower_highs and lower_lows:
            return "bearish"
        else:
            return None  # Choppy/unclear
    
    def _analyze_hl_pattern(self, candles: List[MarketData]) -> Optional[str]:
        """
        Analyze if making consistent higher highs/lows or lower highs/lows
        
        More lenient than market structure - looks at overall pattern
        
        Returns:
            "bullish", "bearish", or None
        """
        if len(candles) < 6:
            return None
        
        # Split into two halves and compare
        mid = len(candles) // 2
        first_half = candles[:mid]
        second_half = candles[mid:]
        
        # Get average high and low for each half
        first_avg_high = sum(c.high for c in first_half) / len(first_half)
        first_avg_low = sum(c.low for c in first_half) / len(first_half)
        
        second_avg_high = sum(c.high for c in second_half) / len(second_half)
        second_avg_low = sum(c.low for c in second_half) / len(second_half)
        
        # Check if second half is higher (bullish) or lower (bearish)
        highs_rising = second_avg_high > first_avg_high * 1.005  # 0.5% threshold
        lows_rising = second_avg_low > first_avg_low * 1.005
        
        highs_falling = second_avg_high < first_avg_high * 0.995
        lows_falling = second_avg_low < first_avg_low * 0.995
        
        if highs_rising and lows_rising:
            return "bullish"
        elif highs_falling and lows_falling:
            return "bearish"
        else:
            return None
    
    def _analyze_swing_breaks(self, candles: List[MarketData]) -> Optional[str]:
        """
        Analyze trend based on swing high/low breaks
        
        Bullish: Breaking above previous swing highs
        Bearish: Breaking below previous swing lows
        
        Returns:
            "bullish", "bearish", or None
        """
        if len(candles) < 8:
            return None
        
        # Get last 8 candles
        recent = candles[-8:]
        
        # Find the highest high in the first 6 candles
        early_highs = [c.high for c in recent[:6]]
        early_high = max(early_highs)
        
        # Find the lowest low in the first 6 candles
        early_lows = [c.low for c in recent[:6]]
        early_low = min(early_lows)
        
        # Check if recent price (last 2 candles) broke these levels
        recent_price = recent[-1].close
        recent_high = max(c.high for c in recent[-2:])
        recent_low = min(c.low for c in recent[-2:])
        
        # Bullish: breaking above early high
        if recent_high > early_high and recent_price > early_high * 0.998:
            return "bullish"
        
        # Bearish: breaking below early low
        if recent_low < early_low and recent_price < early_low * 1.002:
            return "bearish"
        
        return None
    
    def is_crt_aligned(self, crt_type: str, htf_bias: Optional[str]) -> bool:
        """
        Check if CRT signal is aligned with HTF bias
        
        Args:
            crt_type: "bullish" or "bearish"
            htf_bias: "bullish", "bearish", or None
            
        Returns:
            True if aligned or HTF bias is neutral, False if misaligned
        """
        # If HTF bias is neutral/unclear, allow the trade
        if htf_bias is None:
            return True
        
        # CRT must match HTF bias
        return crt_type == htf_bias
