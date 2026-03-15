"""
CRT Strategy - Change of Retail Tendency (ICT Concept)
Wraps existing CRT detection logic into the new strategy framework
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy, StrategySignal
from models import MarketData, CRTAlert
from htf_trend_analyzer import HTFTrendAnalyzer


class CRTStrategy(BaseStrategy):
    """
    CRT (Change of Retail Tendency) Strategy
    Detects liquidity sweeps with close back in range on 4H timeframe
    Now with enhanced professional ICT filters
    """
    
    def __init__(self, config):
        super().__init__("CRT", config)
        
        # Choose detector based on config
        if hasattr(config, 'CRT_USE_ENHANCED_FILTERS') and config.CRT_USE_ENHANCED_FILTERS:
            from enhanced_crt_detector import EnhancedCRTDetector
            self.crt_detector = EnhancedCRTDetector(config)
            print("   ✅ CRT: Using ENHANCED detector (professional ICT filters)")
        else:
            from crt_detector import CRTDetector
            self.crt_detector = CRTDetector()
            print("   ℹ️  CRT: Using BASIC detector")
        
        self.htf_analyzer = HTFTrendAnalyzer() if config.CRT_REQUIRE_HTF_ALIGNMENT else None
        self.timeframe = config.CRT_TIMEFRAME
        self.max_signal_age = timedelta(minutes=config.CRT_MAX_SIGNAL_AGE_MINUTES)
        
        # Track processed candles to avoid duplicates
        self.last_candle_time: Dict[str, int] = {}
        self.htf_bias_cache: Dict[str, Optional[str]] = {}
    
    def _is_enabled(self) -> bool:
        return self.config.ENABLE_CRT_STRATEGY
    
    def _is_auto_trade_enabled(self) -> bool:
        return self.config.CRT_AUTO_TRADE
    
    def get_required_data(self) -> Dict:
        timeframes = [self.timeframe]
        if self.config.CRT_REQUIRE_HTF_ALIGNMENT:
            timeframes.append(self.config.CRT_HTF_TIMEFRAME)
        
        return {
            "timeframes": timeframes,
            "lookback": 10,
            "indicators": []
        }
    
    def scan_pair(self, pair: str, **kwargs) -> List[StrategySignal]:
        """
        Scan for CRT patterns
        
        Required kwargs:
            - candles: List[MarketData] for 4H timeframe
            - htf_candles: List[MarketData] for HTF (optional)
        """
        candles = kwargs.get('candles', [])
        htf_candles = kwargs.get('htf_candles', [])
        
        if not candles or len(candles) < 3:
            return []
        
        # Initialize tracking for this pair
        if pair not in self.last_candle_time:
            self.last_candle_time[pair] = 0
        
        # Check completed candle
        completed_candle_time = candles[-2].timestamp
        
        # Skip if already processed
        if completed_candle_time == self.last_candle_time.get(pair):
            return []
        
        # Get HTF bias if required
        htf_bias = None
        if self.config.CRT_REQUIRE_HTF_ALIGNMENT and self.htf_analyzer and htf_candles:
            htf_bias = self.htf_analyzer.get_trend_bias(htf_candles)
            self.htf_bias_cache[pair] = htf_bias
        
        # Detect CRT pattern
        crt = self.crt_detector.detect_crt(candles)
        
        if crt is None:
            return []
        
        # Check HTF alignment
        if self.config.CRT_REQUIRE_HTF_ALIGNMENT and self.htf_analyzer:
            if not self.htf_analyzer.is_crt_aligned(crt["type"], htf_bias):
                return []
        
        # Check signal freshness
        signal_time = crt["timestamp"]
        current_time = datetime.now()
        signal_age = current_time - signal_time
        
        if signal_age > self.max_signal_age:
            return []
        
        # Validate entry zone
        if not self.crt_detector.is_valid_entry_zone(crt):
            return []
        
        # Update processed candle tracker
        self.last_candle_time[pair] = completed_candle_time
        
        # Add candles to CRT data for visualization
        crt["candles"] = candles[-5:] if len(candles) >= 5 else candles
        
        # Convert to StrategySignal
        signal = self._create_signal(pair, crt, htf_bias)
        
        return [signal] if signal else []
    
    def _create_signal(self, pair: str, crt: Dict, htf_bias: Optional[str]) -> StrategySignal:
        """Convert CRT detection to StrategySignal"""
        
        is_bullish = crt["type"] == "bullish"
        
        # Entry and exits
        entry_price = crt["candle_2_close"]
        stop_loss = crt.get("sweep_low") if is_bullish else crt.get("sweep_high")
        
        # Take profit = opposite liquidity
        take_profit = crt["candle_1_high"] if is_bullish else crt["candle_1_low"]
        
        # Determine confidence based on HTF alignment
        confidence = "HIGH" if htf_bias == crt["type"] else "MEDIUM"
        
        # Build details
        details = {
            "Candle 1 High": f"{crt['candle_1_high']:.8f}",
            "Candle 1 Low": f"{crt['candle_1_low']:.8f}",
            "Sweep Price": f"{stop_loss:.8f}",
            "Body Ratio": f"{crt.get('body_ratio', 0):.1f}%",
            "HTF Trend": htf_bias.upper() if htf_bias else "NEUTRAL",
            # Add raw CRT data for chart generation
            "crt_pattern": crt,  # Store full CRT data for visualization
            # Add quality metrics if available
            "Rejection Wick": f"{crt.get('rejection_wick_pct', 0):.1f}%",
            "Close Inside": f"{crt.get('close_inside_pct', 0):.1f}%"
        }
        
        signal = StrategySignal(
            strategy_name="CRT",
            pair=pair,
            signal_type="LONG" if is_bullish else "SHORT",
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=crt["timestamp"],
            timeframe=self.timeframe,
            confidence=confidence,
            details=details,
            auto_trade_enabled=self.auto_trade_enabled
        )
        
        return signal
    
    def validate_signal(self, signal: StrategySignal) -> bool:
        """Validate CRT signal before trading"""
        
        # Check signal age
        age = datetime.now() - signal.timestamp
        if age > self.max_signal_age:
            return False
        
        # Check R:R ratio
        if signal.risk_reward_ratio < 1.0:
            return False
        
        return True
