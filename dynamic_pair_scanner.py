#!/usr/bin/env python3
"""
Dynamic Pair Scanner
Automatically selects high-volatility pairs from both Bybit and Binance
Rescans daily at midnight to adapt to changing market conditions
"""

import requests
import logging
from typing import List, Dict, Tuple
from datetime import datetime, time as dt_time
from threading import Thread, Lock
import time


class DynamicPairScanner:
    """
    Scans and maintains a list of high-volatility trading pairs
    Automatically rescans at midnight each day
    """
    
    def __init__(self, config):
        self.config = config
        self.volatility_threshold = getattr(config, 'VOLATILITY_THRESHOLD', 2.0)
        self.max_pairs = getattr(config, 'MAX_DYNAMIC_PAIRS', 50)
        self.request_timeout = getattr(config, 'REQUEST_TIMEOUT', 10)
        self.rescan_time = getattr(config, 'RESCAN_TIME', "00:00")  # HH:MM format
        
        self.pairs_lock = Lock()
        self.current_pairs: List[str] = []
        self.last_scan_time = None
        
        self.running = False
        self.scan_thread = None
        
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the dynamic pair scanner"""
        self.running = True
        
        # Initial scan
        print("🔍 Performing initial pair scan...")
        self.scan_pairs()
        
        # Start background thread for daily rescans
        self.scan_thread = Thread(target=self._rescan_loop, daemon=True)
        self.scan_thread.start()
        
        print(f"✅ Dynamic pair scanner started (rescans at {self.rescan_time})")
    
    def stop(self):
        """Stop the scanner"""
        self.running = False
        if self.scan_thread:
            self.scan_thread.join(timeout=5)
    
    def get_pairs(self) -> List[str]:
        """Get current list of pairs (thread-safe)"""
        with self.pairs_lock:
            return self.current_pairs.copy()
    
    def scan_pairs(self) -> List[str]:
        """
        Scan for high-volatility pairs on both exchanges
        Returns list of pairs
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔍 SCANNING FOR VOLATILE PAIRS")
            print(f"{'='*60}")
            
            # Get pairs from both exchanges
            bybit_pairs = self._get_bybit_futures()
            print(f"📊 Bybit: {len(bybit_pairs)} USDT pairs found")
            
            binance_pairs = self._get_binance_futures()
            print(f"📊 Binance: {len(binance_pairs)} USDT pairs found")
            
            # Find common pairs
            common = set(bybit_pairs.keys()) & set(binance_pairs.keys())
            print(f"📊 Common pairs: {len(common)}")
            
            # Filter by volatility and calculate average
            volatile: List[Tuple[str, float]] = []
            for symbol in common:
                avg_vol = (bybit_pairs[symbol] + binance_pairs[symbol]) / 2
                if avg_vol >= self.volatility_threshold:
                    volatile.append((symbol, avg_vol))
            
            # Sort by volatility (highest first)
            volatile.sort(key=lambda x: x[1], reverse=True)
            
            # Limit to max pairs
            volatile = volatile[:self.max_pairs]
            
            print(f"✅ Found {len(volatile)} volatile pairs (≥{self.volatility_threshold}%)")
            
            # Extract symbols
            selected_pairs = [symbol for symbol, _ in volatile]
            
            # Display top 10
            if volatile:
                print(f"\n🔥 Top 10 Most Volatile:")
                print(f"{'Rank':<6} {'Pair':<15} {'Bybit %':>10} {'Binance %':>10} {'Avg %':>10}")
                print("-" * 56)
                for i, (symbol, avg_vol) in enumerate(volatile[:10], 1):
                    bybit_vol = bybit_pairs[symbol]
                    binance_vol = binance_pairs[symbol]
                    print(f"{i:<6} {symbol:<15} {bybit_vol:>9.2f}% {binance_vol:>9.2f}% {avg_vol:>9.2f}%")
            
            # Update current pairs (thread-safe)
            with self.pairs_lock:
                self.current_pairs = selected_pairs
                self.last_scan_time = datetime.now()
            
            print(f"\n✅ Pair list updated: {len(selected_pairs)} pairs")
            print(f"{'='*60}\n")
            
            return selected_pairs
            
        except Exception as e:
            self.logger.error(f"Error scanning pairs: {e}")
            print(f"❌ Pair scan failed: {e}")
            
            # Return existing pairs if scan fails
            with self.pairs_lock:
                return self.current_pairs.copy() if self.current_pairs else []
    
    def _get_bybit_futures(self) -> Dict[str, float]:
        """
        Get Bybit linear perpetual futures with volatility
        Returns {symbol: abs_price_change_pct}
        """
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "linear"}
        
        response = requests.get(url, params=params, timeout=self.request_timeout)
        response.raise_for_status()
        data = response.json()
        
        pairs: Dict[str, float] = {}
        for item in data.get("result", {}).get("list", []):
            symbol = item.get("symbol", "")
            
            # Only USDT-margined perpetuals
            if not symbol.endswith("USDT"):
                continue
            
            try:
                # Bybit returns as decimal (0.05 = 5%)
                change_pct = abs(float(item.get("price24hPcnt", 0)) * 100)
                pairs[symbol] = change_pct
            except (ValueError, TypeError):
                continue
        
        return pairs
    
    def _get_binance_futures(self) -> Dict[str, float]:
        """
        Get Binance USD-M futures with volatility
        Returns {symbol: abs_price_change_pct}
        """
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        
        response = requests.get(url, timeout=self.request_timeout)
        response.raise_for_status()
        data = response.json()
        
        pairs: Dict[str, float] = {}
        for item in data:
            symbol = item.get("symbol", "")
            
            # Only USDT-margined
            if not symbol.endswith("USDT"):
                continue
            
            try:
                # Binance returns as percentage already
                change_pct = abs(float(item.get("priceChangePercent", 0)))
                pairs[symbol] = change_pct
            except (ValueError, TypeError):
                continue
        
        return pairs
    
    def _rescan_loop(self):
        """Background thread that rescans pairs daily at specified time"""
        while self.running:
            try:
                # Parse rescan time
                rescan_hour, rescan_minute = map(int, self.rescan_time.split(':'))
                target_time = dt_time(rescan_hour, rescan_minute)
                
                # Get current time
                now = datetime.now()
                current_time = now.time()
                
                # Check if we've crossed the rescan time
                # and haven't scanned yet today at this time
                if current_time >= target_time:
                    # Check if last scan was today before this time
                    if self.last_scan_time is None or \
                       self.last_scan_time.date() < now.date() or \
                       (self.last_scan_time.date() == now.date() and 
                        self.last_scan_time.time() < target_time):
                        
                        print(f"\n⏰ Daily rescan triggered at {now.strftime('%Y-%m-%d %H:%M:%S')}")
                        self.scan_pairs()
                
                # Sleep for 60 seconds before next check
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in rescan loop: {e}")
                time.sleep(60)
    
    def get_stats(self) -> Dict:
        """Get scanner statistics"""
        with self.pairs_lock:
            return {
                "pair_count": len(self.current_pairs),
                "last_scan": self.last_scan_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_scan_time else "Never",
                "volatility_threshold": self.volatility_threshold,
                "max_pairs": self.max_pairs,
                "rescan_time": self.rescan_time
            }
