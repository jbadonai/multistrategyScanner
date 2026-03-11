"""
Scanner Engine - Multi-Strategy Orchestrator
Coordinates all trading strategies and manages scanning workflow
"""

from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging

# Import strategies
from strategies.crt_strategy import CRTStrategy
from strategies.poi_fvg_strategy import POIFVGStrategy
from strategies.sr_channel_strategy import SRChannelStrategy
from strategies.base_strategy import StrategySignal

# Import core components
from binance_client import BinanceClient
from core.signal_router import SignalRouter
from core.trade_executor import TradeExecutor


class ScannerEngine:
    """
    Main scanner engine that orchestrates all strategies
    """
    
    def __init__(self, config):
        self.config = config
        self.binance = BinanceClient()
        
        # Setup logging
        self.debug_mode = config.LOG_LEVEL == "DEBUG"
        self._setup_logging()
        
        # Initialize strategies
        self.strategies = self._initialize_strategies()
        
        # Initialize core components
        self.signal_router = SignalRouter(config)
        self.trade_executor = TradeExecutor(config)
        
        # Initialize position monitor for profit targets
        if hasattr(config, 'ENABLE_PROFIT_TARGET') and config.ENABLE_PROFIT_TARGET:
            from position_monitor import PositionMonitor
            self.position_monitor = PositionMonitor(config)
        else:
            self.position_monitor = None
        
        # Settings
        self.pairs = config.PAIRS
        self.scan_interval = config.SCAN_INTERVAL
        self.max_workers = config.MAX_WORKERS
        self.running = False
        
        print(f"\n{'='*60}")
        print(f"🎯 MULTI-STRATEGY SCANNER ENGINE")
        print(f"{'='*60}")
        self._display_strategy_status()
    
    def _setup_logging(self):
        """Setup logging based on config"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        
        log_level = level_map.get(self.config.LOG_LEVEL, logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(message)s'
        )
        
        # Disable noisy HTTP logs from urllib3 and requests
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
        
        if self.debug_mode:
            print(f"🔍 Debug mode: ENABLED")
        else:
            print(f"ℹ️  Log level: {self.config.LOG_LEVEL}")
    
    def _initialize_strategies(self) -> List:
        """Initialize all enabled strategies"""
        strategies = []
        
        # POI/FVG Strategy
        if self.config.ENABLE_POI_STRATEGY:
            strategies.append(POIFVGStrategy(self.config))
        
        # CRT Strategy
        if self.config.ENABLE_CRT_STRATEGY:
            strategies.append(CRTStrategy(self.config))
        
        # SR Channel Strategy
        if self.config.ENABLE_SR_STRATEGY:
            strategies.append(SRChannelStrategy(self.config))
        
        return strategies
    
    def _display_strategy_status(self):
        """Display enabled strategies and their status"""
        print(f"\n📊 Active Strategies:")
        
        for strategy in self.strategies:
            auto_trade_status = "🤖 AUTO-TRADE ON" if strategy.auto_trade_enabled else "📢 ALERTS ONLY"
            print(f"   ✅ {strategy.name:15} {auto_trade_status}")
        
        if not self.strategies:
            print(f"   ⚠️  No strategies enabled!")
        
        print(f"\n📈 Monitoring {len(self.pairs)} pairs")
        print(f"⏱️  Scan interval: {self.scan_interval}s")
        print(f"{'='*60}\n")
    
    def start(self):
        """Start the scanning engine"""
        print("🔄 Initializing connections...")
        
        # Test Binance connection
        print("📡 Testing Binance API connection...", end=" ")
        if not self.binance.test_connection():
            print("❌ Failed")
            return False
        print("✅ Connected")
        
        # Test Telegram connection
        print("📱 Testing Telegram connection...", end=" ")
        if not self.signal_router.test_telegram():
            print("❌ Failed")
            return False
        print("✅ Connected")
        
        # Test ByBit connection (if needed)
        if self.trade_executor.enabled:
            print("🤖 Testing ByBit API connection...", end=" ")
            if not self.trade_executor.test_connection():
                print("❌ Failed - Auto-trading disabled")
                self.trade_executor.enabled = False
            else:
                testnet_label = "TESTNET" if self.config.BYBIT_TESTNET else "LIVE"
                print(f"✅ Connected ({testnet_label})")
                if not self.config.BYBIT_TESTNET:
                    print("   ⚠️  WARNING: REAL MONEY TRADING ENABLED!")
        
        print(f"\n✅ Initialization complete!\n")
        
        # Start position monitor if enabled
        if self.position_monitor:
            self.position_monitor.start()
        
        self.running = True
        self._run_scan_loop()
    
    def _run_scan_loop(self):
        """Main scanning loop"""
        scan_count = 0
        
        while self.running:
            scan_count += 1
            print(f"\n{'='*60}")
            print(f"📊 Scan #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            try:
                # Scan all pairs concurrently
                results = self._scan_all_pairs()
                
                # Process results
                self._process_scan_results(results)
                
            except KeyboardInterrupt:
                print("\n\n⏸️  Scan interrupted by user")
                self.stop()
                break
            except Exception as e:
                print(f"\n❌ Scan error: {e}")
                import traceback
                traceback.print_exc()
            
            # Wait for next scan with countdown
            if self.running:
                import time
                print()  # Blank line before countdown
                try:
                    # Countdown timer with progress
                    for remaining in range(self.scan_interval, 0, -1):
                        mins = remaining // 60
                        secs = remaining % 60
                        
                        if mins > 0:
                            timer_str = f"{mins:02d}:{secs:02d}"
                        else:
                            timer_str = f"00:{secs:02d}"
                        
                        # Calculate progress bar
                        progress = int((self.scan_interval - remaining) / self.scan_interval * 20)
                        bar = "█" * progress + "░" * (20 - progress)
                        
                        print(f"\r⏳ Next scan: [{bar}] {timer_str}", end="", flush=True)
                        time.sleep(1)
                    
                    print()  # New line after countdown
                    
                except KeyboardInterrupt:
                    print("\n\n⏸️  Interrupted")
                    self.stop()
                    break
    
    def _scan_all_pairs(self) -> Dict:
        """Scan all pairs concurrently"""
        results = {
            "signals_by_strategy": {s.name: [] for s in self.strategies},
            "total_signals": 0,
            "successful_scans": 0,
            "failed_scans": 0,
            "errors": [],
            "debug_output": []  # Collect debug output
        }
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._scan_pair, pair): pair for pair in self.pairs}
            
            for future in as_completed(futures):
                pair = futures[future]
                try:
                    pair_signals, debug_lines = future.result()
                    results["successful_scans"] += 1
                    
                    # Store debug output for later
                    if debug_lines:
                        results["debug_output"].extend(debug_lines)
                    
                    # Group signals by strategy
                    for signal in pair_signals:
                        results["signals_by_strategy"][signal.strategy_name].append(signal)
                        results["total_signals"] += 1
                    
                    if pair_signals and not self.debug_mode:
                        print(f"   🚨 {pair}: {len(pair_signals)} signal(s) detected!")
                    
                except Exception as e:
                    results["failed_scans"] += 1
                    results["errors"].append(f"{pair}: {str(e)}")
                    print(f"   ❌ {pair}: Scan failed")
        
        return results
    
    def _scan_pair(self, pair: str) -> tuple:
        """Scan a single pair with all strategies
        
        Returns:
            Tuple of (signals, debug_lines)
        """
        all_signals = []
        debug_info = []
        
        # Debug header
        if self.debug_mode:
            debug_info.append(f"   🔍 {pair} Scan Details:")
        
        # Fetch required data for all strategies
        data = self._fetch_required_data(pair)
        
        # Run each enabled strategy
        for strategy in self.strategies:
            try:
                signals = strategy.scan_pair(pair, **data)
                
                # Debug output per strategy
                if self.debug_mode:
                    if strategy.name == "CRT":
                        debug_info.extend(self._debug_crt(pair, signals, data))
                    elif strategy.name == "POI_FVG":
                        debug_info.extend(self._debug_poi_fvg(pair, signals, data))
                    elif strategy.name == "SR_CHANNEL":
                        debug_info.extend(self._debug_sr_channel(pair, signals, data))
                
                # Validate signals
                valid_signals = [s for s in signals if strategy.validate_signal(s)]
                all_signals.extend(valid_signals)
                
            except Exception as e:
                if self.debug_mode:
                    debug_info.append(f"      ❌ {strategy.name}: {e}")
                else:
                    # Store error for later display
                    debug_info.append(f"   ⚠️  {pair} ({strategy.name}): {e}")
                continue
        
        return (all_signals, debug_info)
    
    def _fetch_required_data(self, pair: str) -> Dict:
        """Fetch all required data for strategies"""
        data = {}
        
        # Determine all required timeframes
        required_timeframes = set()
        for strategy in self.strategies:
            req = strategy.get_required_data()
            required_timeframes.update(req.get("timeframes", []))
        
        # Fetch each timeframe
        for tf in required_timeframes:
            candles = self.binance.get_klines(pair, tf, self.config.KLINES_LIMIT)
            
            # Map to common names
            if tf == "4h":
                data["candles"] = candles
            elif tf == "1d":
                data["daily_candles"] = candles
                data["htf_candles"] = candles
            elif tf == "15m":
                if "candles" not in data:
                    data["candles"] = candles
            else:
                data[f"{tf}_candles"] = candles
        
        return data
    
    def _process_scan_results(self, results: Dict):
        """Process scan results and route signals"""
        
        # Print debug output first (if any)
        if self.debug_mode and results.get("debug_output"):
            for line in results["debug_output"]:
                print(line)
            print()  # Blank line after debug output
        
        # Display summary
        print(f"📈 Scan Summary:")
        print(f"   ✅ Successful: {results['successful_scans']}/{len(self.pairs)}")
        if results['failed_scans'] > 0:
            print(f"   ❌ Failed: {results['failed_scans']}")
        
        # Display signals by strategy
        for strategy_name, signals in results["signals_by_strategy"].items():
            if signals:
                print(f"   🎯 {strategy_name}: {len(signals)} signal(s)")
        
        print(f"   📊 Total Signals: {results['total_signals']}")
        
        # If no signals, return
        if results["total_signals"] == 0:
            return
        
        # Collect all signals
        all_signals = []
        for signals in results["signals_by_strategy"].values():
            all_signals.extend(signals)
        
        # Route signals
        print(f"\n🔔 Routing {len(all_signals)} signal(s)...")
        self.signal_router.route_signals(all_signals)
        
        # Execute auto-trades
        auto_trade_signals = [s for s in all_signals if s.auto_trade_enabled]
        if auto_trade_signals:
            print(f"\n🤖 Executing {len(auto_trade_signals)} auto-trade(s)...")
            self.trade_executor.execute_signals(auto_trade_signals)
    
    def _debug_crt(self, pair: str, signals: List[StrategySignal], data: Dict) -> List[str]:
        """Generate debug output for CRT strategy"""
        output = []
        
        candles = data.get("candles", [])
        if not candles or len(candles) < 3:
            output.append(f"      🔴 {pair} CRT: Insufficient candles")
            return output
        
        # Check if signal was generated
        if signals:
            signal = signals[0]
            output.append(f"      🟢 {pair} CRT ({signal.signal_type.lower()}): SIGNAL DETECTED")
            htf_trend = signal.details.get("HTF Trend", "unknown")
            output.append(f"         HTF Alignment: {htf_trend}")
        else:
            # No signal - explain why
            from crt_detector import CRTDetector
            from htf_trend_analyzer import HTFTrendAnalyzer
            
            detector = CRTDetector()
            crt = detector.detect_crt(candles)
            
            if crt is None:
                output.append(f"      ⚪ {pair}: No CRT pattern detected")
            else:
                # Pattern exists but was filtered
                if self.config.CRT_REQUIRE_HTF_ALIGNMENT:
                    htf_candles = data.get("htf_candles", [])
                    if htf_candles:
                        analyzer = HTFTrendAnalyzer()
                        htf_bias = analyzer.get_trend_bias(htf_candles)
                        aligned = analyzer.is_crt_aligned(crt["type"], htf_bias)
                        
                        if not aligned:
                            output.append(f"      🚫 {pair} CRT ({crt['type']}): NOT aligned with HTF ({htf_bias})")
                        else:
                            output.append(f"      ⚠️  {pair} CRT ({crt['type']}): Signal filtered (check staleness)")
                else:
                    output.append(f"      ⚠️  {pair} CRT ({crt['type']}): Pattern found but filtered")
        
        return output
    
    def _debug_poi_fvg(self, pair: str, signals: List[StrategySignal], data: Dict) -> List[str]:
        """Generate debug output for POI/FVG strategy"""
        output = []
        
        candles = data.get("candles", [])
        daily_candles = data.get("daily_candles", [])
        
        if not candles:
            output.append(f"      🔴 {pair} POI/FVG: No candles")
            return output
        
        # Get trend info
        if self.config.POI_ENABLE_DAILY_TREND and daily_candles:
            from swing_tracker import SwingTracker
            tracker = SwingTracker()
            historical = daily_candles[:-1]
            context = tracker.update_daily_context(pair, historical)
            
            if context:
                trend = context.get("trend", "unknown")
                protected = context.get("protected", 0)
                daily_open = context.get("daily_open", 0)
                poi_count = len(context.get("poi_levels", []))
                
                if signals:
                    output.append(f"      🟢 {pair} POI/FVG: {len(signals)} signal(s)")
                else:
                    output.append(f"      ⚪ {pair} ({trend}): {poi_count} POIs active, 0 mitigated")
            else:
                output.append(f"      ⚫ {pair}: Trend unclear (skipped)")
        else:
            # No trend mode
            if signals:
                output.append(f"      🟢 {pair} POI/FVG: {len(signals)} signal(s)")
            else:
                output.append(f"      ⚪ {pair}: 0 swings/FVGs detected")
        
        return output
    
    def _debug_sr_channel(self, pair: str, signals: List[StrategySignal], data: Dict) -> List[str]:
        """Generate debug output for SR Channel strategy"""
        output = []
        
        candles = data.get("candles", [])
        
        if not candles or len(candles) < 50:
            output.append(f"      🔴 {pair} SR Channel: Insufficient candles")
            return output
        
        if signals:
            for signal in signals:
                signal_type = signal.details.get("Signal Type", "unknown")
                output.append(f"      🟢 {pair} SR Channel: {signal_type}")
        else:
            output.append(f"      ⚪ {pair} SR Channel: No valid channel/signals")
        
        return output
    
    def stop(self):
        """Stop the scanner"""
        print("\n🛑 Stopping scanner...")
        self.running = False
        
        # Stop position monitor if running
        if self.position_monitor:
            self.position_monitor.stop()
        
        print("✅ Scanner stopped")
