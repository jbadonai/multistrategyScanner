"""
Main scanner module - orchestrates the liquidity swing scanning process
"""
import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import config
from binance_client import BinanceClient
from telegram_notifier import TelegramNotifier
from swing_tracker import SwingTracker
from crt_scanner import CRTScanner
from auto_trader import AutoTrader
from models import SwingAlert, FVGAlert, CRTAlert


class LiquidityScanner:
    """Main scanner class that coordinates all components"""
    
    def __init__(self):
        self.binance = BinanceClient()
        self.telegram = TelegramNotifier()
        self.tracker = SwingTracker()
        self.crt_scanner = CRTScanner() if config.ENABLE_CRT_DETECTION else None
        self.auto_trader = AutoTrader() if config.ENABLE_CRT_DETECTION and config.ENABLE_AUTO_TRADE else None
        self.pairs = config.PAIRS
        self.timeframe = config.TIMEFRAME
        self.scan_interval = config.SCAN_INTERVAL
        self.running = False
        
        print("=" * 60)
        print("🔍 LIQUIDITY SWING SCANNER")
        print("=" * 60)
        print(f"📊 Monitoring {len(self.pairs)} pairs on {self.timeframe} timeframe")
        print(f"⚙️  Pivot Lookback: {config.PIVOT_LOOKBACK}")
        print(f"⚙️  Swing Area: {config.SWING_AREA}")
        print(f"⚙️  Filter By: {config.FILTER_BY} (threshold: {config.FILTER_VALUE})")
        
        # Show POI mode status
        if config.ENABLE_DAILY_TREND:
            print(f"\n🎯 POI MODE ENABLED:")
            print(f"   • Daily Trend Detection: {config.TREND_LOOKBACK_DAYS} days lookback")
            print(f"   • Only tracking liquidity between Daily Open & Protected Level")
            print(f"   • Protected = Prev Day LOW (uptrend) or HIGH (downtrend)")
        else:
            print(f"\n📍 STANDARD MODE: Tracking all liquidity swings")
        
        # Show FVG status
        if config.ENABLE_FVG_DETECTION:
            print(f"\n✨ FVG DETECTION ENABLED:")
            print(f"   • Monitoring for FVG formations after sweeps")
            print(f"   • Lookback window: {config.FVG_LOOKBACK_CANDLES} candles")
            print(f"   • Requirements: Gap + 2x body ratio + close in range")
        
        # Show CRT status
        if config.ENABLE_CRT_DETECTION:
            print(f"\n🎯 CRT DETECTION ENABLED:")
            print(f"   • Monitoring {config.CRT_TIMEFRAME.upper()} candles for CRT patterns")
            print(f"   • Pattern: Sweep high/low + close back in range")
            print(f"   • Body Ratio Filter: ≤ {config.CRT_MAX_BODY_RATIO}%")
            if config.CRT_REQUIRE_HTF_ALIGNMENT:
                print(f"   • HTF Alignment: REQUIRED ({config.CRT_HTF_TIMEFRAME.upper()} trend bias)")
            else:
                print(f"   • HTF Alignment: DISABLED (takes all CRT signals)")
            print(f"   • Independent scan (parallel to POI/swing detection)")
            
            # Auto-trading status
            if config.ENABLE_AUTO_TRADE and self.auto_trader:
                print(f"\n🤖 AUTO-TRADING ENABLED:")
                print(f"   • Platform: ByBit ({'Testnet' if config.BYBIT_TESTNET else 'LIVE TRADING'})")
                print(f"   • Leverage: {'Max (auto-detect)' if config.USE_MAX_LEVERAGE else f'{config.FIXED_LEVERAGE}x'}")
                print(f"   • Order Value: {config.ORDER_VALUE_MULTIPLIER}x leverage")
                print(f"   • Max Concurrent: {config.MAX_CONCURRENT_TRADES} positions")
                print(f"   • Execution: Market orders in separate thread")
                if not config.BYBIT_TESTNET:
                    print(f"   ⚠️  REAL MONEY MODE - USE WITH CAUTION!")
        
        print(f"\n⏱️  Scan Interval: {self.scan_interval}s")
        print("=" * 60)
    
    def initialize(self) -> bool:
        """
        Initialize and test all connections
        
        Returns:
            True if initialization successful, False otherwise
        """
        print("\n🔄 Initializing connections...")
        
        # Test Binance connection
        print("📡 Testing Binance API connection...", end=" ")
        if not self.binance.test_connection():
            print("❌ Failed")
            return False
        print("✅ Connected")
        
        # Test Telegram connection
        print("📱 Testing Telegram bot connection...", end=" ")
        if not self.telegram.test_connection():
            print("❌ Failed")
            return False
        print(f"✅ Telegram bot connected")
        
        # Test ByBit connection (if auto-trading enabled)
        if self.auto_trader and config.ENABLE_AUTO_TRADE:
            print("🤖 Testing ByBit API connection...", end=" ")
            if not self.auto_trader.test_connection():
                print("❌ Failed")
                print("   ⚠️  Auto-trading will be disabled")
                self.auto_trader = None
            else:
                testnet_label = "TESTNET" if config.BYBIT_TESTNET else "MAINNET"
                print(f"✅ Connected to ByBit {testnet_label}")
                if not config.BYBIT_TESTNET:
                    print("   ⚠️  WARNING: MAINNET MODE - REAL MONEY TRADING!")
        
        # Verify all pairs are valid
        print(f"\n🔍 Validating {len(self.pairs)} trading pairs...")
        invalid_pairs = []
        for pair in self.pairs:
            info = self.binance.get_exchange_info(pair)
            if info is None:
                invalid_pairs.append(pair)
                print(f"   ❌ {pair} - Invalid or not found")
            else:
                print(f"   ✅ {pair} - Valid")
        
        if invalid_pairs:
            print(f"\n⚠️  Warning: {len(invalid_pairs)} invalid pair(s) found")
            print(f"Invalid pairs will be skipped: {', '.join(invalid_pairs)}")
            self.pairs = [p for p in self.pairs if p not in invalid_pairs]
        
        if not self.pairs:
            print("\n❌ No valid pairs to monitor!")
            return False
        
        print(f"\n✅ Initialization complete! Monitoring {len(self.pairs)} pairs")
        return True
    
    def scan_pair(self, pair: str) -> tuple:
        """
        Scan a single pair for swing points and swept liquidity
        Also scans for CRT patterns on 4H if enabled
        
        Args:
            pair: Trading pair to scan
            
        Returns:
            Tuple of (pair, sweep_alerts, fvg_alerts, crt_alert, active_swings, daily_context, error)
        """
        try:
            daily_context = None
            crt_alert = None
            
            # Fetch intraday market data (used for both POI detection and swing detection)
            data = self.binance.get_klines(
                pair,
                self.timeframe,  # Uses configured timeframe (5m, 15m, etc.)
                config.KLINES_LIMIT
            )
            
            if data is None:
                return (pair, [], [], None, {}, None, "Failed to fetch intraday data")
            
            # CRT Detection (independent, runs in parallel)
            if config.ENABLE_CRT_DETECTION:
                # Fetch 4H candles for CRT detection
                # Need at least 3 to ensure we check completed candles only
                crt_candles = self.binance.get_klines(
                    pair,
                    config.CRT_TIMEFRAME,
                    10  # Fetch more candles to ensure we have completed ones
                )
                
                # Fetch HTF candles if alignment is required
                htf_candles = None
                if config.CRT_REQUIRE_HTF_ALIGNMENT:
                    htf_candles = self.binance.get_klines(
                        pair,
                        config.CRT_HTF_TIMEFRAME,
                        config.CRT_HTF_LOOKBACK
                    )
                
                if crt_candles and len(crt_candles) >= 3:
                    crt_alert = self.crt_scanner.scan_pair(pair, crt_candles, htf_candles)
            
            # Fetch daily candles if POI mode enabled
            if config.ENABLE_DAILY_TREND:
                daily_candles = self.binance.get_daily_candles(
                    pair,
                    config.TREND_LOOKBACK_DAYS + 1  # +1 for today
                )
                
                if daily_candles and len(daily_candles) > config.TREND_LOOKBACK_DAYS:
                    # Separate today's candle from historical
                    # We exclude today completely - using only completed days
                    historical_daily = daily_candles[:-1]  # Exclude today for trend analysis
                    
                    # Update daily trend context
                    # Daily open = yesterday's close (prev day close in historical_daily)
                    daily_context = self.tracker.update_daily_context(pair, historical_daily)
                    
                    # If strict POI mode and no trend detected, skip this pair
                    if config.SKIP_PAIRS_WITHOUT_TREND and daily_context is None:
                        return (pair, [], [], crt_alert, {}, None, "No clear trend detected (skipped in strict POI mode)")

            
            # Process intraday data and detect swings on configured timeframe
            # (with POI context if available from daily analysis)
            # Returns tuple: (sweep_alerts, fvg_alerts)
            sweep_alerts, fvg_alerts = self.tracker.process_market_data(pair, data, daily_context)
            
            # Combine all alerts
            all_alerts = sweep_alerts + fvg_alerts
            
            # Enhance sweep alerts with POI context
            if daily_context and sweep_alerts:
                for alert in sweep_alerts:
                    alert.poi_context = daily_context
            
            # Get active swing counts
            active_swings = self.tracker.get_active_swings(pair)
            
            return (pair, sweep_alerts, fvg_alerts, crt_alert, active_swings, daily_context, None)
            
        except Exception as e:
            return (pair, [], [], None, {}, None, str(e))
    
    def scan_all_pairs(self) -> Dict:
        """
        Scan all pairs concurrently
        
        Returns:
            Dict with scan results and statistics
        """
        results = {
            "total_sweep_alerts": 0,
            "total_fvg_alerts": 0,
            "total_crt_alerts": 0,
            "successful_scans": 0,
            "failed_scans": 0,
            "skipped_scans": 0,
            "sweep_alerts": [],
            "fvg_alerts": [],
            "crt_alerts": [],
            "active_swings": {},
            "daily_contexts": {}
        }
        
        # Use ThreadPoolExecutor for concurrent API requests
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            future_to_pair = {
                executor.submit(self.scan_pair, pair): pair 
                for pair in self.pairs
            }
            
            for future in as_completed(future_to_pair):
                pair, sweep_alerts, fvg_alerts, crt_alert, active_swings, daily_context, error = future.result()
                
                if error:
                    # Different handling for skipped pairs vs actual errors
                    if "No clear trend" in error and config.SKIP_PAIRS_WITHOUT_TREND:
                        results["skipped_scans"] += 1
                        print(f"   ⏭️  {pair}: Trend unclear (skipped)")
                    else:
                        results["failed_scans"] += 1
                        print(f"   ❌ {pair}: {error}")
                else:
                    results["successful_scans"] += 1
                    results["active_swings"][pair] = active_swings
                    if daily_context:
                        results["daily_contexts"][pair] = daily_context
                    
                    # Track sweep alerts
                    if sweep_alerts:
                        results["total_sweep_alerts"] += len(sweep_alerts)
                        results["sweep_alerts"].extend(sweep_alerts)
                    
                    # Track FVG alerts
                    if fvg_alerts:
                        results["total_fvg_alerts"] += len(fvg_alerts)
                        results["fvg_alerts"].extend(fvg_alerts)
                    
                    # Track CRT alerts
                    if crt_alert:
                        results["total_crt_alerts"] += 1
                        results["crt_alerts"].append(crt_alert)
                    
                    # Display status
                    if sweep_alerts or fvg_alerts or crt_alert:
                        alert_msg = []
                        if sweep_alerts:
                            alert_msg.append(f"{len(sweep_alerts)} sweep(s)")
                        if fvg_alerts:
                            alert_msg.append(f"{len(fvg_alerts)} FVG(s)")
                        if crt_alert:
                            alert_msg.append(f"1 CRT ({crt_alert.crt_type})")
                        print(f"   🚨 {pair}: {' + '.join(alert_msg)} detected!")
                    else:
                        # Show status based on mode
                        if config.ENABLE_DAILY_TREND and daily_context:
                            # POI mode
                            high_liq = active_swings.get("high_liquidity", 0)
                            low_liq = active_swings.get("low_liquidity", 0)
                            mitigated = active_swings.get("mitigated_total", 0)
                            trend = daily_context["trend"]
                            trend_emoji = "📈" if trend == "uptrend" else "📉"
                            print(f"   {trend_emoji} {pair} ({trend}): {high_liq}H/{low_liq}L POIs active, {mitigated} mitigated")
                        else:
                            # Standard mode
                            high_count = active_swings.get("high", 0)
                            low_count = active_swings.get("low", 0)
                            high_liq = active_swings.get("high_liquidity", 0)
                            low_liq = active_swings.get("low_liquidity", 0)
                            
                            if config.FILTER_VALUE > 0:
                                print(f"   ✅ {pair}: {high_count}H/{low_count}L swings ({high_liq}H/{low_liq}L liquidity zones)")
                            else:
                                print(f"   ✅ {pair}: {high_count}H/{low_count}L liquidity swings")
        
        return results
    
    def send_alerts(self, sweep_alerts: List, fvg_alerts: List, crt_alerts: List):
        """Send Telegram alerts for swept liquidity, FVG formations, and CRT patterns"""
        # Send sweep alerts
        for alert in sweep_alerts:
            # Pass POI manager if in POI mode
            if config.ENABLE_DAILY_TREND:
                message = alert.format_message(self.tracker.poi_manager)
            else:
                message = alert.format_message()
            
            success = self.telegram.send_message(message)
            if success:
                print(f"   📤 Sweep alert sent for {alert.pair}")
            else:
                print(f"   ❌ Failed to send sweep alert for {alert.pair}")
        
        # Send FVG alerts
        for alert in fvg_alerts:
            message = alert.format_message()
            success = self.telegram.send_message(message)
            if success:
                print(f"   📤 FVG alert sent for {alert.pair} ({alert.fvg_type})")
            else:
                print(f"   ❌ Failed to send FVG alert for {alert.pair}")
        
        # Send CRT alerts
        for alert in crt_alerts:
            message = alert.format_message()
            success = self.telegram.send_message(message)
            if success:
                print(f"   📤 CRT alert sent for {alert.pair} ({alert.crt_type} on {alert.timeframe.upper()})")
                
                # Execute auto-trade if enabled
                if self.auto_trader and config.ENABLE_AUTO_TRADE:
                    self.auto_trader.execute_trade(alert)
            else:
                print(f"   ❌ Failed to send CRT alert for {alert.pair}")
    
    def countdown(self, seconds: int):
        """Display countdown timer on single line"""
        for remaining in range(seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            timer = f"⏳ Next scan in: {mins:02d}:{secs:02d}"
            print(f"\r{timer}", end="", flush=True)
            time.sleep(1)
        print("\r" + " " * 50 + "\r", end="", flush=True)  # Clear line
    
    def run(self):
        """Main run loop"""
        if not self.initialize():
            print("\n❌ Initialization failed. Exiting.")
            return
        
        print("\n" + "=" * 60)
        print("🚀 Scanner started! Press Ctrl+C to stop")
        print("=" * 60 + "\n")
        
        self.running = True
        scan_count = 0
        
        try:
            while self.running:
                scan_count += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"\n{'='*60}")
                print(f"📊 Scan #{scan_count} - {timestamp}")
                print(f"{'='*60}")
                
                # Scan all pairs
                results = self.scan_all_pairs()
                
                # Send alerts if any
                total_alerts = results["total_sweep_alerts"] + results["total_fvg_alerts"] + results["total_crt_alerts"]
                if total_alerts > 0:
                    print(f"\n🔔 Sending {results['total_sweep_alerts']} sweep + {results['total_fvg_alerts']} FVG + {results['total_crt_alerts']} CRT alert(s)...")
                    self.send_alerts(results["sweep_alerts"], results["fvg_alerts"], results["crt_alerts"])
                
                # Print summary
                print(f"\n📈 Scan Summary:")
                print(f"   ✅ Successful: {results['successful_scans']}/{len(self.pairs)}")
                
                if config.ENABLE_DAILY_TREND and config.SKIP_PAIRS_WITHOUT_TREND and results['skipped_scans'] > 0:
                    print(f"   ⏭️  Skipped (no trend): {results['skipped_scans']}/{len(self.pairs)}")
                
                if results['failed_scans'] > 0:
                    print(f"   ❌ Failed: {results['failed_scans']}/{len(self.pairs)}")
                
                print(f"   🚨 Alerts: {results['total_sweep_alerts']} sweeps, {results['total_fvg_alerts']} FVGs, {results['total_crt_alerts']} CRTs")
                
                if config.ENABLE_DAILY_TREND:
                    # POI mode summary
                    total_active_pois = sum(
                        s.get("high_liquidity", 0) + s.get("low_liquidity", 0) 
                        for s in results["active_swings"].values()
                    )
                    total_mitigated = sum(
                        s.get("mitigated_total", 0) 
                        for s in results["active_swings"].values()
                    )
                    pairs_with_trend = len(results.get("daily_contexts", {}))
                    
                    print(f"   🎯 Pairs with Trend: {pairs_with_trend}/{len(self.pairs)}")
                    print(f"   💧 Active POIs: {total_active_pois}")
                    print(f"   ❌ Mitigated Today: {total_mitigated}")
                else:
                    # Standard mode summary
                    total_highs = sum(s.get("high", 0) for s in results["active_swings"].values())
                    total_lows = sum(s.get("low", 0) for s in results["active_swings"].values())
                    total_high_liq = sum(s.get("high_liquidity", 0) for s in results["active_swings"].values())
                    total_low_liq = sum(s.get("low_liquidity", 0) for s in results["active_swings"].values())
                    
                    if config.FILTER_VALUE > 0:
                        print(f"   📍 Total Swings: {total_highs}H/{total_lows}L")
                        print(f"   💧 Liquidity Zones: {total_high_liq}H/{total_low_liq}L (qualified with {config.FILTER_BY} > {config.FILTER_VALUE})")
                    else:
                        print(f"   💧 Liquidity Swings: {total_highs}H/{total_lows}L")
                
                # Countdown to next scan
                if self.running:
                    self.countdown(self.scan_interval)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Scanner stopped by user")
            self.running = False
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
            self.running = False
        
        print("\n" + "=" * 60)
        print("👋 Scanner terminated")
        print("=" * 60)


def main():
    """Entry point"""
    scanner = LiquidityScanner()
    scanner.run()


if __name__ == "__main__":
    main()
