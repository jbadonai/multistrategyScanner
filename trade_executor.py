"""
Trade Executor
Handles automated trade execution for all strategies
Routes signals to ByBit based on strategy configuration
"""

from typing import List, Optional, Dict
from threading import Thread, Lock
from datetime import datetime
from strategies.base_strategy import StrategySignal
from bybit_client import ByBitClient
from telegram_notifier import TelegramNotifier
from persistent_tracker import PersistentSignalTracker


class TradeExecutor:
    """
    Executes trades for signals with auto-trade enabled
    """
    
    def __init__(self, config):
        self.config = config
        self.enabled = self._check_if_enabled()
        
        # Thread safety for concurrent trade management
        self.trade_lock = Lock()
        self.pending_trades = 0  # Trades currently being placed
        
        # Persistent tracking to prevent duplicate trades across restarts
        self.tracker = PersistentSignalTracker()
        
        if self.enabled:
            self.bybit = ByBitClient()
            self.telegram = TelegramNotifier()
        else:
            self.bybit = None
            self.telegram = None
    
    def _check_if_enabled(self) -> bool:
        """Check if any strategy has auto-trade enabled"""
        return (self.config.POI_AUTO_TRADE or 
                self.config.CRT_AUTO_TRADE or 
                self.config.SR_AUTO_TRADE)
    
    def test_connection(self) -> bool:
        """Test ByBit connection"""
        if not self.enabled or not self.bybit:
            return False
        return self.bybit.test_connection()
    
    def execute_signals(self, signals: List[StrategySignal]):
        """
        Execute trades for signals with auto-trade enabled
        Respects MAX_CONCURRENT_TRADES limit and prevents duplicate trades
        
        Args:
            signals: List of signals to potentially trade
        """
        if not self.enabled:
            return
        
        # Filter out duplicate trades using persistent tracker
        new_signals = []
        for signal in signals:
            if not signal.auto_trade_enabled:
                continue
            
            # Check if this exact trade was already executed recently
            if self.tracker.is_duplicate_trade(
                signal.strategy_name,
                signal.pair,
                signal.signal_type,
                signal.entry_price,
                tolerance_pct=0.3  # Stricter for trades
            ):
                print(f"   🔄 Skipping duplicate trade: {signal.pair} {signal.signal_type} ({signal.strategy_name})")
                continue
            
            new_signals.append(signal)
        
        if not new_signals:
            if signals:
                print(f"   ℹ️  All {len(signals)} trade(s) were duplicates (already executed recently)")
            return
        
        # Get current open positions
        open_positions = self.bybit.get_open_positions_count()
        available_slots = max(0, self.config.MAX_CONCURRENT_TRADES - open_positions)
        
        if available_slots == 0:
            print(f"   ⚠️  Max concurrent trades reached ({self.config.MAX_CONCURRENT_TRADES})")
            print(f"      Skipping {len(new_signals)} signal(s)")
            return
        
        # Limit signals to available slots
        signals_to_execute = new_signals[:available_slots]
        
        if len(new_signals) > available_slots:
            print(f"   ⚠️  Only executing {available_slots}/{len(new_signals)} signals (MAX_CONCURRENT_TRADES limit)")
        
        for signal in signals_to_execute:
            # Execute in separate thread to avoid blocking
            thread = Thread(target=self._execute_signal_threaded, args=(signal,))
            thread.daemon = True
            thread.start()
    
    def _execute_signal_threaded(self, signal: StrategySignal):
        """Execute signal in separate thread"""
        try:
            result, error_msg = self._execute_signal(signal)
            
            if result:
                self._send_success_notification(signal, result)
            else:
                # Use specific error message if available
                if error_msg:
                    self._send_failure_notification(signal, error_msg)
                else:
                    self._send_failure_notification(signal, "Order placement failed")
        
        except Exception as e:
            self._send_failure_notification(signal, str(e))
    
    def _execute_signal(self, signal: StrategySignal) -> tuple:
        """
        Execute a single signal on ByBit
        
        Returns:
            Tuple of (result_dict or None, error_message or None)
        """
        symbol = signal.pair
        
        # Skip USDC pairs
        if "USDC" in symbol:
            return (None, f"{symbol} not supported (USDC pairs not available)")
        
        # Determine leverage
        if self.config.USE_MAX_LEVERAGE:
            max_leverage = self.bybit.get_max_leverage(symbol)
            if not max_leverage:
                return (None, f"Could not get max leverage for {symbol}")
            leverage = max_leverage
        else:
            leverage = self.config.FIXED_LEVERAGE
        
        # Set leverage
        if not self.bybit.set_leverage(symbol, leverage):
            pass  # Continue anyway
        
        # Calculate order value
        if self.config.USE_PERCENTAGE_OF_BALANCE:
            balance = self.bybit.get_account_balance()
            if not balance:
                return (None, "Could not get account balance")
            order_value = balance * (self.config.PERCENTAGE_OF_BALANCE / 100.0)
        else:
            order_value = leverage * self.config.ORDER_VALUE_MULTIPLIER
        
        # Calculate quantity
        qty = self.bybit.calculate_order_qty(symbol, signal.entry_price, order_value)
        
        if not qty or qty <= 0:
            return (None, f"Invalid quantity calculated: {qty} (might be below minimum)")
        
        # Determine side
        side = "Buy" if signal.signal_type == "LONG" else "Sell"
        
        # Override TP with percentage profit target if enabled
        if hasattr(self.config, 'USE_PERCENTAGE_PROFIT_TARGET') and self.config.USE_PERCENTAGE_PROFIT_TARGET:
            # Calculate TP based on percentage
            target_pct = self.config.PERCENTAGE_PROFIT_TARGET / 100.0
            
            if signal.signal_type == "LONG":
                # LONG: TP = entry * (1 + %)
                take_profit = signal.entry_price * (1 + target_pct)
            else:
                # SHORT: TP = entry * (1 - %)
                take_profit = signal.entry_price * (1 - target_pct)
            
            print(f"\n   🎯 Using {self.config.PERCENTAGE_PROFIT_TARGET}% profit target")
            print(f"      Original TP: {signal.take_profit:.8f} → Override: {take_profit:.8f}")
        else:
            # Use strategy's TP
            take_profit = signal.take_profit
        
        # Generate unique order ID
        import time
        timestamp = int(time.time() * 1000)
        order_link_id = f"{signal.strategy_name}_{symbol}_{signal.signal_type}_{timestamp}"
        
        print(f"\n   🤖 [{signal.strategy_name}] Placing {side} order for {symbol}")
        print(f"      Qty: {qty}, Entry: ~{signal.entry_price:.8f}")
        print(f"      SL: {signal.stop_loss:.8f}, TP: {take_profit:.8f}")
        print(f"      Leverage: {leverage}x, Value: ${order_value:.2f}")
        
        # Place order
        result = self.bybit.place_order(
            symbol=symbol,
            side=side,
            qty=qty,
            stop_loss=signal.stop_loss,
            take_profit=take_profit,  # Use calculated TP
            order_link_id=order_link_id
        )
        
        if not result:
            return (None, f"ByBit API rejected order for {symbol} (check symbol availability, min size, balance)")
        
        return (result, None)
    
    def _send_success_notification(self, signal: StrategySignal, order_result: Dict):
        """Send success notification via Telegram and record trade"""
        
        # Extract order ID
        order_id = None
        if 'result' in order_result:
            order_info = order_result['result']
            order_id = order_info.get('orderId', None)
        
        # Record trade in persistent tracker
        self.tracker.record_trade(
            signal.strategy_name,
            signal.pair,
            signal.signal_type,
            signal.entry_price,
            order_id=order_id
        )
        
        message = f"✅ *TRADE EXECUTED SUCCESSFULLY* ✅\n\n"
        message += f"🤖 *Strategy:* {signal.strategy_name}\n"
        message += f"📊 Pair: `{signal.pair}`\n"
        message += f"📈 Direction: *{signal.signal_type}*\n"
        message += f"⏰ Timeframe: *{signal.timeframe}*\n\n"
        
        message += f"💰 *Order Details:*\n"
        message += f"   • Entry: `{signal.entry_price:.8f}`\n"
        message += f"   • Stop Loss: `{signal.stop_loss:.8f}`\n"
        message += f"   • Take Profit: `{signal.take_profit:.8f}`\n"
        
        if signal.take_profit_2:
            message += f"   • Take Profit 2: `{signal.take_profit_2:.8f}`\n"
        
        message += f"   • R:R: `{signal.risk_reward_ratio:.2f}:1`\n"
        
        # Extract order info
        if 'result' in order_result:
            order_info = order_result['result']
            order_id = order_info.get('orderId', 'N/A')
            message += f"   • Order ID: `{order_id}`\n"
        
        message += f"\n⏱️ Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
        
        if self.telegram:
            self.telegram.send_message(message)
        
        print(f"   ✅ Trade executed successfully")
    
    def _send_failure_notification(self, signal: StrategySignal, error: str):
        """Send failure notification via Telegram"""
        
        # Skip notification for USDC pairs
        if "USDC" in signal.pair:
            return
        
        message = f"❌ *TRADE EXECUTION FAILED* ❌\n\n"
        message += f"🤖 *Strategy:* {signal.strategy_name}\n"
        message += f"📊 Pair: `{signal.pair}`\n"
        message += f"📈 Direction: *{signal.signal_type}*\n\n"
        
        message += f"💰 *Intended Setup:*\n"
        message += f"   • Entry: `{signal.entry_price:.8f}`\n"
        message += f"   • Stop Loss: `{signal.stop_loss:.8f}`\n\n"
        
        message += f"❌ *Error:*\n"
        message += f"   `{error}`\n\n"
        
        message += f"⏱️ Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
        
        if self.telegram:
            self.telegram.send_message(message)
        
        print(f"   ❌ Trade failed: {error}")
