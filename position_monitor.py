"""
Position Monitor
Monitors open positions and closes them when profit target % is reached
"""
import time
from typing import List, Dict, Optional
from threading import Thread, Lock
from datetime import datetime
from bybit_client import ByBitClient
from telegram_notifier import TelegramNotifier


class PositionMonitor:
    """
    Monitors open positions and automatically closes at profit target %
    """
    
    def __init__(self, config):
        self.config = config
        self.enabled = config.ENABLE_PROFIT_TARGET
        self.target_percentage = config.PROFIT_TARGET_PERCENTAGE
        self.check_interval = config.CHECK_PROFIT_INTERVAL
        
        self.bybit = ByBitClient()
        self.telegram = TelegramNotifier()
        
        self.running = False
        self.monitor_thread = None
        self.positions_lock = Lock()
        
        # Track positions we've already closed to avoid duplicates
        self.closed_positions = set()
        
        if self.enabled:
            print(f"💰 Profit Target Monitor: ENABLED")
            print(f"   Target: {self.target_percentage}% profit")
            print(f"   Check interval: {self.check_interval}s")
    
    def start(self):
        """Start monitoring positions"""
        if not self.enabled:
            return
        
        self.running = True
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("✅ Position monitor started")
    
    def stop(self):
        """Stop monitoring positions"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("🛑 Position monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_positions()
            except Exception as e:
                print(f"⚠️  Position monitor error: {e}")
            
            # Sleep in small increments so we can stop quickly
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _check_positions(self):
        """Check all open positions and close if profit target hit"""
        with self.positions_lock:
            # Get all open positions
            positions = self.bybit.get_positions()
            
            if not positions:
                return
            
            for position in positions:
                try:
                    self._check_single_position(position)
                except Exception as e:
                    symbol = position.get('symbol', 'UNKNOWN')
                    print(f"   ⚠️  Error checking {symbol}: {e}")
    
    def _check_single_position(self, position: Dict):
        """Check a single position and close if target hit"""
        symbol = position.get('symbol')
        side = position.get('side')  # Buy or Sell
        size = float(position.get('size', 0))
        
        # Skip if no position
        if size == 0:
            return
        
        # Get unrealized PnL percentage
        unrealized_pnl_pct = float(position.get('unrealisedPnl', 0))
        
        # ByBit returns PnL as decimal (e.g., 0.05 = 5%)
        # But we need to check the actual field name
        # Let's use the cumRealisedPnl or calculate from entry/mark price
        
        entry_price = float(position.get('avgPrice', 0))
        mark_price = float(position.get('markPrice', 0))
        
        if entry_price == 0 or mark_price == 0:
            return
        
        # Calculate profit percentage
        if side == "Buy":
            # Long position
            profit_pct = ((mark_price - entry_price) / entry_price) * 100
        else:
            # Short position
            profit_pct = ((entry_price - mark_price) / entry_price) * 100
        
        # Create unique position key
        position_key = f"{symbol}_{side}_{entry_price:.8f}"
        
        # Skip if already closed
        if position_key in self.closed_positions:
            return
        
        # Check if profit target hit
        if profit_pct >= self.target_percentage:
            print(f"\n   🎯 Profit target hit for {symbol}!")
            print(f"      Side: {side}, Profit: {profit_pct:.2f}%")
            
            # Close position
            success = self._close_position(symbol, side, size, profit_pct)
            
            if success:
                # Mark as closed
                self.closed_positions.add(position_key)
                
                # Send notification
                self._send_profit_notification(symbol, side, entry_price, mark_price, profit_pct)
    
    def _close_position(self, symbol: str, side: str, size: float, profit_pct: float) -> bool:
        """
        Close a position at market
        
        Args:
            symbol: Trading pair
            side: Buy or Sell (current position side)
            size: Position size
            profit_pct: Current profit percentage
        
        Returns:
            True if closed successfully
        """
        # Determine close side (opposite of position side)
        close_side = "Sell" if side == "Buy" else "Buy"
        
        print(f"   🔄 Closing {symbol} {side} position...")
        print(f"      Size: {size}, Profit: {profit_pct:.2f}%")
        
        # Close position via market order
        result = self.bybit.close_position(symbol, close_side, size)
        
        if result:
            print(f"   ✅ Position closed successfully")
            return True
        else:
            print(f"   ❌ Failed to close position")
            return False
    
    def _send_profit_notification(self, symbol: str, side: str, 
                                  entry_price: float, exit_price: float, 
                                  profit_pct: float):
        """Send Telegram notification for profit target hit"""
        
        direction = "LONG" if side == "Buy" else "SHORT"
        
        message = f"💰 *PROFIT TARGET HIT* 💰\n\n"
        message += f"📊 Pair: `{symbol}`\n"
        message += f"📈 Direction: *{direction}*\n"
        message += f"🎯 Profit: *{profit_pct:.2f}%*\n\n"
        
        message += f"💵 *Trade Details:*\n"
        message += f"   • Entry: `{entry_price:.8f}`\n"
        message += f"   • Exit: `{exit_price:.8f}`\n"
        message += f"   • Target: `{self.target_percentage}%`\n\n"
        
        message += f"✅ Position closed automatically\n"
        message += f"⏱️ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self.telegram.send_message(message)
    
    def get_monitored_positions_count(self) -> int:
        """Get count of currently monitored positions"""
        if not self.enabled:
            return 0
        
        try:
            positions = self.bybit.get_positions()
            return len([p for p in positions if float(p.get('size', 0)) > 0])
        except:
            return 0
