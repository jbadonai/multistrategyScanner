"""
Auto-trader module for executing CRT signals on ByBit
Runs in separate thread to avoid blocking main scanner
"""
import time
from threading import Thread
from typing import Optional, Dict
from datetime import datetime
from models import CRTAlert
from bybit_client import ByBitClient
from telegram_notifier import TelegramNotifier
import config


class AutoTrader:
    """Executes CRT signals automatically on ByBit"""
    
    def __init__(self):
        self.bybit = ByBitClient()
        self.telegram = TelegramNotifier()
        self.enabled = config.ENABLE_AUTO_TRADE
        
        if not self.enabled:
            return
        
        # Validate API credentials
        if not config.BYBIT_API_KEY or not config.BYBIT_API_SECRET:
            print("⚠️  WARNING: ByBit API credentials not configured!")
            print("   Set BYBIT_API_KEY and BYBIT_API_SECRET in config.py")
            self.enabled = False
    
    def execute_trade(self, crt_alert: CRTAlert):
        """
        Execute trade for CRT signal in separate thread
        
        Args:
            crt_alert: CRT alert with trading setup
        """
        if not self.enabled:
            return
        
        # Run in separate thread to avoid blocking scanner
        thread = Thread(target=self._execute_trade_threaded, args=(crt_alert,))
        thread.daemon = True
        thread.start()
    
    def _execute_trade_threaded(self, crt_alert: CRTAlert):
        """Execute trade in separate thread"""
        try:
            result = self._place_trade(crt_alert)
            
            if result:
                self._send_success_notification(crt_alert, result)
            else:
                self._send_failure_notification(crt_alert, "Order placement failed")
        
        except Exception as e:
            self._send_failure_notification(crt_alert, str(e))
    
    def _place_trade(self, crt_alert: CRTAlert) -> Optional[Dict]:
        """
        Place trade on ByBit based on CRT signal
        
        Returns:
            Order result dict or None if failed
        """
        symbol = crt_alert.pair
        
        # Validate symbol for ByBit
        # ByBit linear perpetuals use USDT, not USDC
        if "USDC" in symbol:
            print(f"   ⚠️  {symbol} not supported on ByBit (USDC pairs not available for linear perpetuals)")
            return None
        
        # Check concurrent positions limit
        open_positions = self.bybit.get_open_positions_count()
        if open_positions >= config.MAX_CONCURRENT_TRADES:
            print(f"   ⚠️  Max concurrent trades ({config.MAX_CONCURRENT_TRADES}) reached")
            return None
        
        # Determine leverage
        if config.USE_MAX_LEVERAGE:
            max_leverage = self.bybit.get_max_leverage(symbol)
            if not max_leverage:
                print(f"   ❌ Could not get max leverage for {symbol}")
                return None
            leverage = max_leverage
        else:
            leverage = config.FIXED_LEVERAGE
        
        # Set leverage (handles already-set case intelligently)
        if not self.bybit.set_leverage(symbol, leverage):
            # Not critical, continue anyway
            pass
        
        # Calculate order value
        if config.USE_PERCENTAGE_OF_BALANCE:
            balance = self.bybit.get_account_balance()
            if not balance:
                print(f"   ❌ Could not get account balance")
                return None
            order_value = balance * (config.PERCENTAGE_OF_BALANCE / 100.0)
        else:
            order_value = leverage * config.ORDER_VALUE_MULTIPLIER
        
        # Calculate quantity
        entry_price = crt_alert.candle_2_close
        qty = self.bybit.calculate_order_qty(symbol, entry_price, order_value)
        
        if not qty or qty <= 0:
            error_msg = f"Invalid order quantity calculated: {qty} (entry: {entry_price}, value: {order_value})"
            print(f"   ❌ {error_msg}")
            return None
        
        # Determine side
        side = "Buy" if crt_alert.crt_type == "bullish" else "Sell"
        
        # Calculate TP based on opposite liquidity
        if crt_alert.crt_type == "bullish":
            take_profit = crt_alert.candle_1_high
        else:
            take_profit = crt_alert.candle_1_low
        
        # Generate unique order ID
        timestamp = int(time.time() * 1000)
        order_link_id = f"CRT_{symbol}_{crt_alert.crt_type}_{timestamp}"
        
        print(f"\n   🤖 Placing {side} order for {symbol}")
        print(f"      Qty: {qty}, Entry: ~{entry_price:.8f}")
        print(f"      SL: {crt_alert.sweep_price:.8f}, TP: {take_profit:.8f}")
        print(f"      Leverage: {leverage}x, Value: ${order_value:.2f}")
        
        # Place order
        result = self.bybit.place_order(
            symbol=symbol,
            side=side,
            qty=qty,
            stop_loss=crt_alert.sweep_price,
            take_profit=take_profit,
            order_link_id=order_link_id
        )
        
        return result
    
    def _send_success_notification(self, crt_alert: CRTAlert, order_result: Dict):
        """Send Telegram notification for successful trade"""
        symbol = crt_alert.pair
        side = "LONG" if crt_alert.crt_type == "bullish" else "SHORT"
        
        # Calculate TP
        if crt_alert.crt_type == "bullish":
            take_profit = crt_alert.candle_1_high
        else:
            take_profit = crt_alert.candle_1_low
        
        message = f"✅ *TRADE EXECUTED SUCCESSFULLY* ✅\n\n"
        message += f"🤖 *Auto-Trade:* CRT Signal\n"
        message += f"📊 Pair: `{symbol}`\n"
        message += f"📈 Direction: *{side}*\n"
        message += f"⏰ Timeframe: *{crt_alert.timeframe.upper()}*\n\n"
        
        message += f"💰 *Order Details:*\n"
        message += f"   • Entry: `{crt_alert.candle_2_close:.8f}`\n"
        message += f"   • Stop Loss: `{crt_alert.sweep_price:.8f}`\n"
        message += f"   • Take Profit: `{take_profit:.8f}`\n"
        
        # Extract order info from result
        if 'result' in order_result:
            order_info = order_result['result']
            order_id = order_info.get('order_id', 'N/A')
            message += f"   • Order ID: `{order_id}`\n"
        
        message += f"\n⏱️ Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
        message += f"\n{'🟢' if crt_alert.crt_type == 'bullish' else '🔴'} Trade placed via ByBit API"
        
        self.telegram.send_message(message)
        print(f"   ✅ Trade executed and notification sent")
    
    def _send_failure_notification(self, crt_alert: CRTAlert, error: str):
        """Send Telegram notification for failed trade"""
        symbol = crt_alert.pair
        side = "LONG" if crt_alert.crt_type == "bullish" else "SHORT"
        
        # Skip notification for USDC pairs (not supported)
        if "USDC" in symbol:
            return
        
        message = f"❌ *TRADE EXECUTION FAILED* ❌\n\n"
        message += f"🤖 *Auto-Trade:* CRT Signal\n"
        message += f"📊 Pair: `{symbol}`\n"
        message += f"📈 Direction: *{side}*\n"
        message += f"⏰ Timeframe: *{crt_alert.timeframe.upper()}*\n\n"
        
        message += f"💰 *Intended Setup:*\n"
        message += f"   • Entry: `{crt_alert.candle_2_close:.8f}`\n"
        message += f"   • Stop Loss: `{crt_alert.sweep_price:.8f}`\n\n"
        
        message += f"❌ *Error:*\n"
        message += f"   `{error}`\n\n"
        
        message += f"⏱️ Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
        message += f"\n⚠️ Please check ByBit API settings or pair availability"
        
        self.telegram.send_message(message)
        print(f"   ❌ Trade failed: {error}")
    
    def test_connection(self) -> bool:
        """Test ByBit API connection"""
        if not self.enabled:
            return False
        
        return self.bybit.test_connection()
