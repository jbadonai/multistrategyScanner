"""
Data models for tracking liquidity swing points
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SwingPoint:
    """Represents a liquidity swing point (high or low)"""
    pair: str
    swing_type: str  # "high" or "low"
    price_top: float
    price_btm: float
    bar_index: int
    timestamp: datetime
    count: int = 0
    volume: float = 0.0
    crossed: bool = False
    
    def __hash__(self):
        """Make SwingPoint hashable for set operations"""
        return hash((self.pair, self.swing_type, self.bar_index, self.timestamp))
    
    def is_swept(self, current_close: float) -> bool:
        """Check if the swing point has been swept by price"""
        if self.swing_type == "high":
            return current_close > self.price_top
        else:  # "low"
            return current_close < self.price_btm
    
    def is_in_zone(self, high: float, low: float) -> bool:
        """Check if a candle is within the swing zone"""
        return low < self.price_top and high > self.price_btm
    
    def update_metrics(self, volume: float):
        """Update count and volume metrics"""
        self.count += 1
        self.volume += volume


@dataclass
class MarketData:
    """Represents OHLCV market data for a candle"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @classmethod
    def from_binance(cls, kline):
        """Create MarketData from Binance kline format"""
        return cls(
            timestamp=kline[0],
            open=float(kline[1]),
            high=float(kline[2]),
            low=float(kline[3]),
            close=float(kline[4]),
            volume=float(kline[5])
        )


@dataclass
class SwingAlert:
    """Alert data for swept liquidity"""
    pair: str
    swing_type: str
    swing_price_top: float
    swing_price_btm: float
    sweep_price: float
    swing_timestamp: datetime
    sweep_timestamp: datetime
    count: int
    volume: float
    poi_context: Optional[dict] = None  # Contains trend, protected, daily_open, all_pois
    
    def format_message(self, poi_manager=None) -> str:
        """Format alert message for Telegram"""
        swing_label = "Swing High" if self.swing_type == "high" else "Swing Low"
        
        message = f"🔔 *LIQUIDITY SWEPT* 🔔\n\n"
        message += f"📊 Pair: `{self.pair}`\n"
        
        # Add POI context if available
        if self.poi_context:
            trend_emoji = "📈" if self.poi_context["trend"] == "uptrend" else "📉"
            # Correct: uptrend protects LOW, downtrend protects HIGH
            protected_label = "Prev Day Low" if self.poi_context["trend"] == "uptrend" else "Prev Day High"
            message += f"{trend_emoji} Trend: *{self.poi_context['trend'].upper()}*\n"
            message += f"🛡️ {protected_label}: `{self.poi_context['protected']:.8f}`\n"
            message += f"🔓 Daily Open: `{self.poi_context['daily_open']:.8f}`\n"
            message += f"\n"
        
        message += f"📍 Type: *{swing_label} POI MITIGATED*\n" if self.poi_context else f"📍 Type: *{swing_label}*\n"
        message += f"💰 Swing Zone: `{self.swing_price_btm:.8f}` - `{self.swing_price_top:.8f}`\n"
        message += f"🎯 Sweep Price: `{self.sweep_price:.8f}`\n"
        message += f"📈 Touches: `{self.count}`\n"
        message += f"📦 Volume: `{self.volume:,.2f}`\n"
        message += f"⏰ Swing Time: `{self.swing_timestamp.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        message += f"⏱️ Sweep Time: `{self.sweep_timestamp.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        
        # Add all POIs list if in POI mode
        if self.poi_context and poi_manager:
            message += f"\n{poi_manager.format_poi_list(self.pair)}"
        
        return message


@dataclass
class FVGAlert:
    """Alert data for FVG formation after sweep"""
    pair: str
    fvg_type: str  # "bullish" or "bearish"
    gap_top: float
    gap_bottom: float
    candle_2_body: float
    candle_3_body: float
    body_ratio: float
    candles_after_sweep: int
    fvg_timestamp: datetime
    sweep_timestamp: datetime
    original_sweep: SwingAlert  # Reference to original sweep alert
    
    def format_message(self) -> str:
        """Format FVG alert message for Telegram"""
        fvg_emoji = "🟢" if self.fvg_type == "bullish" else "🔴"
        fvg_label = "BULLISH FVG" if self.fvg_type == "bullish" else "BEARISH FVG"
        
        message = f"✨ *{fvg_emoji} {fvg_label} DETECTED* ✨\n\n"
        message += f"📊 Pair: `{self.pair}`\n"
        message += f"🎯 Type: *{fvg_label}* (Confirmation Signal)\n\n"
        
        message += f"📐 FVG Gap Zone:\n"
        message += f"   Top: `{self.gap_top:.8f}`\n"
        message += f"   Bottom: `{self.gap_bottom:.8f}`\n"
        message += f"   Size: `{abs(self.gap_top - self.gap_bottom):.8f}`\n\n"
        
        message += f"📊 Candle Analysis:\n"
        message += f"   Candle 2 Body: `{self.candle_2_body:.8f}`\n"
        message += f"   Candle 3 Body: `{self.candle_3_body:.8f}`\n"
        message += f"   Body Ratio: `{self.body_ratio:.2f}x` (2x+ required)\n\n"
        
        message += f"⏱️ Timing:\n"
        message += f"   Sweep Time: `{self.sweep_timestamp.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        message += f"   FVG Formed: `{self.fvg_timestamp.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        message += f"   Candles After Sweep: `{self.candles_after_sweep}`\n\n"
        
        message += f"🔗 Related to previous liquidity sweep:\n"
        message += f"   {self.original_sweep.swing_type.title()} swept at `{self.original_sweep.sweep_price:.8f}`\n"
        
        return message


@dataclass
class CRTAlert:
    """Alert data for CRT (Change of Retail Tendency) pattern"""
    pair: str
    crt_type: str  # "bullish" or "bearish"
    candle_1_high: float
    candle_1_low: float
    candle_2_high: float
    candle_2_low: float
    candle_2_close: float
    candle_2_open: float
    sweep_price: float  # The low (bullish) or high (bearish) that was swept
    timestamp: datetime
    candle_1_timestamp: datetime
    timeframe: str = "4h"
    body_ratio: float = 0.0  # Body ratio percentage (sweep candle / range candle)
    htf_bias: str = "neutral"  # HTF trend bias ("bullish", "bearish", or "neutral")
    
    def format_message(self) -> str:
        """Format CRT alert message for Telegram"""
        crt_emoji = "🟢" if self.crt_type == "bullish" else "🔴"
        crt_label = "BULLISH CRT" if self.crt_type == "bullish" else "BEARISH CRT"
        direction = "UP ⬆️" if self.crt_type == "bullish" else "DOWN ⬇️"
        
        # Calculate take profit (opposite liquidity)
        if self.crt_type == "bullish":
            # Bullish: swept low, target high
            take_profit = self.candle_1_high
            tp_label = "High"
        else:
            # Bearish: swept high, target low
            take_profit = self.candle_1_low
            tp_label = "Low"
        
        message = f"🎯 *{crt_emoji} {crt_label} - ENTRY SIGNAL* 🎯\n\n"
        message += f"📊 Pair: `{self.pair}`\n"
        message += f"⏰ Timeframe: *{self.timeframe.upper()}*\n"
        message += f"📈 Direction: *{direction}*\n\n"
        
        # TRADING SETUP FIRST - MOST IMPORTANT
        message += f"━━━━━━━━━━━━━━━━━━━━\n"
        message += f"💰 *TRADING SETUP*\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if self.crt_type == "bullish":
            message += f"🎯 *Entry:* `{self.candle_2_close:.8f}`\n"
            message += f"🛑 *Stop Loss:* `{self.sweep_price:.8f}` (below sweep)\n"
            message += f"💎 *Take Profit:* `{take_profit:.8f}` (opposite {tp_label})\n"
            message += f"📊 *Risk/Reward:* `{abs(take_profit - self.candle_2_close) / abs(self.candle_2_close - self.sweep_price):.2f}:1`\n\n"
            message += f"📌 *Bias:* LONG (Buy)\n"
            if self.htf_bias and self.htf_bias != "neutral":
                htf_emoji = "✅" if self.htf_bias == "bullish" else "⚠️"
                message += f"📈 *HTF Trend:* {self.htf_bias.upper()} {htf_emoji}\n"
            message += f"💡 *Rationale:* Low swept → Retail trapped short → Smart money long\n\n"
        else:
            message += f"🎯 *Entry:* `{self.candle_2_close:.8f}`\n"
            message += f"🛑 *Stop Loss:* `{self.sweep_price:.8f}` (above sweep)\n"
            message += f"💎 *Take Profit:* `{take_profit:.8f}` (opposite {tp_label})\n"
            message += f"📊 *Risk/Reward:* `{abs(self.candle_2_close - take_profit) / abs(self.sweep_price - self.candle_2_close):.2f}:1`\n\n"
            message += f"📌 *Bias:* SHORT (Sell)\n"
            if self.htf_bias and self.htf_bias != "neutral":
                htf_emoji = "✅" if self.htf_bias == "bearish" else "⚠️"
                message += f"📉 *HTF Trend:* {self.htf_bias.upper()} {htf_emoji}\n"
            message += f"💡 *Rationale:* High swept → Retail trapped long → Smart money short\n\n"
        
        # PATTERN DETAILS SECOND
        message += f"━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📍 *PATTERN DETAILS*\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += f"Candle 1 (Range):\n"
        message += f"   • High: `{self.candle_1_high:.8f}`\n"
        message += f"   • Low: `{self.candle_1_low:.8f}`\n"
        message += f"   • Size: `{self.candle_1_high - self.candle_1_low:.8f}`\n\n"
        
        message += f"Candle 2 (CRT Action):\n"
        message += f"   • Open: `{self.candle_2_open:.8f}`\n"
        message += f"   • Close: `{self.candle_2_close:.8f}` ✅\n"
        
        if self.crt_type == "bullish":
            message += f"   • Swept Low: `{self.sweep_price:.8f}` 🔻\n"
            message += f"   • Closed back in range ✅\n"
        else:
            message += f"   • Swept High: `{self.sweep_price:.8f}` 🔺\n"
            message += f"   • Closed back in range ✅\n"
        
        # Add body ratio quality indicator
        if self.body_ratio > 0:
            quality = "Strong" if self.body_ratio < 20 else "Good" if self.body_ratio < 40 else "Weak"
            message += f"   • Body Ratio: `{self.body_ratio:.1f}%` ({quality}) 📊\n\n"
        else:
            message += "\n"
        
        message += f"⏱️ *Timing:*\n"
        message += f"   • Candle 1: `{self.candle_1_timestamp.strftime('%Y-%m-%d %H:%M')}`\n"
        message += f"   • Confirmed: `{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        
        # Add signal age for transparency
        from datetime import datetime
        signal_age = datetime.now() - self.timestamp
        age_seconds = signal_age.total_seconds()
        if age_seconds < 60:
            age_display = f"{int(age_seconds)}s"
        else:
            age_display = f"{int(age_seconds / 60)}m {int(age_seconds % 60)}s"
        message += f"   • Signal Age: `{age_display}` ✅ Fresh\n"
        
        return message
