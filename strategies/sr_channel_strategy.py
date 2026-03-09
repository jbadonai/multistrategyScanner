"""
SR Channel Strategy
Professional Support/Resistance Channel trading with:
- Institutional liquidity trap detection
- Fake breakout filtering  
- Multi-timeframe validation
- Professional entry/exit rules
"""
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from strategies.base_strategy import BaseStrategy, StrategySignal
from models import MarketData


@dataclass
class SRChannel:
    """Represents a validated SR channel"""
    resistance: float
    support: float
    resistance_touches: List[int]  # Candle indices that touched resistance
    support_touches: List[int]     # Candle indices that touched support
    first_touch_time: datetime
    last_touch_time: datetime
    width_pct: float              # Channel width as % of price
    balance_ratio: float          # Touch balance (0.5 = perfect balance)
    
    def is_valid(self, min_touches: int, min_per_side: int, 
                 min_width: float, max_width: float, balance_tolerance: float) -> bool:
        """Check if channel meets validation criteria"""
        total_touches = len(self.resistance_touches) + len(self.support_touches)
        
        # Must have minimum total touches
        if total_touches < min_touches:
            return False
        
        # Must have minimum touches per side
        if len(self.resistance_touches) < min_per_side or len(self.support_touches) < min_per_side:
            return False
        
        # Width must be in acceptable range
        if self.width_pct < min_width or self.width_pct > max_width:
            return False
        
        # Balance between sides
        if abs(self.balance_ratio - 0.5) > balance_tolerance:
            return False
        
        return True
    
    def get_midline(self) -> float:
        """Get channel midpoint"""
        return (self.resistance + self.support) / 2


class SRChannelStrategy(BaseStrategy):
    """
    SR Channel Strategy Implementation
    Professional-grade with institutional improvements
    """
    
    def __init__(self, config):
        super().__init__("SR_CHANNEL", config)
        
        # Load configuration
        self.timeframe = config.SR_TIMEFRAME
        self.htf_timeframe = config.SR_HTF_TIMEFRAME
        self.min_touches = config.SR_MIN_TOUCHES
        self.min_touches_per_side = config.SR_MIN_TOUCHES_PER_SIDE
        self.min_width_pct = config.SR_MIN_CHANNEL_WIDTH
        self.max_width_pct = config.SR_MAX_CHANNEL_WIDTH
        self.balance_tolerance = config.SR_BALANCE_TOLERANCE
        
        # Entry rules
        self.require_rejection_wick = config.SR_REQUIRE_REJECTION_WICK
        self.min_wick_ratio = config.SR_MIN_WICK_RATIO
        self.require_momentum_slow = config.SR_REQUIRE_MOMENTUM_SLOW
        self.confirmation_candles = config.SR_CONFIRMATION_CANDLES
        
        # Liquidity trap detection
        self.detect_traps = config.SR_DETECT_LIQUIDITY_TRAPS
        self.trap_threshold = config.SR_TRAP_THRESHOLD
        self.require_quick_return = config.SR_REQUIRE_QUICK_RETURN
        self.max_candles_after_sweep = config.SR_MAX_CANDLES_AFTER_SWEEP
        
        # Fake breakout detection
        self.detect_fake_breakouts = config.SR_DETECT_FAKE_BREAKOUTS
        self.min_breakout_body_ratio = config.SR_MIN_BREAKOUT_BODY_RATIO
        self.allow_retest_entry = config.SR_ALLOW_RETEST_ENTRY
        
        # Risk management
        self.target_mid_channel = config.SR_TARGET_MID_CHANNEL
        self.min_rr_ratio = config.SR_MIN_RR_RATIO
        self.max_signal_age = timedelta(minutes=config.SR_MAX_SIGNAL_AGE_MINUTES)
        
        # Advanced improvements
        self.use_atr_zones = getattr(config, 'SR_USE_ATR_ZONES', True)
        self.atr_zone_multiplier = getattr(config, 'SR_ATR_ZONE_MULTIPLIER', 0.5)
        self.require_volume_confirmation = getattr(config, 'SR_REQUIRE_VOLUME', True)
        self.volume_spike_threshold = getattr(config, 'SR_VOLUME_SPIKE', 1.5)
        self.min_channel_quality_score = getattr(config, 'SR_MIN_QUALITY_SCORE', 3)
        self.enable_trend_filter = getattr(config, 'SR_ENABLE_TREND_FILTER', True)
        self.max_trend_strength = getattr(config, 'SR_MAX_TREND_STRENGTH', 0.015)
        self.signal_expiry_candles = getattr(config, 'SR_SIGNAL_EXPIRY_CANDLES', 2)
        self.max_channel_age = getattr(config, 'SR_MAX_CHANNEL_AGE', 200)
        self.require_reversal_strength = getattr(config, 'SR_REQUIRE_REVERSAL_STRENGTH', True)
        self.min_reversal_atr_multiple = getattr(config, 'SR_MIN_REVERSAL_ATR', 0.6)
        
        # Cache active channels per pair
        self.active_channels: Dict[str, Optional[SRChannel]] = {}
        
        # Duplicate prevention - track last signal per pair
        self.last_signals: Dict[str, Dict] = {}  # pair -> {type, entry, time}
        
        # Track trades per channel to prevent overtrading
        self.channel_trade_count: Dict[str, int] = {}
        self.max_trades_per_channel = getattr(config, 'SR_MAX_TRADES_PER_CHANNEL', 2)
    
    def _is_enabled(self) -> bool:
        return self.config.ENABLE_SR_STRATEGY
    
    def _is_auto_trade_enabled(self) -> bool:
        return self.config.SR_AUTO_TRADE
    
    def get_required_data(self) -> Dict:
        return {
            "timeframes": [self.timeframe, self.htf_timeframe],
            "lookback": 100,  # Need enough candles to identify channels
            "indicators": []
        }
    
    def scan_pair(self, pair: str, **kwargs) -> List[StrategySignal]:
        """
        Scan for SR channel signals
        
        Required kwargs:
            - candles: List[MarketData] for execution timeframe
            - htf_candles: List[MarketData] for higher timeframe context (optional)
        """
        candles = kwargs.get('candles', [])
        htf_candles = kwargs.get('htf_candles', [])
        
        if not candles or len(candles) < 50:
            return []
        
        signals = []
        
        # Calculate ATR for adaptive zones
        atr = self._calculate_atr(candles, period=14)
        
        # Trend filter - skip if strong trend
        if self.enable_trend_filter and self._is_strong_trend(candles):
            return []  # Skip channel trading in strong trends
        
        # Step 1: Identify or validate active channel
        channel = self._identify_channel(pair, candles)
        
        if not channel:
            return []
        
        # Check channel age
        if self._get_channel_age(channel) > self.max_channel_age:
            return []  # Channel too old
        
        # Score channel quality
        quality_score = self._score_channel_quality(channel, candles)
        if quality_score < self.min_channel_quality_score:
            return []  # Low quality channel
        
        # Check if we've overtraded this channel
        channel_key = f"{pair}_{channel.support:.2f}_{channel.resistance:.2f}"
        if self.channel_trade_count.get(channel_key, 0) >= self.max_trades_per_channel:
            return []  # Max trades reached for this channel
        
        # Step 2: Check for liquidity trap signals
        if self.detect_traps:
            trap_signal = self._check_liquidity_trap(pair, candles, channel, atr)
            if trap_signal and not self._is_duplicate_signal(pair, trap_signal):
                # Increment channel trade count
                self.channel_trade_count[channel_key] = self.channel_trade_count.get(channel_key, 0) + 1
                signals.append(trap_signal)
                self._update_last_signal(pair, trap_signal)
        
        # Step 3: Check for support/resistance bounce signals
        bounce_signal = self._check_bounce_entry(pair, candles, channel, atr)
        if bounce_signal and not self._is_duplicate_signal(pair, bounce_signal):
            # Increment channel trade count
            self.channel_trade_count[channel_key] = self.channel_trade_count.get(channel_key, 0) + 1
            signals.append(bounce_signal)
            self._update_last_signal(pair, bounce_signal)
        
        # Step 4: Check for breakout signals (if enabled)
        if not self.detect_fake_breakouts or self.allow_retest_entry:
            breakout_signal = self._check_breakout_retest(pair, candles, channel)
            if breakout_signal and not self._is_duplicate_signal(pair, breakout_signal):
                signals.append(breakout_signal)
                self._update_last_signal(pair, breakout_signal)
        
        return signals
    
    def _calculate_atr(self, candles: List[MarketData], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(candles) < period + 1:
            return 0.0
        
        recent = candles[-(period+1):]
        true_ranges = []
        
        for i in range(1, len(recent)):
            high = recent[i].high
            low = recent[i].low
            prev_close = recent[i-1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
    
    def _is_strong_trend(self, candles: List[MarketData]) -> bool:
        """Check if market is in strong trend (avoid mean reversion)"""
        if len(candles) < 50:
            return False
        
        # Calculate EMA50 and EMA200
        closes = [c.close for c in candles]
        
        ema50 = self._calculate_ema(closes, 50)
        ema200 = self._calculate_ema(closes, 200)
        
        if ema50 == 0 or ema200 == 0:
            return False
        
        current_price = closes[-1]
        trend_strength = abs(ema50 - ema200) / current_price
        
        return trend_strength > self.max_trend_strength
    
    def _calculate_ema(self, data: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return 0.0
        
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period  # Start with SMA
        
        for price in data[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _score_channel_quality(self, channel: SRChannel, candles: List[MarketData]) -> int:
        """
        Score channel quality
        Higher score = better channel
        """
        score = 0
        
        # Equal highs/lows (symmetrical)
        if abs(channel.balance_ratio - 0.5) < 0.1:
            score += 1
        
        # More than 6 touches
        total_touches = len(channel.resistance_touches) + len(channel.support_touches)
        if total_touches >= 6:
            score += 1
        
        # Clean wick rejections (check recent touches)
        if self._has_clean_rejections(channel, candles):
            score += 1
        
        # Volume reaction at boundaries (if enabled)
        if self.require_volume_confirmation:
            if self._has_volume_reactions(channel, candles):
                score += 1
        
        # Narrow channel (precision)
        if channel.width_pct < 2.0:
            score += 1
        
        return score
    
    def _has_clean_rejections(self, channel: SRChannel, candles: List[MarketData]) -> bool:
        """Check if touches have clean rejection wicks"""
        clean_count = 0
        
        # Check last 3 touches on each side
        recent_res_touches = channel.resistance_touches[-3:] if len(channel.resistance_touches) >= 3 else channel.resistance_touches
        recent_sup_touches = channel.support_touches[-3:] if len(channel.support_touches) >= 3 else channel.support_touches
        
        for idx in recent_res_touches:
            if idx < len(candles):
                candle = candles[idx]
                upper_wick = candle.high - max(candle.open, candle.close)
                candle_range = candle.high - candle.low
                if candle_range > 0 and (upper_wick / candle_range) >= 0.3:
                    clean_count += 1
        
        for idx in recent_sup_touches:
            if idx < len(candles):
                candle = candles[idx]
                lower_wick = min(candle.open, candle.close) - candle.low
                candle_range = candle.high - candle.low
                if candle_range > 0 and (lower_wick / candle_range) >= 0.3:
                    clean_count += 1
        
        return clean_count >= 3
    
    def _has_volume_reactions(self, channel: SRChannel, candles: List[MarketData]) -> bool:
        """Check if volume spikes at channel boundaries"""
        # Simplified - would need actual volume data
        # For now, return True to not penalize when volume unavailable
        return True
    
    def _get_channel_age(self, channel: SRChannel) -> int:
        """Get channel age in candles"""
        age = datetime.now() - channel.first_touch_time
        # Approximate candles based on timeframe
        if self.timeframe == "15m":
            return int(age.total_seconds() / (15 * 60))
        elif self.timeframe == "1h":
            return int(age.total_seconds() / (60 * 60))
        else:
            return 0
    
    def _identify_channel(self, pair: str, candles: List[MarketData]) -> Optional[SRChannel]:
        """
        Identify or validate SR channel
        Uses last 50-100 candles to find consistent channel
        """
        if len(candles) < 50:
            return None
        
        # Use recent candles for channel identification
        recent_candles = candles[-100:] if len(candles) >= 100 else candles
        
        # Find potential resistance and support levels
        highs = [c.high for c in recent_candles]
        lows = [c.low for c in recent_candles]
        
        # Method 1: Use recent swing highs/lows
        resistance_candidates = self._find_resistance_levels(recent_candles)
        support_candidates = self._find_support_levels(recent_candles)
        
        # Try to form channels from candidates
        best_channel = None
        best_score = 0
        
        for resistance in resistance_candidates:
            for support in support_candidates:
                if support >= resistance:
                    continue
                
                channel = self._form_channel(recent_candles, resistance, support)
                
                if channel and channel.is_valid(
                    self.min_touches, 
                    self.min_touches_per_side,
                    self.min_width_pct,
                    self.max_width_pct,
                    self.balance_tolerance
                ):
                    # Score channel (prefer more touches and better balance)
                    total_touches = len(channel.resistance_touches) + len(channel.support_touches)
                    balance_score = 1 - abs(channel.balance_ratio - 0.5)
                    score = total_touches * balance_score
                    
                    if score > best_score:
                        best_score = score
                        best_channel = channel
        
        # Cache the channel
        self.active_channels[pair] = best_channel
        
        return best_channel
    
    def _find_resistance_levels(self, candles: List[MarketData]) -> List[float]:
        """Find potential resistance levels from swing highs"""
        levels = []
        
        for i in range(2, len(candles) - 2):
            if (candles[i].high > candles[i-1].high and 
                candles[i].high > candles[i-2].high and
                candles[i].high > candles[i+1].high and 
                candles[i].high > candles[i+2].high):
                levels.append(candles[i].high)
        
        return levels
    
    def _find_support_levels(self, candles: List[MarketData]) -> List[float]:
        """Find potential support levels from swing lows"""
        levels = []
        
        for i in range(2, len(candles) - 2):
            if (candles[i].low < candles[i-1].low and 
                candles[i].low < candles[i-2].low and
                candles[i].low < candles[i+1].low and 
                candles[i].low < candles[i+2].low):
                levels.append(candles[i].low)
        
        return levels
    
    def _form_channel(self, candles: List[MarketData], resistance: float, 
                     support: float) -> Optional[SRChannel]:
        """Form channel and count touches"""
        
        tolerance = (resistance - support) * 0.02  # 2% tolerance
        
        resistance_touches = []
        support_touches = []
        first_touch_time = None
        last_touch_time = None
        
        for i, candle in enumerate(candles):
            # Check resistance touch
            if abs(candle.high - resistance) <= tolerance:
                resistance_touches.append(i)
                touch_time = datetime.fromtimestamp(candle.timestamp / 1000)
                if first_touch_time is None:
                    first_touch_time = touch_time
                last_touch_time = touch_time
            
            # Check support touch
            if abs(candle.low - support) <= tolerance:
                support_touches.append(i)
                touch_time = datetime.fromtimestamp(candle.timestamp / 1000)
                if first_touch_time is None:
                    first_touch_time = touch_time
                last_touch_time = touch_time
        
        if not resistance_touches or not support_touches:
            return None
        
        # Calculate metrics
        mid_price = (resistance + support) / 2
        width_pct = ((resistance - support) / mid_price) * 100
        
        total_touches = len(resistance_touches) + len(support_touches)
        balance_ratio = len(resistance_touches) / total_touches
        
        return SRChannel(
            resistance=resistance,
            support=support,
            resistance_touches=resistance_touches,
            support_touches=support_touches,
            first_touch_time=first_touch_time,
            last_touch_time=last_touch_time,
            width_pct=width_pct,
            balance_ratio=balance_ratio
        )
    
    def _check_liquidity_trap(self, pair: str, candles: List[MarketData], 
                             channel: SRChannel, atr: float) -> Optional[StrategySignal]:
        """
        Detect liquidity trap entries (PROFESSIONAL METHOD)
        
        Pattern:
        1. Price breaks below support (liquidity sweep)
        2. Quick return above support (within N candles)
        3. Bullish confirmation candle
        """
        if len(candles) < 5:
            return None
        
        recent = candles[-5:]
        
        # Check for support liquidity trap (bullish)
        support_trap = self._check_support_trap(pair, recent, channel)
        if support_trap:
            return support_trap
        
        # Check for resistance liquidity trap (bearish)
        resistance_trap = self._check_resistance_trap(pair, recent, channel)
        if resistance_trap:
            return resistance_trap
        
        return None
    
    def _check_support_trap(self, pair: str, candles: List[MarketData], 
                           channel: SRChannel) -> Optional[StrategySignal]:
        """Check for bullish liquidity trap at support"""
        
        sweep_threshold = channel.support * (1 - self.trap_threshold / 100)
        
        sweep_candle_idx = None
        sweep_low = None
        
        # Find sweep candle
        for i, candle in enumerate(candles):
            if candle.low < sweep_threshold:
                sweep_candle_idx = i
                sweep_low = candle.low
                break
        
        if sweep_candle_idx is None:
            return None
        
        # Check if price returned above support
        returned = False
        return_idx = None
        
        for i in range(sweep_candle_idx + 1, len(candles)):
            if candles[i].close > channel.support:
                returned = True
                return_idx = i
                break
        
        if not returned:
            return None
        
        # Check if return was quick
        candles_to_return = return_idx - sweep_candle_idx
        if self.require_quick_return and candles_to_return > self.max_candles_after_sweep:
            return None
        
        # Check for bullish confirmation
        last_candle = candles[-1]
        if last_candle.close <= last_candle.open:  # Not bullish
            return None
        
        # Valid liquidity trap!
        entry = last_candle.close
        stop_loss = sweep_low
        take_profit = channel.get_midline() if self.target_mid_channel else channel.resistance
        
        # Check R:R
        risk = entry - stop_loss
        reward = take_profit - entry
        rr = reward / risk if risk > 0 else 0
        
        if rr < self.min_rr_ratio:
            return None
        
        details = {
            "Signal Type": "Liquidity Trap (Support)",
            "Channel": f"{channel.resistance:.8f} - {channel.support:.8f}",
            "Sweep Low": f"{sweep_low:.8f}",
            "Return Time": f"{candles_to_return} candles",
            "Channel Touches": f"{len(channel.resistance_touches) + len(channel.support_touches)} total"
        }
        
        signal = StrategySignal(
            strategy_name="SR_CHANNEL",
            pair=pair,
            signal_type="LONG",
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            take_profit_2=channel.resistance if self.target_mid_channel else None,
            timestamp=datetime.now(),
            timeframe=self.timeframe,
            confidence="HIGH",
            details=details,
            auto_trade_enabled=self.auto_trade_enabled
        )
        
        return signal
    
    def _check_resistance_trap(self, pair: str, candles: List[MarketData], 
                              channel: SRChannel) -> Optional[StrategySignal]:
        """Check for bearish liquidity trap at resistance (inverse of support trap)"""
        
        sweep_threshold = channel.resistance * (1 + self.trap_threshold / 100)
        
        sweep_candle_idx = None
        sweep_high = None
        
        for i, candle in enumerate(candles):
            if candle.high > sweep_threshold:
                sweep_candle_idx = i
                sweep_high = candle.high
                break
        
        if sweep_candle_idx is None:
            return None
        
        returned = False
        return_idx = None
        
        for i in range(sweep_candle_idx + 1, len(candles)):
            if candles[i].close < channel.resistance:
                returned = True
                return_idx = i
                break
        
        if not returned:
            return None
        
        candles_to_return = return_idx - sweep_candle_idx
        if self.require_quick_return and candles_to_return > self.max_candles_after_sweep:
            return None
        
        last_candle = candles[-1]
        if last_candle.close >= last_candle.open:
            return None
        
        entry = last_candle.close
        stop_loss = sweep_high
        take_profit = channel.get_midline() if self.target_mid_channel else channel.support
        
        risk = stop_loss - entry
        reward = entry - take_profit
        rr = reward / risk if risk > 0 else 0
        
        if rr < self.min_rr_ratio:
            return None
        
        details = {
            "Signal Type": "Liquidity Trap (Resistance)",
            "Channel": f"{channel.resistance:.8f} - {channel.support:.8f}",
            "Sweep High": f"{sweep_high:.8f}",
            "Return Time": f"{candles_to_return} candles",
            "Channel Touches": f"{len(channel.resistance_touches) + len(channel.support_touches)} total"
        }
        
        signal = StrategySignal(
            strategy_name="SR_CHANNEL",
            pair=pair,
            signal_type="SHORT",
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            take_profit_2=channel.support if self.target_mid_channel else None,
            timestamp=datetime.now(),
            timeframe=self.timeframe,
            confidence="HIGH",
            details=details,
            auto_trade_enabled=self.auto_trade_enabled
        )
        
        return signal
    
    def _check_bounce_entry(self, pair: str, candles: List[MarketData], 
                           channel: SRChannel) -> Optional[StrategySignal]:
        """
        Check for support bounce or resistance rejection entries
        """
        if len(candles) < 3:
            return None
        
        last_candle = candles[-1]
        prev_candle = candles[-2]
        
        # Check support bounce (bullish)
        if self._is_at_support(last_candle, channel):
            if self._has_rejection_wick(last_candle, "support"):
                return self._create_bounce_signal(pair, candles, channel, "LONG")
        
        # Check resistance rejection (bearish)
        if self._is_at_resistance(last_candle, channel):
            if self._has_rejection_wick(last_candle, "resistance"):
                return self._create_bounce_signal(pair, candles, channel, "SHORT")
        
        return None
    
    def _is_at_support(self, candle: MarketData, channel: SRChannel) -> bool:
        """Check if candle is at support"""
        tolerance = (channel.resistance - channel.support) * 0.03
        return abs(candle.low - channel.support) <= tolerance
    
    def _is_at_resistance(self, candle: MarketData, channel: SRChannel) -> bool:
        """Check if candle is at resistance"""
        tolerance = (channel.resistance - channel.support) * 0.03
        return abs(candle.high - channel.resistance) <= tolerance
    
    def _has_rejection_wick(self, candle: MarketData, level_type: str) -> bool:
        """Check for rejection wick"""
        if not self.require_rejection_wick:
            return True
        
        candle_range = candle.high - candle.low
        if candle_range == 0:
            return False
        
        if level_type == "support":
            lower_wick = min(candle.open, candle.close) - candle.low
            wick_ratio = lower_wick / candle_range
        else:  # resistance
            upper_wick = candle.high - max(candle.open, candle.close)
            wick_ratio = upper_wick / candle_range
        
        return wick_ratio >= self.min_wick_ratio
    
    def _create_bounce_signal(self, pair: str, candles: List[MarketData], 
                              channel: SRChannel, signal_type: str) -> Optional[StrategySignal]:
        """Create signal for support bounce or resistance rejection"""
        
        last_candle = candles[-1]
        
        if signal_type == "LONG":
            entry = last_candle.close
            stop_loss = last_candle.low * 0.998
            take_profit = channel.get_midline() if self.target_mid_channel else channel.resistance
        else:
            entry = last_candle.close
            stop_loss = last_candle.high * 1.002
            take_profit = channel.get_midline() if self.target_mid_channel else channel.support
        
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr = reward / risk if risk > 0 else 0
        
        if rr < self.min_rr_ratio:
            return None
        
        details = {
            "Signal Type": "Support Bounce" if signal_type == "LONG" else "Resistance Rejection",
            "Channel": f"{channel.resistance:.8f} - {channel.support:.8f}",
            "Rejection Level": f"{channel.support if signal_type == 'LONG' else channel.resistance:.8f}",
            "Channel Touches": f"{len(channel.resistance_touches) + len(channel.support_touches)} total"
        }
        
        signal = StrategySignal(
            strategy_name="SR_CHANNEL",
            pair=pair,
            signal_type=signal_type,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            take_profit_2=channel.resistance if signal_type == "LONG" and self.target_mid_channel else 
                         channel.support if signal_type == "SHORT" and self.target_mid_channel else None,
            timestamp=datetime.now(),
            timeframe=self.timeframe,
            confidence="MEDIUM",
            details=details,
            auto_trade_enabled=self.auto_trade_enabled
        )
        
        return signal
    
    def _check_breakout_retest(self, pair: str, candles: List[MarketData], 
                               channel: SRChannel) -> Optional[StrategySignal]:
        """Check for breakout retest entries (if enabled)"""
        # Simplified - can be expanded
        return None
    
    def _is_duplicate_signal(self, pair: str, signal: StrategySignal) -> bool:
        """Check if signal is duplicate of recent signal"""
        if pair not in self.last_signals:
            return False
        
        last = self.last_signals[pair]
        
        # Same signal type
        if last.get("type") != signal.signal_type:
            return False
        
        # Similar entry price (within 0.5%)
        price_diff = abs(signal.entry_price - last.get("entry", 0)) / signal.entry_price
        if price_diff > 0.005:  # More than 0.5% different = new signal
            return False
        
        # Recent signal (within 5 minutes)
        time_diff = datetime.now() - last.get("time", datetime.min)
        if time_diff > timedelta(minutes=5):
            return False
        
        # It's a duplicate!
        return True
    
    def _update_last_signal(self, pair: str, signal: StrategySignal):
        """Update last signal tracker"""
        self.last_signals[pair] = {
            "type": signal.signal_type,
            "entry": signal.entry_price,
            "time": datetime.now()
        }
    
    def validate_signal(self, signal: StrategySignal) -> bool:
        """Validate SR channel signal"""
        
        # Check R:R
        if signal.risk_reward_ratio < self.min_rr_ratio:
            return False
        
        # Check signal age
        age = datetime.now() - signal.timestamp
        if age > self.max_signal_age:
            return False
        
        return True
