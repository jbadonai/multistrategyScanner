"""
POI/FVG Strategy - Points of Interest with Fair Value Gaps
Wraps existing POI and FVG detection logic into the new strategy framework
"""

from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy, StrategySignal
from models import MarketData, SwingAlert, FVGAlert
from swing_tracker import SwingTracker


class POIFVGStrategy(BaseStrategy):
    """
    POI/FVG Strategy
    Monitors liquidity swings (POIs) and Fair Value Gap confirmations
    """
    
    def __init__(self, config):
        super().__init__("POI_FVG", config)
        
        self.tracker = SwingTracker()
        
        self.timeframe = config.POI_TIMEFRAME
        self.enable_daily_trend = config.POI_ENABLE_DAILY_TREND
        self.skip_without_trend = config.POI_SKIP_PAIRS_WITHOUT_TREND
        self.enable_fvg = config.POI_ENABLE_FVG
        
        # Duplicate prevention - track last signal per pair
        self.last_signals: Dict[str, Dict] = {}  # pair -> {type, price, time}
    
    def _is_enabled(self) -> bool:
        return self.config.ENABLE_POI_STRATEGY
    
    def _is_auto_trade_enabled(self) -> bool:
        return self.config.POI_AUTO_TRADE
    
    def get_required_data(self) -> Dict:
        timeframes = [self.timeframe]
        if self.enable_daily_trend:
            timeframes.append("1d")
        
        return {
            "timeframes": timeframes,
            "lookback": self.config.KLINES_LIMIT,
            "indicators": []
        }
    
    def scan_pair(self, pair: str, **kwargs) -> List[StrategySignal]:
        """
        Scan for POI/FVG signals
        
        Required kwargs:
            - candles: List[MarketData] for intraday timeframe
            - daily_candles: List[MarketData] for daily trend (optional)
        """
        candles = kwargs.get('candles', [])
        daily_candles = kwargs.get('daily_candles', [])
        
        if not candles:
            return []
        
        signals = []
        
        # Get daily trend context if enabled
        daily_context = None
        if self.enable_daily_trend and daily_candles:
            # Exclude today - use only completed days
            historical_daily = daily_candles[:-1]
            
            # Update daily trend context via SwingTracker
            daily_context = self.tracker.update_daily_context(pair, historical_daily)
            
            # Skip if no trend and configured to skip
            if self.skip_without_trend and daily_context is None:
                return []
        
        # Process swing detection and get alerts
        sweep_alerts, fvg_alerts = self.tracker.process_market_data(
            pair, candles, daily_context
        )
        
        # Convert sweep alerts to signals
        for alert in sweep_alerts:
            signal = self._create_sweep_signal(pair, alert, daily_context)
            if signal and not self._is_duplicate_signal(pair, signal):
                signals.append(signal)
                self._update_last_signal(pair, signal)
        
        # Convert FVG alerts to signals
        for alert in fvg_alerts:
            signal = self._create_fvg_signal(pair, alert, daily_context)
            if signal and not self._is_duplicate_signal(pair, signal):
                signals.append(signal)
                self._update_last_signal(pair, signal)
        
        return signals
    
    def _create_sweep_signal(self, pair: str, alert: SwingAlert, 
                            daily_context: Optional[Dict]) -> Optional[StrategySignal]:
        """Convert SwingAlert to StrategySignal"""
        
        is_high_sweep = alert.swing_type == "high"
        
        # Determine signal type based on sweep direction
        # High swept = bearish, Low swept = bullish
        signal_type = "SHORT" if is_high_sweep else "LONG"
        
        # Entry at current price (sweep just happened)
        entry_price = alert.current_price
        
        # Stop loss beyond the swing point
        if is_high_sweep:
            stop_loss = alert.swing_price * 1.002  # 0.2% above high
        else:
            stop_loss = alert.swing_price * 0.998  # 0.2% below low
        
        # Take profit at opposite side (simple target)
        # In real trading, you'd use more sophisticated targeting
        risk = abs(entry_price - stop_loss)
        take_profit = entry_price + (risk * 2.0 if not is_high_sweep else -risk * 2.0)
        
        # Build details
        details = {
            "Swing Type": alert.swing_type.upper(),
            "Swing Price": f"{alert.swing_price:.8f}",
            "Swing Count": str(alert.swing_count),
            "Zone Type": "POI" if daily_context else "Liquidity Swing"
        }
        
        if daily_context:
            details["Daily Trend"] = daily_context.get("trend", "").upper()
        
        # Confidence based on swing count and POI status
        if daily_context and alert.swing_count >= 2:
            confidence = "HIGH"
        elif alert.swing_count >= 2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        signal = StrategySignal(
            strategy_name="POI_FVG",
            pair=pair,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=alert.timestamp,
            timeframe=self.timeframe,
            confidence=confidence,
            details=details,
            auto_trade_enabled=self.auto_trade_enabled
        )
        
        return signal
    
    def _create_fvg_signal(self, pair: str, alert: FVGAlert,
                          daily_context: Optional[Dict]) -> Optional[StrategySignal]:
        """Convert FVGAlert to StrategySignal"""
        
        is_bullish = alert.fvg_type == "bullish"
        
        # Entry at FVG zone
        entry_price = (alert.gap_top + alert.gap_bottom) / 2
        
        # Stop loss below/above FVG gap
        if is_bullish:
            stop_loss = alert.gap_bottom * 0.998
        else:
            stop_loss = alert.gap_top * 1.002
        
        # Target based on risk
        risk = abs(entry_price - stop_loss)
        take_profit = entry_price + (risk * 2.5 if is_bullish else -risk * 2.5)
        
        # Build details
        details = {
            "FVG Type": alert.fvg_type.upper(),
            "Gap Top": f"{alert.gap_top:.8f}",
            "Gap Bottom": f"{alert.gap_bottom:.8f}",
            "Gap Size": f"{alert.gap_top - alert.gap_bottom:.8f}",
            "Body Ratio": f"{alert.body_ratio:.1f}",
            "Candles After Sweep": str(alert.candles_after_sweep)
        }
        
        signal = StrategySignal(
            strategy_name="POI_FVG",
            pair=pair,
            signal_type="LONG" if is_bullish else "SHORT",
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=alert.timestamp,
            timeframe=self.timeframe,
            confidence="HIGH",  # FVG is strong confirmation
            details=details,
            auto_trade_enabled=self.auto_trade_enabled
        )
        
        return signal
    
    def _is_duplicate_signal(self, pair: str, signal: StrategySignal) -> bool:
        """Check if signal is duplicate of recent signal"""
        if pair not in self.last_signals:
            return False
        
        last = self.last_signals[pair]
        
        # Same signal type
        if last.get("type") != signal.signal_type:
            return False
        
        # Similar price (within 0.3% for POI/FVG)
        price_diff = abs(signal.entry_price - last.get("price", 0)) / signal.entry_price
        if price_diff > 0.003:  # More than 0.3% different = new signal
            return False
        
        # Recent signal (within 3 minutes for faster timeframe)
        time_diff = datetime.now() - last.get("time", datetime.min)
        if time_diff > timedelta(minutes=3):
            return False
        
        # It's a duplicate!
        return True
    
    def _update_last_signal(self, pair: str, signal: StrategySignal):
        """Update last signal tracker"""
        self.last_signals[pair] = {
            "type": signal.signal_type,
            "price": signal.entry_price,
            "time": datetime.now()
        }
    
    def validate_signal(self, signal: StrategySignal) -> bool:
        """Validate POI/FVG signal before trading"""
        
        # Check R:R ratio
        if signal.risk_reward_ratio < 1.5:
            return False
        
        # Could add more validation here
        
        return True
