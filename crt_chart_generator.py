"""
CRT Chart Generator for Telegram
Creates simple ASCII chart visualization of CRT patterns
"""
from typing import List, Dict
from models import MarketData


class CRTChartGenerator:
    """Generates ASCII chart of CRT pattern for Telegram"""
    
    @staticmethod
    def generate_crt_chart(candles: List[MarketData], crt_data: Dict) -> str:
        """
        Generate ASCII chart showing CRT pattern
        
        Args:
            candles: List of candles (last 5-7 candles)
            crt_data: CRT detection result with candle_1 and candle_2 info
        
        Returns:
            ASCII chart as string
        """
        if len(candles) < 3:
            return "❌ Not enough candles for chart"
        
        # Get last 5 candles for context
        display_candles = candles[-5:] if len(candles) >= 5 else candles
        
        # Extract values
        highs = [c.high for c in display_candles]
        lows = [c.low for c in display_candles]
        opens = [c.open for c in display_candles]
        closes = [c.close for c in display_candles]
        
        # Find range for normalization
        max_price = max(highs)
        min_price = min(lows)
        price_range = max_price - min_price
        
        if price_range == 0:
            return "❌ No price movement"
        
        # Chart settings
        chart_height = 15
        chart_width = len(display_candles) * 6
        
        # CRT pattern info
        candle_1_high = crt_data.get('candle_1_high')
        candle_1_low = crt_data.get('candle_1_low')
        candle_2_high = crt_data.get('candle_2_high')
        candle_2_low = crt_data.get('candle_2_low')
        candle_2_close = crt_data.get('candle_2_close')
        crt_type = crt_data.get('type')
        
        # Build chart
        chart_lines = []
        chart_lines.append("📊 CRT Pattern Visualization:")
        chart_lines.append("")
        
        # Price levels
        chart_lines.append(f"Candle 1 Range: {candle_1_high:.8f} - {candle_1_low:.8f}")
        chart_lines.append(f"Candle 2 High:  {candle_2_high:.8f}")
        chart_lines.append(f"Candle 2 Low:   {candle_2_low:.8f}")
        chart_lines.append(f"Candle 2 Close: {candle_2_close:.8f}")
        chart_lines.append("")
        
        # Pattern info
        if crt_type == "bearish":
            swept = f"Swept HIGH by {(candle_2_high - candle_1_high):.8f}"
            closed = "Closed INSIDE range"
        else:
            swept = f"Swept LOW by {(candle_1_low - candle_2_low):.8f}"
            closed = "Closed INSIDE range"
        
        chart_lines.append(f"Pattern: {crt_type.upper()}")
        chart_lines.append(f"Sweep: {swept}")
        chart_lines.append(f"Close: {closed}")
        chart_lines.append("")
        
        # Simple candle representation
        chart_lines.append("Last 5 Candles:")
        chart_lines.append("")
        
        for i, candle in enumerate(display_candles):
            candle_num = i + 1
            is_candle_1 = (i == len(display_candles) - 3)
            is_candle_2 = (i == len(display_candles) - 2)
            
            # Candle label
            if is_candle_1:
                label = f"C{candle_num} [C1]"
            elif is_candle_2:
                label = f"C{candle_num} [C2] ← CRT"
            else:
                label = f"C{candle_num}"
            
            # Candle direction
            if candle.close > candle.open:
                direction = "🟢 BULL"
            elif candle.close < candle.open:
                direction = "🔴 BEAR"
            else:
                direction = "⚪ DOJI"
            
            # Build line
            line = f"{label:<12} {direction}"
            line += f"  H:{candle.high:.8f}"
            line += f"  L:{candle.low:.8f}"
            line += f"  C:{candle.close:.8f}"
            
            # Mark sweep
            if is_candle_2:
                if crt_type == "bearish" and candle.high > candle_1_high:
                    line += " ⚠️ SWEPT HIGH"
                elif crt_type == "bullish" and candle.low < candle_1_low:
                    line += " ⚠️ SWEPT LOW"
            
            chart_lines.append(line)
        
        chart_lines.append("")
        chart_lines.append("─" * 50)
        
        # Verification checks
        chart_lines.append("")
        chart_lines.append("✅ Verification:")
        
        if crt_type == "bearish":
            swept_correctly = candle_2_high > candle_1_high
            closed_in_range = candle_1_low < candle_2_close < candle_1_high
            
            chart_lines.append(f"  {'✅' if swept_correctly else '❌'} High swept: {candle_2_high:.8f} > {candle_1_high:.8f}")
            chart_lines.append(f"  {'✅' if closed_in_range else '❌'} Close in range: {candle_1_low:.8f} < {candle_2_close:.8f} < {candle_1_high:.8f}")
        else:
            swept_correctly = candle_2_low < candle_1_low
            closed_in_range = candle_1_low < candle_2_close < candle_1_high
            
            chart_lines.append(f"  {'✅' if swept_correctly else '❌'} Low swept: {candle_2_low:.8f} < {candle_1_low:.8f}")
            chart_lines.append(f"  {'✅' if closed_in_range else '❌'} Close in range: {candle_1_low:.8f} < {candle_2_close:.8f} < {candle_1_high:.8f}")
        
        return "\n".join(chart_lines)
    
    @staticmethod
    def generate_simple_summary(crt_data: Dict) -> str:
        """Generate simple one-line summary"""
        crt_type = crt_data.get('type', 'unknown')
        c1_high = crt_data.get('candle_1_high')
        c1_low = crt_data.get('candle_1_low')
        c2_high = crt_data.get('candle_2_high')
        c2_low = crt_data.get('candle_2_low')
        c2_close = crt_data.get('candle_2_close')
        
        if crt_type == "bearish":
            sweep_amount = c2_high - c1_high
            return f"🔴 Bearish CRT: High swept by {sweep_amount:.8f}, closed at {c2_close:.8f} (in range)"
        else:
            sweep_amount = c1_low - c2_low
            return f"🟢 Bullish CRT: Low swept by {sweep_amount:.8f}, closed at {c2_close:.8f} (in range)"
