"""
Persistent Signal Tracker
Tracks sent signals and executed trades to prevent duplicates across restarts
Uses a simple JSON file for persistence
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from threading import Lock


class PersistentSignalTracker:
    """
    Tracks signals and trades persistently to prevent duplicates across restarts
    """
    
    def __init__(self, filepath: str = "signal_history.json", max_age_hours: int = 24):
        self.filepath = filepath
        self.max_age = timedelta(hours=max_age_hours)
        self.lock = Lock()
        self.data = self._load()
    
    def _load(self) -> Dict:
        """Load signal history from file"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    # Clean old entries on load
                    self._clean_old_entries(data)
                    return data
            except Exception as e:
                print(f"⚠️  Could not load signal history: {e}")
                return {"signals": {}, "trades": {}}
        
        return {"signals": {}, "trades": {}}
    
    def _save(self):
        """Save signal history to file"""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save signal history: {e}")
    
    def _clean_old_entries(self, data: Dict):
        """Remove entries older than max_age"""
        current_time = datetime.now()
        
        # Clean signals
        if "signals" in data:
            signals_to_remove = []
            for key, entry in data["signals"].items():
                entry_time = datetime.fromisoformat(entry["time"])
                if current_time - entry_time > self.max_age:
                    signals_to_remove.append(key)
            
            for key in signals_to_remove:
                del data["signals"][key]
        
        # Clean trades
        if "trades" in data:
            trades_to_remove = []
            for key, entry in data["trades"].items():
                entry_time = datetime.fromisoformat(entry["time"])
                if current_time - entry_time > self.max_age:
                    trades_to_remove.append(key)
            
            for key in trades_to_remove:
                del data["trades"][key]
    
    def is_duplicate_signal(self, strategy: str, pair: str, signal_type: str, 
                           entry_price: float, tolerance_pct: float = 0.5) -> bool:
        """
        Check if signal is a duplicate
        
        Args:
            strategy: Strategy name (CRT, POI_FVG, SR_CHANNEL)
            pair: Trading pair
            signal_type: LONG or SHORT
            entry_price: Entry price
            tolerance_pct: Price tolerance percentage (default 0.5%)
        
        Returns:
            True if duplicate, False if new signal
        """
        with self.lock:
            key = f"{strategy}_{pair}_{signal_type}"
            
            if key not in self.data["signals"]:
                return False
            
            last_signal = self.data["signals"][key]
            last_price = last_signal["price"]
            last_time = datetime.fromisoformat(last_signal["time"])
            
            # Check if too old (not a duplicate if old enough)
            if datetime.now() - last_time > self.max_age:
                return False
            
            # Check price similarity
            price_diff_pct = abs(entry_price - last_price) / last_price * 100
            if price_diff_pct <= tolerance_pct:
                return True  # Duplicate!
            
            return False
    
    def record_signal(self, strategy: str, pair: str, signal_type: str, entry_price: float):
        """
        Record a signal that was sent
        
        Args:
            strategy: Strategy name
            pair: Trading pair
            signal_type: LONG or SHORT
            entry_price: Entry price
        """
        with self.lock:
            key = f"{strategy}_{pair}_{signal_type}"
            
            self.data["signals"][key] = {
                "price": entry_price,
                "time": datetime.now().isoformat()
            }
            
            self._save()
    
    def is_duplicate_trade(self, strategy: str, pair: str, signal_type: str,
                          entry_price: float, tolerance_pct: float = 0.3) -> bool:
        """
        Check if trade was already executed (more strict than signal check)
        
        Args:
            strategy: Strategy name
            pair: Trading pair
            signal_type: LONG or SHORT
            entry_price: Entry price
            tolerance_pct: Price tolerance percentage (default 0.3%)
        
        Returns:
            True if duplicate, False if new trade
        """
        with self.lock:
            key = f"{strategy}_{pair}_{signal_type}"
            
            if key not in self.data["trades"]:
                return False
            
            last_trade = self.data["trades"][key]
            last_price = last_trade["price"]
            last_time = datetime.fromisoformat(last_trade["time"])
            
            # Check if too old
            if datetime.now() - last_time > self.max_age:
                return False
            
            # Check price similarity (stricter for trades)
            price_diff_pct = abs(entry_price - last_price) / last_price * 100
            if price_diff_pct <= tolerance_pct:
                return True  # Duplicate trade!
            
            return False
    
    def record_trade(self, strategy: str, pair: str, signal_type: str, 
                    entry_price: float, order_id: Optional[str] = None):
        """
        Record a trade that was executed
        
        Args:
            strategy: Strategy name
            pair: Trading pair
            signal_type: LONG or SHORT
            entry_price: Entry price
            order_id: Optional ByBit order ID
        """
        with self.lock:
            key = f"{strategy}_{pair}_{signal_type}"
            
            self.data["trades"][key] = {
                "price": entry_price,
                "time": datetime.now().isoformat(),
                "order_id": order_id
            }
            
            self._save()
    
    def get_stats(self) -> Dict:
        """Get statistics about tracked signals and trades"""
        with self.lock:
            return {
                "total_signals": len(self.data["signals"]),
                "total_trades": len(self.data["trades"]),
                "oldest_signal": self._get_oldest_time(self.data["signals"]),
                "oldest_trade": self._get_oldest_time(self.data["trades"])
            }
    
    def _get_oldest_time(self, entries: Dict) -> Optional[str]:
        """Get the oldest entry time"""
        if not entries:
            return None
        
        oldest = None
        for entry in entries.values():
            entry_time = datetime.fromisoformat(entry["time"])
            if oldest is None or entry_time < oldest:
                oldest = entry_time
        
        return oldest.isoformat() if oldest else None
    
    def clear_old_entries(self):
        """Manually trigger cleanup of old entries"""
        with self.lock:
            self._clean_old_entries(self.data)
            self._save()
