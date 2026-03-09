"""
FVG (Fair Value Gap) detector module
Detects valid FVG formations after liquidity sweeps
"""
from typing import List, Optional, Tuple
from models import MarketData
from datetime import datetime


class FVGDetector:
    """Detects Fair Value Gap formations"""
    
    def __init__(self, lookback_candles: int = 20):
        """
        Initialize FVG detector
        
        Args:
            lookback_candles: Number of candles to watch for FVG after sweep
        """
        self.lookback_candles = lookback_candles
    
    def get_candle_body(self, candle: MarketData) -> float:
        """
        Calculate candle body size (abs difference between open and close)
        
        Args:
            candle: Market candle data
            
        Returns:
            Body size
        """
        return abs(candle.close - candle.open)
    
    def detect_fvg(self, candles: List[MarketData], start_index: int) -> Optional[dict]:
        """
        Detect FVG formation in a 3-candle pattern
        
        FVG Requirements:
        1. Gap between candle 1 and candle 3
        2. Candle 2 creates the gap (strong momentum candle)
        3. Candle 3 closes within the range of candle 2
        4. Candle 2 body >= 2x candle 3 body
        
        Args:
            candles: List of market candles
            start_index: Index to start looking for FVG (usually after sweep)
            
        Returns:
            Dict with FVG info or None if no valid FVG found
        """
        # Need at least 3 candles from start_index
        if start_index + 2 >= len(candles):
            return None
        
        # Check each possible 3-candle pattern within lookback
        end_index = min(start_index + self.lookback_candles, len(candles) - 2)
        
        for i in range(start_index, end_index):
            # Need 3 consecutive candles
            if i + 2 >= len(candles):
                break
            
            candle_1 = candles[i]
            candle_2 = candles[i + 1]
            candle_3 = candles[i + 2]
            
            # Check for bullish FVG (gap up)
            bullish_fvg = self._check_bullish_fvg(candle_1, candle_2, candle_3)
            if bullish_fvg:
                return {
                    "type": "bullish",
                    "candle_1_index": i,
                    "candle_2_index": i + 1,
                    "candle_3_index": i + 2,
                    "gap_top": bullish_fvg["gap_top"],
                    "gap_bottom": bullish_fvg["gap_bottom"],
                    "candle_2_body": self.get_candle_body(candle_2),
                    "candle_3_body": self.get_candle_body(candle_3),
                    "timestamp": datetime.fromtimestamp(candle_3.timestamp / 1000),
                    "candles_after_sweep": i - start_index + 3
                }
            
            # Check for bearish FVG (gap down)
            bearish_fvg = self._check_bearish_fvg(candle_1, candle_2, candle_3)
            if bearish_fvg:
                return {
                    "type": "bearish",
                    "candle_1_index": i,
                    "candle_2_index": i + 1,
                    "candle_3_index": i + 2,
                    "gap_top": bearish_fvg["gap_top"],
                    "gap_bottom": bearish_fvg["gap_bottom"],
                    "candle_2_body": self.get_candle_body(candle_2),
                    "candle_3_body": self.get_candle_body(candle_3),
                    "timestamp": datetime.fromtimestamp(candle_3.timestamp / 1000),
                    "candles_after_sweep": i - start_index + 3
                }
        
        return None
    
    def _check_bullish_fvg(self, candle_1: MarketData, candle_2: MarketData, 
                          candle_3: MarketData) -> Optional[dict]:
        """
        Check for bullish FVG pattern
        
        Bullish FVG:
        - Gap between candle 1 high and candle 3 low
        - Candle 2 is strong bullish (creates gap)
        - Candle 3 closes within candle 2 range
        - Candle 2 body >= 2x candle 3 body
        
        Returns:
            Dict with gap info or None
        """
        # Gap exists: candle 3 low > candle 1 high
        if candle_3.low <= candle_1.high:
            return None
        
        # Candle 2 must be bullish (close > open)
        if candle_2.close <= candle_2.open:
            return None
        
        # Candle 3 must close within candle 2 range
        if not (candle_2.low <= candle_3.close <= candle_2.high):
            return None
        
        # Candle 2 body must be at least 2x candle 3 body
        body_2 = self.get_candle_body(candle_2)
        body_3 = self.get_candle_body(candle_3)
        
        if body_2 < 2 * body_3:
            return None
        
        # Valid bullish FVG
        return {
            "gap_top": candle_3.low,
            "gap_bottom": candle_1.high
        }
    
    def _check_bearish_fvg(self, candle_1: MarketData, candle_2: MarketData, 
                          candle_3: MarketData) -> Optional[dict]:
        """
        Check for bearish FVG pattern
        
        Bearish FVG:
        - Gap between candle 1 low and candle 3 high
        - Candle 2 is strong bearish (creates gap)
        - Candle 3 closes within candle 2 range
        - Candle 2 body >= 2x candle 3 body
        
        Returns:
            Dict with gap info or None
        """
        # Gap exists: candle 3 high < candle 1 low
        if candle_3.high >= candle_1.low:
            return None
        
        # Candle 2 must be bearish (close < open)
        if candle_2.close >= candle_2.open:
            return None
        
        # Candle 3 must close within candle 2 range
        if not (candle_2.low <= candle_3.close <= candle_2.high):
            return None
        
        # Candle 2 body must be at least 2x candle 3 body
        body_2 = self.get_candle_body(candle_2)
        body_3 = self.get_candle_body(candle_3)
        
        if body_2 < 2 * body_3:
            return None
        
        # Valid bearish FVG
        return {
            "gap_top": candle_1.low,
            "gap_bottom": candle_3.high
        }
    
    def format_fvg_info(self, fvg: dict, pair: str) -> str:
        """
        Format FVG information for display
        
        Args:
            fvg: FVG detection result
            pair: Trading pair
            
        Returns:
            Formatted string
        """
        fvg_type = "🟢 Bullish FVG" if fvg["type"] == "bullish" else "🔴 Bearish FVG"
        
        info = f"{fvg_type} detected for {pair}\n"
        info += f"Gap Zone: {fvg['gap_bottom']:.8f} - {fvg['gap_top']:.8f}\n"
        info += f"Candle 2 Body: {fvg['candle_2_body']:.8f}\n"
        info += f"Candle 3 Body: {fvg['candle_3_body']:.8f}\n"
        info += f"Ratio: {fvg['candle_2_body'] / fvg['candle_3_body']:.2f}x\n"
        info += f"Formed {fvg['candles_after_sweep']} candles after sweep\n"
        info += f"Time: {fvg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return info
