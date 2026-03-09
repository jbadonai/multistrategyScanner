"""
Binance API client for fetching market data
"""
import requests
from typing import List, Optional
from models import MarketData
import config
import time


class BinanceClient:
    """Client for interacting with Binance public API"""
    
    def __init__(self):
        self.base_url = config.BINANCE_API_BASE
        self.timeout = config.REQUEST_TIMEOUT
        self.max_retries = config.MAX_RETRIES
    
    def get_klines(self, symbol: str, interval: str, limit: int) -> Optional[List[MarketData]]:
        """
        Fetch kline/candlestick data from Binance
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            interval: Kline interval (e.g., "5m", "15m", "1h")
            limit: Number of klines to fetch
            
        Returns:
            List of MarketData objects, or None if request fails
        """
        endpoint = f"{self.base_url}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    endpoint,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                klines = response.json()
                return [MarketData.from_binance(k) for k in klines]
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                else:
                    return None
        
        return None
    
    def test_connection(self) -> bool:
        """
        Test connection to Binance API
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v3/ping",
                timeout=self.timeout
            )
            return response.status_code == 200
        except:
            return False
    
    def get_exchange_info(self, symbol: str) -> Optional[dict]:
        """
        Get exchange information for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Exchange info dict or None if request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v3/exchangeInfo",
                params={"symbol": symbol},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except:
            return None
    
    def get_daily_candles(self, symbol: str, days: int = 4) -> Optional[List[MarketData]]:
        """
        Fetch daily candlestick data
        
        Args:
            symbol: Trading pair symbol
            days: Number of days to fetch (includes today)
            
        Returns:
            List of MarketData objects (daily timeframe), or None if request fails
        """
        return self.get_klines(symbol, "1d", days)
