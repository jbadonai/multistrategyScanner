"""
Swing tracker module for managing and monitoring liquidity swing points
"""
from typing import Dict, List, Set, Optional
from datetime import datetime
from models import SwingPoint, MarketData, SwingAlert, FVGAlert
from pivot_detector import PivotDetector
from poi_manager import POIManager
from trend_analyzer import TrendAnalyzer
from fvg_tracker import FVGTracker
import config


class SwingTracker:
    """Tracks liquidity swing points and detects when they are swept"""
    
    def __init__(self):
        self.pivot_detector = PivotDetector(config.PIVOT_LOOKBACK)
        self.swing_points: Dict[str, Set[SwingPoint]] = {}  # pair -> set of swing points
        self.lookback = config.PIVOT_LOOKBACK
        self.swing_area = config.SWING_AREA
        self.filter_by = config.FILTER_BY
        self.filter_value = config.FILTER_VALUE
        
        # POI tracking (new feature)
        self.poi_enabled = config.ENABLE_DAILY_TREND
        self.poi_manager = POIManager()
        self.trend_analyzer = TrendAnalyzer(config.TREND_LOOKBACK_DAYS)
        
        # FVG tracking (new feature)
        self.fvg_tracker = FVGTracker()
    
    def initialize_pair(self, pair: str):
        """Initialize tracking for a new pair"""
        if pair not in self.swing_points:
            self.swing_points[pair] = set()
        if self.poi_enabled:
            self.poi_manager.initialize_pair(pair)
    
    def update_daily_context(self, pair: str, daily_candles: List[MarketData]) -> Optional[Dict]:
        """
        Update daily trend context and identify POI zone
        
        Args:
            pair: Trading pair
            daily_candles: Daily candles (excluding today, most recent is yesterday)
            
        Returns:
            Dict with trend info or None if trend unclear
        """
        if not self.poi_enabled or len(daily_candles) < config.TREND_LOOKBACK_DAYS:
            return None
        
        # Detect trend from previous days (excluding today)
        trend = self.trend_analyzer.detect_trend(daily_candles)
        
        if trend is None:
            return None
        
        # Get protected level (prev day high/low)
        protected = self.trend_analyzer.get_protected_level(daily_candles, trend)
        
        # Get daily open (previous day's close)
        daily_open = self.trend_analyzer.get_daily_open(daily_candles)
        
        if protected is None or daily_open is None:
            return None
        
        # Start new POI session
        self.poi_manager.start_new_session(
            pair, trend, protected, daily_open, 
            datetime.now()  # Use current time for session
        )
        
        return {
            "trend": trend,
            "protected": protected,
            "daily_open": daily_open
        }
    
    def process_market_data(self, pair: str, data: List[MarketData], 
                           daily_context: Optional[Dict] = None) -> tuple:
        """
        Process market data to detect new swings and check for swept liquidity
        Also checks for FVG formations after sweeps
        
        Args:
            pair: Trading pair symbol
            data: List of market data (must have enough for pivot detection)
            daily_context: Optional dict with trend, protected, daily_open for POI mode
            
        Returns:
            Tuple of (sweep_alerts, fvg_alerts)
        """
        self.initialize_pair(pair)
        sweep_alerts = []
        fvg_alerts = []
        
        # Need enough data for pivot detection
        if len(data) < self.lookback * 2 + 1:
            return (sweep_alerts, fvg_alerts)
        
        # Check for new pivot points at lookback position from end
        pivot_index = len(data) - self.lookback - 1
        
        # Detect pivot high
        if config.SHOW_SWING_HIGH:
            pivot_high = self.pivot_detector.detect_pivot_high(data, pivot_index)
            if pivot_high is not None:
                swing_zone = self.pivot_detector.get_swing_zone(
                    data, pivot_index, "high", self.swing_area
                )
                if swing_zone:
                    swing = self._create_swing_point(pair, "high", swing_zone, 
                                                    pivot_index, data[pivot_index])
                    
                    # In POI mode, only add if in POI zone
                    if self.poi_enabled and daily_context:
                        if self._is_poi(swing, daily_context):
                            self.poi_manager.add_poi(pair, swing)
                            self.swing_points[pair].add(swing)
                    else:
                        # Original mode: add all swings
                        self.swing_points[pair].add(swing)
        
        # Detect pivot low
        if config.SHOW_SWING_LOW:
            pivot_low = self.pivot_detector.detect_pivot_low(data, pivot_index)
            if pivot_low is not None:
                swing_zone = self.pivot_detector.get_swing_zone(
                    data, pivot_index, "low", self.swing_area
                )
                if swing_zone:
                    swing = self._create_swing_point(pair, "low", swing_zone, 
                                                    pivot_index, data[pivot_index])
                    
                    # In POI mode, only add if in POI zone
                    if self.poi_enabled and daily_context:
                        if self._is_poi(swing, daily_context):
                            self.poi_manager.add_poi(pair, swing)
                            self.swing_points[pair].add(swing)
                    else:
                        # Original mode: add all swings
                        self.swing_points[pair].add(swing)
        
        # Update counts for existing swings
        for i in range(self.lookback, len(data) - 1):
            candle = data[i]
            self._update_swing_counts(pair, candle)
        
        # Check for swept liquidity
        current_candle = data[-1]
        current_index = len(data) - 1
        
        if self.poi_enabled and daily_context:
            # POI mode: only check POIs
            swept_swings = self._check_swept_pois(pair, current_candle, daily_context)
        else:
            # Original mode: check all swings
            swept_swings = self._check_swept_liquidity(pair, current_candle)
        
        # Create sweep alerts
        for swing in swept_swings:
            alert = SwingAlert(
                pair=pair,
                swing_type=swing.swing_type,
                swing_price_top=swing.price_top,
                swing_price_btm=swing.price_btm,
                sweep_price=current_candle.close,
                swing_timestamp=swing.timestamp,
                sweep_timestamp=datetime.fromtimestamp(current_candle.timestamp / 1000),
                count=swing.count,
                volume=swing.volume
            )
            sweep_alerts.append(alert)
            
            # Add sweep to FVG tracker
            if config.ENABLE_FVG_DETECTION:
                self.fvg_tracker.add_sweep(pair, alert, current_index)
        
        # Check for FVG formations
        if config.ENABLE_FVG_DETECTION:
            fvg_alerts = self.fvg_tracker.check_for_fvg(pair, data, current_index)
        
        return (sweep_alerts, fvg_alerts)
    
    def _create_swing_point(self, pair: str, swing_type: str, 
                           swing_zone: tuple, index: int, candle: MarketData) -> SwingPoint:
        """Create a new swing point (doesn't add to tracking yet)"""
        top, btm = swing_zone
        
        return SwingPoint(
            pair=pair,
            swing_type=swing_type,
            price_top=top,
            price_btm=btm,
            bar_index=index,
            timestamp=datetime.fromtimestamp(candle.timestamp / 1000),
            count=0,
            volume=0.0,
            crossed=False
        )
    
    def _is_poi(self, swing: SwingPoint, daily_context: Dict) -> bool:
        """Check if a swing qualifies as a POI based on daily context"""
        return self.trend_analyzer.is_between_open_and_protected(
            swing.price_top,
            swing.price_btm,
            daily_context["daily_open"],
            daily_context["protected"],
            daily_context["trend"]
        )
    
    def _update_swing_counts(self, pair: str, candle: MarketData):
        """Update count and volume for swings that the candle touches"""
        for swing in self.swing_points[pair]:
            if not swing.crossed and swing.is_in_zone(candle.high, candle.low):
                swing.update_metrics(candle.volume)
    
    def _check_swept_liquidity(self, pair: str, current_candle: MarketData) -> List[SwingPoint]:
        """
        Check which swing points have been swept by current price
        CRITICAL: Only swings that have accumulated enough touches/volume qualify as liquidity
        
        Args:
            pair: Trading pair
            current_candle: Current market candle
            
        Returns:
            List of swept swing points (only those that qualified as liquidity zones)
        """
        swept = []
        to_remove = []
        
        for swing in self.swing_points[pair]:
            # Skip if already marked as crossed
            if swing.crossed:
                continue
            
            # CRITICAL LIQUIDITY FILTER: Only swings that meet filter criteria are liquidity zones
            # This replicates the Pine Script logic where swings are only tracked/alerted if they
            # cross the filter threshold (ta.crossover(target, filterValue))
            filter_target = swing.count if self.filter_by == "Count" else swing.volume
            
            # If swing hasn't built up liquidity yet, skip it (not a liquidity zone yet)
            if filter_target <= self.filter_value:
                continue
            
            # Check if price has swept the swing (only matters if it's a liquidity zone)
            if swing.is_swept(current_candle.close):
                swing.crossed = True
                swept.append(swing)
                to_remove.append(swing)
        
        # Remove swept swings from tracking
        for swing in to_remove:
            self.swing_points[pair].discard(swing)
        
        return swept
    
    def _check_swept_pois(self, pair: str, current_candle: MarketData, 
                         daily_context: Dict) -> List[SwingPoint]:
        """
        Check which POIs have been mitigated
        
        Args:
            pair: Trading pair
            current_candle: Current market candle
            daily_context: Daily trend context
            
        Returns:
            List of mitigated POIs
        """
        mitigated = []
        active_pois = self.poi_manager.get_active_pois(pair)
        
        for poi in active_pois:
            # Check if POI meets filter criteria
            filter_target = poi.count if self.filter_by == "Count" else poi.volume
            if filter_target <= self.filter_value:
                continue
            
            # Check if price has mitigated the POI
            if poi.is_swept(current_candle.close):
                self.poi_manager.mark_poi_mitigated(pair, poi)
                self.swing_points[pair].discard(poi)
                mitigated.append(poi)
        
        return mitigated
    
    def get_active_swings(self, pair: str) -> Dict[str, int]:
        """
        Get count of active swing points for a pair
        In POI mode, returns POI counts instead
        
        Returns:
            Dict with counts of swings/POIs and qualified liquidity zones
        """
        if self.poi_enabled:
            # POI mode: return POI summary
            summary = self.poi_manager.get_poi_summary(pair)
            return {
                "high": summary["active_highs"] + summary["mitigated_highs"],
                "low": summary["active_lows"] + summary["mitigated_lows"],
                "high_liquidity": summary["active_highs"],
                "low_liquidity": summary["active_lows"],
                "mitigated_total": summary["mitigated"]
            }
        
        # Original mode
        if pair not in self.swing_points:
            return {"high": 0, "low": 0, "high_liquidity": 0, "low_liquidity": 0}
        
        high_swings = 0
        low_swings = 0
        high_liquidity = 0
        low_liquidity = 0
        
        for s in self.swing_points[pair]:
            if s.crossed:
                continue
                
            # Count total swings
            if s.swing_type == "high":
                high_swings += 1
            else:
                low_swings += 1
            
            # Count qualified liquidity zones (meet filter criteria)
            filter_target = s.count if self.filter_by == "Count" else s.volume
            if filter_target > self.filter_value:
                if s.swing_type == "high":
                    high_liquidity += 1
                else:
                    low_liquidity += 1
        
        return {
            "high": high_swings, 
            "low": low_swings,
            "high_liquidity": high_liquidity,
            "low_liquidity": low_liquidity
        }
