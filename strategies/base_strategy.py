"""
Base Strategy Class
All trading strategies inherit from this abstract base class
Ensures consistent interface and behavior across all strategies
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StrategySignal:
    """
    Universal signal format for all strategies
    """
    strategy_name: str          # "POI_FVG", "CRT", "SR_CHANNEL"
    pair: str                   # Trading pair
    signal_type: str            # "LONG", "SHORT"
    entry_price: float          # Entry price
    stop_loss: float            # Stop loss price
    take_profit: float          # Primary take profit
    take_profit_2: Optional[float] = None  # Secondary TP (if applicable)
    
    # Signal metadata
    timestamp: datetime = None
    timeframe: str = ""
    confidence: str = "MEDIUM"  # "LOW", "MEDIUM", "HIGH"
    
    # Strategy-specific data
    details: Dict[str, Any] = None  # Strategy-specific information
    
    # Risk/Reward
    risk_reward_ratio: float = 0.0
    
    # Auto-trading flag
    auto_trade_enabled: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}
        
        # Calculate R:R if not set
        if self.risk_reward_ratio == 0.0:
            self._calculate_rr()
    
    def _calculate_rr(self):
        """Calculate risk:reward ratio"""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        
        if risk > 0:
            self.risk_reward_ratio = reward / risk
    
    def format_telegram_message(self) -> str:
        """
        Format signal as Telegram message
        Override in subclass for strategy-specific formatting
        """
        signal_emoji = "🟢" if self.signal_type == "LONG" else "🔴"
        
        message = f"📊 *{signal_emoji} {self.strategy_name} SIGNAL* {signal_emoji}\n\n"
        message += f"📈 Pair: `{self.pair}`\n"
        message += f"⏰ Timeframe: *{self.timeframe}*\n"
        message += f"📍 Type: *{self.signal_type}*\n"
        message += f"💎 Confidence: *{self.confidence}*\n\n"
        
        message += f"━━━━━━━━━━━━━━━━━━━━\n"
        message += f"💰 *TRADING SETUP*\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += f"🎯 *Entry:* `{self.entry_price:.8f}`\n"
        message += f"🛑 *Stop Loss:* `{self.stop_loss:.8f}`\n"
        message += f"💎 *Take Profit 1:* `{self.take_profit:.8f}`\n"
        
        if self.take_profit_2:
            message += f"💎 *Take Profit 2:* `{self.take_profit_2:.8f}`\n"
        
        message += f"📊 *Risk/Reward:* `{self.risk_reward_ratio:.2f}:1`\n\n"
        
        if self.details:
            message += f"━━━━━━━━━━━━━━━━━━━━\n"
            message += f"📋 *DETAILS*\n"
            message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for key, value in self.details.items():
                message += f"• {key}: `{value}`\n"
            message += "\n"
        
        message += f"⏱️ Time: `{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        
        return message


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    """
    
    def __init__(self, name: str, config: Any):
        self.name = name
        self.config = config
        self.enabled = self._is_enabled()
        self.auto_trade_enabled = self._is_auto_trade_enabled()
    
    @abstractmethod
    def _is_enabled(self) -> bool:
        """Check if strategy is enabled in config"""
        pass
    
    @abstractmethod
    def _is_auto_trade_enabled(self) -> bool:
        """Check if auto-trading is enabled for this strategy"""
        pass
    
    @abstractmethod
    def scan_pair(self, pair: str, **kwargs) -> List[StrategySignal]:
        """
        Scan a pair for signals
        
        Args:
            pair: Trading pair to scan
            **kwargs: Strategy-specific data (candles, context, etc.)
        
        Returns:
            List of StrategySignal objects
        """
        pass
    
    @abstractmethod
    def validate_signal(self, signal: StrategySignal) -> bool:
        """
        Validate a signal before sending/trading
        
        Args:
            signal: Signal to validate
        
        Returns:
            True if signal is valid, False otherwise
        """
        pass
    
    def get_required_data(self) -> Dict[str, Any]:
        """
        Specify what data this strategy needs
        
        Returns:
            Dict with data requirements (timeframes, lookback, etc.)
        """
        return {
            "timeframes": [],
            "lookback": 100,
            "indicators": []
        }
    
    def __str__(self):
        status = "ENABLED" if self.enabled else "DISABLED"
        auto_trade = "AUTO-TRADE ON" if self.auto_trade_enabled else "ALERTS ONLY"
        return f"{self.name} ({status}, {auto_trade})"
