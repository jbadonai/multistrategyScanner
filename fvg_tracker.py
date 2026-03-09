"""
FVG tracker module - monitors swept liquidity for FVG formations
"""
from typing import Dict, List, Optional
from datetime import datetime
from models import SwingAlert, FVGAlert, MarketData
from fvg_detector import FVGDetector
import config


class FVGTracker:
    """Tracks liquidity sweeps and monitors for FVG formations"""
    
    def __init__(self):
        self.fvg_detector = FVGDetector(config.FVG_LOOKBACK_CANDLES)
        # Track pending sweeps waiting for FVG: {pair: [(sweep_alert, sweep_candle_index), ...]}
        self.pending_sweeps: Dict[str, List[tuple]] = {}
        # Track which sweeps already generated FVG alerts
        self.fvg_generated: Dict[str, set] = {}
    
    def initialize_pair(self, pair: str):
        """Initialize FVG tracking for a pair"""
        if pair not in self.pending_sweeps:
            self.pending_sweeps[pair] = []
        if pair not in self.fvg_generated:
            self.fvg_generated[pair] = set()
    
    def add_sweep(self, pair: str, sweep_alert: SwingAlert, current_candle_index: int):
        """
        Add a new liquidity sweep to monitor for FVG
        
        Args:
            pair: Trading pair
            sweep_alert: The sweep alert that just occurred
            current_candle_index: Index of candle where sweep occurred
        """
        self.initialize_pair(pair)
        
        # Add to pending sweeps
        self.pending_sweeps[pair].append((sweep_alert, current_candle_index))
        
        # Clean up old pending sweeps (beyond lookback window)
        self._cleanup_old_sweeps(pair, current_candle_index)
    
    def check_for_fvg(self, pair: str, candles: List[MarketData], 
                      current_index: int) -> List[FVGAlert]:
        """
        Check if any pending sweeps now have FVG formations
        
        Args:
            pair: Trading pair
            candles: Full list of market candles
            current_index: Current candle index
            
        Returns:
            List of FVGAlert objects for newly detected FVGs
        """
        if not config.ENABLE_FVG_DETECTION:
            return []
        
        self.initialize_pair(pair)
        fvg_alerts = []
        
        # Check each pending sweep
        for sweep_alert, sweep_index in self.pending_sweeps[pair]:
            # Skip if we already generated FVG alert for this sweep
            sweep_id = id(sweep_alert)
            if sweep_id in self.fvg_generated[pair]:
                continue
            
            # Check if we're still within lookback window
            candles_since_sweep = current_index - sweep_index
            if candles_since_sweep > config.FVG_LOOKBACK_CANDLES:
                continue
            
            # Need at least 3 candles after sweep to detect FVG
            if sweep_index + 2 >= len(candles):
                continue
            
            # Detect FVG starting from sweep candle
            fvg = self.fvg_detector.detect_fvg(candles, sweep_index)
            
            if fvg:
                # Create FVG alert
                fvg_alert = FVGAlert(
                    pair=pair,
                    fvg_type=fvg["type"],
                    gap_top=fvg["gap_top"],
                    gap_bottom=fvg["gap_bottom"],
                    candle_2_body=fvg["candle_2_body"],
                    candle_3_body=fvg["candle_3_body"],
                    body_ratio=fvg["candle_2_body"] / fvg["candle_3_body"],
                    candles_after_sweep=fvg["candles_after_sweep"],
                    fvg_timestamp=fvg["timestamp"],
                    sweep_timestamp=sweep_alert.sweep_timestamp,
                    original_sweep=sweep_alert
                )
                
                fvg_alerts.append(fvg_alert)
                
                # Mark this sweep as having generated FVG
                self.fvg_generated[pair].add(sweep_id)
        
        return fvg_alerts
    
    def _cleanup_old_sweeps(self, pair: str, current_index: int):
        """
        Remove pending sweeps that are beyond lookback window
        
        Args:
            pair: Trading pair
            current_index: Current candle index
        """
        if pair not in self.pending_sweeps:
            return
        
        # Keep only sweeps within lookback window
        self.pending_sweeps[pair] = [
            (sweep, index) for sweep, index in self.pending_sweeps[pair]
            if current_index - index <= config.FVG_LOOKBACK_CANDLES + 5  # +5 buffer
        ]
    
    def get_pending_count(self, pair: str) -> int:
        """Get number of pending sweeps being monitored for FVG"""
        if pair not in self.pending_sweeps:
            return 0
        return len(self.pending_sweeps[pair])
