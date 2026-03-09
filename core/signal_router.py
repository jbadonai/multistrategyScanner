"""
Signal Router
Handles routing of strategy signals to Telegram
Manages grouping, deduplication, and formatting
"""

from typing import List, Dict
from collections import defaultdict
from strategies.base_strategy import StrategySignal
from telegram_notifier import TelegramNotifier
from persistent_tracker import PersistentSignalTracker


class SignalRouter:
    """
    Routes signals to appropriate destinations (Telegram, logging, etc.)
    """
    
    def __init__(self, config):
        self.config = config
        self.telegram = TelegramNotifier()
        self.group_by_pair = config.GROUP_ALERTS_BY_PAIR
        self.max_per_message = config.MAX_ALERTS_PER_MESSAGE
        
        # Persistent tracking to prevent duplicates across restarts
        self.tracker = PersistentSignalTracker()
        
        # Show stats on init
        stats = self.tracker.get_stats()
        if stats["total_signals"] > 0 or stats["total_trades"] > 0:
            print(f"📝 Signal history loaded: {stats['total_signals']} signals, {stats['total_trades']} trades tracked")
    
    def test_telegram(self) -> bool:
        """Test Telegram connection"""
        return self.telegram.test_connection()
    
    def route_signals(self, signals: List[StrategySignal]):
        """
        Route signals to destinations
        
        Args:
            signals: List of signals to route
        """
        if not signals:
            return
        
        # Filter out duplicate signals using persistent tracker
        new_signals = []
        for signal in signals:
            if self.tracker.is_duplicate_signal(
                signal.strategy_name,
                signal.pair,
                signal.signal_type,
                signal.entry_price
            ):
                print(f"   🔄 Skipping duplicate signal: {signal.pair} {signal.signal_type} ({signal.strategy_name})")
                continue
            
            new_signals.append(signal)
            # Record signal
            self.tracker.record_signal(
                signal.strategy_name,
                signal.pair,
                signal.signal_type,
                signal.entry_price
            )
        
        if not new_signals:
            print(f"   ℹ️  All {len(signals)} signal(s) were duplicates (already sent recently)")
            return
        
        # Group signals if configured
        if self.group_by_pair:
            grouped = self._group_by_pair(new_signals)
            self._send_grouped_signals(grouped)
        else:
            self._send_individual_signals(new_signals)
    
    def _group_by_pair(self, signals: List[StrategySignal]) -> Dict[str, List[StrategySignal]]:
        """Group signals by trading pair"""
        grouped = defaultdict(list)
        
        for signal in signals:
            grouped[signal.pair].append(signal)
        
        return grouped
    
    def _send_grouped_signals(self, grouped: Dict[str, List[StrategySignal]]):
        """Send grouped signals"""
        
        for pair, pair_signals in grouped.items():
            # Sort by priority
            sorted_signals = self._sort_by_priority(pair_signals)
            
            # If too many signals, split into batches
            if len(sorted_signals) > self.max_per_message:
                batches = [sorted_signals[i:i+self.max_per_message] 
                          for i in range(0, len(sorted_signals), self.max_per_message)]
            else:
                batches = [sorted_signals]
            
            # Send each batch
            for batch in batches:
                message = self._format_grouped_message(pair, batch)
                success = self.telegram.send_message(message)
                
                if success:
                    print(f"   📤 Sent {len(batch)} signal(s) for {pair}")
                else:
                    print(f"   ❌ Failed to send signals for {pair}")
    
    def _send_individual_signals(self, signals: List[StrategySignal]):
        """Send signals individually"""
        
        for signal in signals:
            message = signal.format_telegram_message()
            success = self.telegram.send_message(message)
            
            if success:
                print(f"   📤 Sent {signal.strategy_name} signal for {signal.pair}")
            else:
                print(f"   ❌ Failed to send signal for {signal.pair}")
    
    def _sort_by_priority(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """Sort signals by strategy priority"""
        
        priority_map = self.config.STRATEGY_PRIORITIES
        
        return sorted(signals, 
                     key=lambda s: priority_map.get(s.strategy_name, 0), 
                     reverse=True)
    
    def _format_grouped_message(self, pair: str, signals: List[StrategySignal]) -> str:
        """Format multiple signals for same pair into one message"""
        
        message = f"🎯 *MULTIPLE SIGNALS FOR {pair}* 🎯\n"
        message += f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"📊 {len(signals)} signal(s) detected:\n\n"
        
        for i, signal in enumerate(signals, 1):
            signal_emoji = "🟢" if signal.signal_type == "LONG" else "🔴"
            
            message += f"{i}️⃣ *{signal_emoji} {signal.strategy_name}* ({signal.timeframe})\n"
            message += f"   Type: *{signal.signal_type}*\n"
            message += f"   Entry: `{signal.entry_price:.8f}`\n"
            message += f"   Stop: `{signal.stop_loss:.8f}`\n"
            message += f"   TP: `{signal.take_profit:.8f}`\n"
            message += f"   R:R: `{signal.risk_reward_ratio:.2f}:1`\n"
            message += f"   Confidence: *{signal.confidence}*\n"
            
            if signal.auto_trade_enabled:
                message += f"   🤖 Auto-trade: ENABLED\n"
            
            message += "\n"
        
        message += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"⏱️ Time: `{signals[0].timestamp.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        
        return message
