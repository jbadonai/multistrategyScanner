"""
POI (Point of Interest) manager for tracking liquidity swings in the POI zone
"""
from typing import Dict, List, Set, Optional
from models import SwingPoint
from datetime import datetime


class POIManager:
    """Manages Points of Interest (liquidity swings between open and protected level)"""
    
    def __init__(self):
        # Structure: {pair: {trend_session_id: [SwingPoint, ...]}}
        self.pois: Dict[str, Dict[str, List[SwingPoint]]] = {}
        # Track current session info: {pair: {"trend": str, "protected": float, "open": float, "session_id": str}}
        self.current_sessions: Dict[str, Dict] = {}
    
    def initialize_pair(self, pair: str):
        """Initialize POI tracking for a pair"""
        if pair not in self.pois:
            self.pois[pair] = {}
        if pair not in self.current_sessions:
            self.current_sessions[pair] = {}
    
    def start_new_session(self, pair: str, trend: str, protected: float, 
                         daily_open: float, date: datetime):
        """
        Start a new trading session with trend context
        
        Args:
            pair: Trading pair
            trend: "uptrend" or "downtrend"
            protected: Protected level (prev day high/low)
            daily_open: Today's opening price
            date: Session date
        """
        self.initialize_pair(pair)
        
        session_id = f"{pair}_{date.strftime('%Y%m%d')}_{trend}"
        
        self.current_sessions[pair] = {
            "trend": trend,
            "protected": protected,
            "daily_open": daily_open,
            "session_id": session_id,
            "date": date
        }
        
        # Initialize POI list for this session
        if session_id not in self.pois[pair]:
            self.pois[pair][session_id] = []
    
    def add_poi(self, pair: str, swing: SwingPoint) -> bool:
        """
        Add a swing point as a POI for the current session
        
        Args:
            pair: Trading pair
            swing: SwingPoint to add as POI
            
        Returns:
            True if added successfully, False if no active session
        """
        if pair not in self.current_sessions or not self.current_sessions[pair]:
            return False
        
        session_id = self.current_sessions[pair]["session_id"]
        
        if pair not in self.pois:
            self.pois[pair] = {}
        if session_id not in self.pois[pair]:
            self.pois[pair][session_id] = []
        
        # Check if POI already exists (same bar_index and type)
        existing = [p for p in self.pois[pair][session_id] 
                   if p.bar_index == swing.bar_index and p.swing_type == swing.swing_type]
        
        if not existing:
            self.pois[pair][session_id].append(swing)
            return True
        
        return False
    
    def get_active_pois(self, pair: str) -> List[SwingPoint]:
        """
        Get all active (unmitigated) POIs for current session
        
        Args:
            pair: Trading pair
            
        Returns:
            List of unmitigated POIs
        """
        if pair not in self.current_sessions or not self.current_sessions[pair]:
            return []
        
        session_id = self.current_sessions[pair]["session_id"]
        
        if pair not in self.pois or session_id not in self.pois[pair]:
            return []
        
        # Return only unmitigated POIs
        return [poi for poi in self.pois[pair][session_id] if not poi.crossed]
    
    def get_all_pois(self, pair: str) -> List[SwingPoint]:
        """
        Get all POIs (mitigated and unmitigated) for current session
        
        Args:
            pair: Trading pair
            
        Returns:
            List of all POIs
        """
        if pair not in self.current_sessions or not self.current_sessions[pair]:
            return []
        
        session_id = self.current_sessions[pair]["session_id"]
        
        if pair not in self.pois or session_id not in self.pois[pair]:
            return []
        
        return self.pois[pair][session_id]
    
    def mark_poi_mitigated(self, pair: str, poi: SwingPoint):
        """
        Mark a POI as mitigated (swept)
        
        Args:
            pair: Trading pair
            poi: POI to mark as mitigated
        """
        poi.crossed = True
    
    def get_session_info(self, pair: str) -> Optional[Dict]:
        """
        Get current session information
        
        Returns:
            Session info dict or None
        """
        if pair not in self.current_sessions:
            return None
        return self.current_sessions[pair]
    
    def get_poi_summary(self, pair: str) -> Dict:
        """
        Get summary of POIs for current session
        
        Returns:
            Dict with POI counts
        """
        all_pois = self.get_all_pois(pair)
        active_pois = self.get_active_pois(pair)
        
        mitigated_count = len(all_pois) - len(active_pois)
        
        # Count by type
        active_highs = sum(1 for p in active_pois if p.swing_type == "high")
        active_lows = sum(1 for p in active_pois if p.swing_type == "low")
        
        mitigated_highs = sum(1 for p in all_pois if p.swing_type == "high" and p.crossed)
        mitigated_lows = sum(1 for p in all_pois if p.swing_type == "low" and p.crossed)
        
        return {
            "total": len(all_pois),
            "active": len(active_pois),
            "mitigated": mitigated_count,
            "active_highs": active_highs,
            "active_lows": active_lows,
            "mitigated_highs": mitigated_highs,
            "mitigated_lows": mitigated_lows
        }
    
    def format_poi_list(self, pair: str, mitigated_poi: Optional[SwingPoint] = None) -> str:
        """
        Format all POIs for display in Telegram message
        
        Args:
            pair: Trading pair
            mitigated_poi: Optionally highlight a specific mitigated POI
            
        Returns:
            Formatted string listing all POIs
        """
        all_pois = self.get_all_pois(pair)
        session = self.get_session_info(pair)
        
        if not all_pois:
            return "No POIs detected in this zone."
        
        # Sort POIs by price (top to bottom)
        sorted_pois = sorted(all_pois, key=lambda x: x.price_top, reverse=True)
        
        message = f"\n📍 *POIs in {session['trend'].upper()} Zone:*\n"
        message += f"   Between Open ({session['daily_open']:.8f}) and Protected ({session['protected']:.8f})\n\n"
        
        for i, poi in enumerate(sorted_pois, 1):
            poi_type = "🔴 High" if poi.swing_type == "high" else "🟢 Low"
            status = "❌ MITIGATED" if poi.crossed else "✅ Active"
            
            # Highlight the newly mitigated POI
            if mitigated_poi and poi == mitigated_poi:
                status = "🚨 JUST MITIGATED 🚨"
            
            message += f"   {i}. {poi_type} | {status}\n"
            message += f"      Zone: {poi.price_btm:.8f} - {poi.price_top:.8f}\n"
            message += f"      Touches: {poi.count} | Volume: {poi.volume:,.0f}\n"
            message += f"      Time: {poi.timestamp.strftime('%H:%M:%S')}\n\n"
        
        return message
