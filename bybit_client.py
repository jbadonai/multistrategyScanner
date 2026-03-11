"""
ByBit trading client for automated CRT signal execution
Handles order placement, leverage management, and position tracking
Uses ByBit V5 API
"""
import hashlib
import hmac
import time
import json
import requests
from typing import Optional, Dict, List
from threading import Lock
import config


class ByBitClient:
    """ByBit V5 API client for automated trading"""
    
    def __init__(self):
        self.api_key = config.BYBIT_API_KEY.strip() if config.BYBIT_API_KEY else ""
        self.api_secret = config.BYBIT_API_SECRET.strip() if config.BYBIT_API_SECRET else ""
        self.testnet = config.BYBIT_TESTNET
        
        # API endpoints
        if self.testnet:
            self.base_url = "https://api-testnet.bybit.com"
        else:
            self.base_url = "https://api.bybit.com"
        
        # Thread safety for order placement
        self.order_lock = Lock()
        
        # Track placed orders to prevent duplicates
        self.placed_orders: Dict[str, set] = {}  # pair -> set of order_ids
        
        # Cache for leverage info
        self.leverage_cache: Dict[str, int] = {}  # pair -> max_leverage
        
        # Time synchronization (only if credentials exist)
        self._time_offset = 0
        if self.api_key and self.api_secret:
            self.sync_server_time()
        
        # Constants
        self.recv_window = "5000"
    
    def sync_server_time(self):
        """Synchronize with ByBit server time"""
        try:
            resp = requests.get(self.base_url + "/v5/public/time", timeout=5)
            data = resp.json()
            # Handle both response formats
            server_time = int(data.get('result', {}).get('timeSecond', 0)) * 1000
            if server_time == 0:
                # Try alternative format
                server_time = int(data.get('result', {}).get('time', 0))
            if server_time == 0:
                # Try direct time field
                server_time = int(data.get('time', 0))
            
            if server_time > 0:
                local_time = int(time.time() * 1000)
                offset = server_time - local_time
                if abs(offset - self._time_offset) > 2000:  # 2 second threshold
                    self._time_offset = offset
        except Exception as e:
            # Silent fail - will use local time
            pass
    
    def _now_ms(self):
        """Get current timestamp in milliseconds (synchronized)"""
        return str(int(time.time() * 1000 + self._time_offset))
    
    def _generate_signature(self, timestamp: str, body_or_query: str) -> str:
        """Generate HMAC SHA256 signature for ByBit V5 API"""
        prehash = timestamp + self.api_key + self.recv_window + body_or_query
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            prehash.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _headers(self, signature: str, timestamp: str) -> Dict:
        """Generate headers for authenticated requests"""
        return {
            'Content-Type': 'application/json',
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': self.recv_window,
            'X-BAPI-SIGN': signature
        }
    
    def _private_post(self, path: str, body: Dict) -> Optional[Dict]:
        """Make authenticated POST request"""
        try:
            body_str = json.dumps(body, separators=(',', ':'))
            ts = self._now_ms()
            sig = self._generate_signature(ts, body_str)
            headers = self._headers(sig, ts)
            
            response = requests.post(
                self.base_url + path,
                headers=headers,
                data=body_str,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('retCode') != 0:
                print(f"ByBit API Error: {result.get('retMsg', 'Unknown error')}")
                return None
            
            return result
        except Exception as e:
            print(f"ByBit API Request Error: {e}")
            return None
    
    def _private_get(self, path: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated GET request"""
        try:
            params = params or {}
            query_items = sorted(params.items())
            query_str = '&'.join([f"{k}={v}" for k, v in query_items])
            
            ts = self._now_ms()
            sig = self._generate_signature(ts, query_str)
            headers = self._headers(sig, ts)
            
            url = self.base_url + path
            if query_str:
                url += '?' + query_str
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('retCode') != 0:
                print(f"ByBit API Error: {result.get('retMsg', 'Unknown error')}")
                return None
            
            return result
        except Exception as e:
            print(f"ByBit API Request Error: {e}")
            return None
    
    def get_instrument_info(self, category: str, symbol: str) -> Optional[Dict]:
        """Get instrument information"""
        try:
            url = f"{self.base_url}/v5/market/instruments-info?category={category}&symbol={symbol}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting instrument info: {e}")
            return None
    
    def get_max_leverage(self, symbol: str) -> Optional[int]:
        """
        Get maximum leverage for a symbol
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            
        Returns:
            Maximum leverage or None
        """
        # Check cache first
        if symbol in self.leverage_cache:
            return self.leverage_cache[symbol]
        
        # Get leverage info from API
        result = self.get_instrument_info("linear", symbol)
        
        if not result or 'result' not in result:
            return None
        
        # Find symbol info
        instrument_list = result.get('result', {}).get('list', [])
        if not instrument_list:
            return None
        
        data = instrument_list[0]
        leverage_filter = data.get('leverageFilter', {})
        if not leverage_filter:
            return None
        
        max_leverage = int(float(leverage_filter.get('maxLeverage', 50)))
        self.leverage_cache[symbol] = max_leverage
        return max_leverage
    
    def get_current_leverage(self, symbol: str) -> Optional[int]:
        """Get current leverage setting for a symbol"""
        result = self._private_get("/v5/position/list", {"category": "linear", "symbol": symbol})
        
        if not result or 'result' not in result:
            return None
        
        positions = result.get('result', {}).get('list', [])
        if positions and len(positions) > 0:
            return int(float(positions[0].get('leverage', 0)))
        
        return None
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a symbol (intelligently handles already-set leverage)
        
        Args:
            symbol: Trading pair
            leverage: Desired leverage
            
        Returns:
            True if successful, False otherwise
        """
        # Check current leverage first
        current_leverage = self.get_current_leverage(symbol)
        
        if current_leverage == leverage:
            # Already at desired leverage, no need to set
            print(f"   ℹ️  {symbol} leverage already at {leverage}x")
            return True
        
        # Set new leverage
        body = {
            "category": "linear",
            "symbol": symbol,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage)
        }
        
        result = self._private_post("/v5/position/set-leverage", body)
        
        if result:
            print(f"   ✅ Set {symbol} leverage to {leverage}x")
            return True
        else:
            print(f"   ❌ Failed to set {symbol} leverage")
            return False
    
    def get_account_balance(self) -> Optional[float]:
        """Get available USDT balance"""
        result = self._private_get("/v5/account/wallet-balance", {"accountType": "UNIFIED"})
        
        if not result or 'result' not in result:
            return None
        
        coins = result.get('result', {}).get('list', [{}])[0].get('coin', [])
        for coin in coins:
            if coin.get('coin') == 'USDT':
                return float(coin.get('availableToWithdraw', 0))
        
        return None
    
    def get_open_positions_count(self) -> int:
        """Get number of currently open positions"""
        result = self._private_get("/v5/position/list", {"category": "linear"})
        
        if not result or 'result' not in result:
            return 0
        
        positions = result.get('result', {}).get('list', [])
        open_count = sum(1 for p in positions if float(p.get('size', 0)) > 0)
        
        return open_count
    
    def calculate_order_qty(self, symbol: str, entry_price: float, 
                           order_value: float) -> Optional[float]:
        """
        Calculate order quantity based on order value and entry price
        
        Args:
            symbol: Trading pair
            entry_price: Entry price
            order_value: Order value in USDT
            
        Returns:
            Order quantity (contracts/coins) or None
        """
        result = self.get_instrument_info("linear", symbol)
        
        if not result or 'result' not in result:
            return None
        
        instrument_list = result.get('result', {}).get('list', [])
        if not instrument_list:
            return None
        
        data = instrument_list[0]
        lot_size_filter = data.get('lotSizeFilter', {})
        
        # Calculate qty
        qty = order_value / entry_price
        
        # Round to proper precision
        qty_step = float(lot_size_filter.get('qtyStep', 0.001))
        qty = round(qty / qty_step) * qty_step
        
        return qty
    
    def place_order(self, symbol: str, side: str, qty: float, 
                   stop_loss: float, take_profit: float,
                   order_link_id: str) -> Optional[Dict]:
        """
        Place market order with SL and TP
        
        Args:
            symbol: Trading pair
            side: "Buy" or "Sell"
            qty: Order quantity
            stop_loss: Stop loss price
            take_profit: Take profit price
            order_link_id: Unique order identifier
            
        Returns:
            Order result dict or None
        """
        with self.order_lock:
            # Check for duplicate
            if symbol not in self.placed_orders:
                self.placed_orders[symbol] = set()
            
            if order_link_id in self.placed_orders[symbol]:
                print(f"   ⚠️  Duplicate order detected for {symbol}, skipping")
                return None
            
            # Hedge mode: positionIdx
            position_idx = 1 if side == "Buy" else 2
            
            # Place order
            body = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(qty),
                "timeInForce": "GTC",
                "positionIdx": position_idx,
                "orderLinkId": order_link_id
            }
            
            # Add SL/TP
            if stop_loss:
                body["stopLoss"] = str(stop_loss)
            if take_profit:
                body["takeProfit"] = str(take_profit)
            
            result = self._private_post("/v5/order/create", body)
            
            if result:
                # Track order
                self.placed_orders[symbol].add(order_link_id)
                return result
            
            return None
    
    def test_connection(self) -> bool:
        """Test ByBit API connection"""
        try:
            print(f"   🔍 Testing connection to {self.base_url}")
            print(f"   🔍 API Key configured: {bool(self.api_key and len(self.api_key) > 0)}")
            print(f"   🔍 API Secret configured: {bool(self.api_secret and len(self.api_secret) > 0)}")
            
            # Try the public time endpoint
            endpoints_to_try = [
                "/v5/public/time",
                "/v5/market/time", 
                "/v5/market/tickers?category=linear&symbol=BTCUSDT"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    print(f"   🔍 Trying endpoint: {endpoint}")
                    response = requests.get(self.base_url + endpoint, timeout=5)
                    print(f"   🔍 Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"   🔍 Response keys: {list(result.keys())}")
                        
                        # Check if response is valid
                        is_success = (result.get('retCode') == 0 or 
                                    'time' in result or 
                                    'result' in result)
                        
                        if is_success:
                            print(f"   ✅ Connection successful using {endpoint}")
                            return True
                except Exception as e:
                    print(f"   ⚠️  Endpoint {endpoint} failed: {e}")
                    continue
            
            print(f"   ❌ All endpoints failed")
            return False
            
        except Exception as e:
            print(f"   ❌ Connection test error: {type(e).__name__}: {e}")
            return False
    
    def get_positions(self) -> List[Dict]:
        """
        Get all open positions
        
        Returns:
            List of position dicts with fields:
            - symbol, side, size, avgPrice, markPrice, unrealisedPnl, etc.
        """
        try:
            endpoint = "/v5/position/list"
            params = {
                "category": "linear",
                "settleCoin": "USDT"
            }
            
            result = self._signed_request("GET", endpoint, params)
            
            if result and result.get('retCode') == 0:
                positions_data = result.get('result', {}).get('list', [])
                
                # Filter to only positions with size > 0
                open_positions = []
                for pos in positions_data:
                    size = float(pos.get('size', 0))
                    if size > 0:
                        open_positions.append(pos)
                
                return open_positions
            
            return []
            
        except Exception as e:
            print(f"   ⚠️  Error getting positions: {e}")
            return []
    
    def close_position(self, symbol: str, side: str, qty: float) -> Optional[Dict]:
        """
        Close a position with market order
        
        Args:
            symbol: Trading pair
            side: "Buy" to close short, "Sell" to close long
            qty: Position size to close
        
        Returns:
            Order result or None
        """
        try:
            endpoint = "/v5/order/create"
            
            # Generate unique order ID
            import time
            timestamp = int(time.time() * 1000)
            order_link_id = f"CLOSE_{symbol}_{side}_{timestamp}"
            
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(qty),
                "timeInForce": "GTC",
                "reduceOnly": True,  # Important: only close, don't open new
                "closeOnTrigger": False,
                "orderLinkId": order_link_id
            }
            
            result = self._signed_request("POST", endpoint, params)
            
            if result and result.get('retCode') == 0:
                return result.get('result')
            else:
                error_msg = result.get('retMsg', 'Unknown error') if result else 'No response'
                print(f"   ❌ Close position failed: {error_msg}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error closing position: {e}")
            return None

