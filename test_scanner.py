"""
Test script to verify scanner components work correctly
"""
import sys
from datetime import datetime
from models import SwingPoint, MarketData, SwingAlert
from pivot_detector import PivotDetector
from binance_client import BinanceClient
from telegram_notifier import TelegramNotifier


def test_models():
    """Test data models"""
    print("Testing Models...")
    
    # Test MarketData
    kline = [1640000000000, "50000", "51000", "49000", "50500", "100.5"]
    data = MarketData.from_binance(kline)
    assert data.open == 50000.0
    assert data.high == 51000.0
    print("  ✅ MarketData works")
    
    # Test SwingPoint
    swing = SwingPoint(
        pair="BTCUSDT",
        swing_type="high",
        price_top=51000.0,
        price_btm=50000.0,
        bar_index=10,
        timestamp=datetime.now()
    )
    assert swing.is_swept(51001.0) == True
    assert swing.is_swept(50999.0) == False
    assert swing.is_in_zone(50500.0, 49500.0) == True
    print("  ✅ SwingPoint works")
    
    # Test SwingAlert
    alert = SwingAlert(
        pair="BTCUSDT",
        swing_type="high",
        swing_price_top=51000.0,
        swing_price_btm=50000.0,
        sweep_price=51100.0,
        swing_timestamp=datetime.now(),
        sweep_timestamp=datetime.now(),
        count=5,
        volume=1000.0
    )
    message = alert.format_message()
    assert "BTCUSDT" in message
    assert "Swing High" in message
    print("  ✅ SwingAlert works")


def test_pivot_detector():
    """Test pivot detection logic"""
    print("\nTesting Pivot Detector...")
    
    detector = PivotDetector(lookback=2)
    
    # Create test data with a clear pivot high at index 2
    test_data = [
        MarketData(1, 100, 105, 95, 100, 10),   # 0
        MarketData(2, 100, 110, 98, 108, 10),   # 1
        MarketData(3, 108, 120, 105, 115, 10),  # 2 - PIVOT HIGH
        MarketData(4, 115, 118, 110, 112, 10),  # 3
        MarketData(5, 112, 115, 108, 110, 10),  # 4
    ]
    
    # Should detect pivot high at index 2
    pivot_high = detector.detect_pivot_high(test_data, 2)
    assert pivot_high == 120.0, f"Expected 120.0, got {pivot_high}"
    print("  ✅ Pivot high detection works")
    
    # Create test data with a clear pivot low at index 2
    test_data = [
        MarketData(1, 100, 105, 95, 100, 10),   # 0
        MarketData(2, 100, 102, 92, 95, 10),    # 1
        MarketData(3, 95, 100, 85, 90, 10),     # 2 - PIVOT LOW
        MarketData(4, 90, 95, 88, 92, 10),      # 3
        MarketData(5, 92, 98, 90, 95, 10),      # 4
    ]
    
    # Should detect pivot low at index 2
    pivot_low = detector.detect_pivot_low(test_data, 2)
    assert pivot_low == 85.0, f"Expected 85.0, got {pivot_low}"
    print("  ✅ Pivot low detection works")
    
    # Test swing zone calculation
    candle = MarketData(1, 100, 110, 95, 105, 10)
    zone = detector.get_swing_zone([candle], 0, "high", "Wick Extremity")
    assert zone == (110.0, 105.0), f"Expected (110.0, 105.0), got {zone}"
    print("  ✅ Swing zone calculation works")


def test_binance_client():
    """Test Binance API client"""
    print("\nTesting Binance Client...")
    
    client = BinanceClient()
    
    # Test connection
    if client.test_connection():
        print("  ✅ Binance API connection works")
    else:
        print("  ⚠️  Binance API connection failed (might be network issue)")
        return
    
    # Test fetching klines
    data = client.get_klines("BTCUSDT", "5m", 10)
    if data and len(data) == 10:
        print("  ✅ Klines fetch works")
        print(f"     Last close: {data[-1].close}")
    else:
        print("  ⚠️  Klines fetch failed")


def test_telegram():
    """Test Telegram notifier"""
    print("\nTesting Telegram Notifier...")
    
    notifier = TelegramNotifier()
    
    # Test connection
    if notifier.test_connection():
        print("  ✅ Telegram connection works")
        
        # Send test message
        test_message = "🧪 *Liquidity Scanner Test*\n\nThis is a test message from the scanner."
        if notifier.send_message(test_message):
            print("  ✅ Test message sent successfully")
        else:
            print("  ⚠️  Failed to send test message")
    else:
        print("  ⚠️  Telegram connection failed")


def test_liquidity_qualification():
    """Test that swings only qualify as liquidity zones after meeting filter criteria"""
    print("\nTesting Liquidity Qualification Logic...")
    
    from swing_tracker import SwingTracker
    import config
    
    # Temporarily set filter
    original_filter = config.FILTER_VALUE
    original_filter_by = config.FILTER_BY
    config.FILTER_VALUE = 1  # Need count > 1 (so 2+ touches) to qualify
    config.FILTER_BY = "Count"
    
    tracker = SwingTracker()
    pair = "TEST_PAIR"
    tracker.initialize_pair(pair)
    
    # Test 1: No touches yet - should NOT sweep
    print("  Test 1: Swing with 0 touches...")
    swing1 = SwingPoint(
        pair=pair,
        swing_type="high",
        price_top=100.0,
        price_btm=98.0,
        bar_index=14,
        timestamp=datetime.now(),
        count=0,  # No revisits yet
        volume=0.0,
        crossed=False
    )
    tracker.swing_points[pair] = {swing1}
    test_candle_sweep = MarketData(4, 99, 101, 98, 100.5, 300)  # Sweeps the high
    swept = tracker._check_swept_liquidity(pair, test_candle_sweep)
    assert len(swept) == 0, f"Should not sweep - no liquidity built up yet (got {len(swept)} sweeps)"
    print("  ✅ Swing with 0 touches does NOT qualify (correctly filtered)")
    
    # Test 2: One touch - should NOT sweep (filter = 1, need count > 1)
    print("  Test 2: Swing with 1 touch...")
    swing2 = SwingPoint(
        pair=pair,
        swing_type="high",
        price_top=100.0,
        price_btm=98.0,
        bar_index=15,  # Different index to create new swing
        timestamp=datetime.now(),
        count=1,
        volume=150.0,
        crossed=False
    )
    tracker.swing_points[pair] = {swing2}
    swept = tracker._check_swept_liquidity(pair, test_candle_sweep)
    assert len(swept) == 0, f"Should not sweep - count=1 not > 1 (got {len(swept)} sweeps)"
    print("  ✅ Swing with 1 touch does NOT qualify (correctly filtered)")
    
    # Test 3: Two touches - SHOULD sweep (count=2 > 1, meets filter)
    print("  Test 3: Swing with 2 touches...")
    swing3 = SwingPoint(
        pair=pair,
        swing_type="high",
        price_top=100.0,
        price_btm=98.0,
        bar_index=16,  # Different index to create new swing
        timestamp=datetime.now(),
        count=2,
        volume=350.0,
        crossed=False
    )
    tracker.swing_points[pair] = {swing3}
    swept = tracker._check_swept_liquidity(pair, test_candle_sweep)
    assert len(swept) == 1, f"Should sweep - count=2 > 1, meets filter (got {len(swept)} sweeps)"
    assert swept[0].count == 2, "Swept swing should have count of 2"
    print("  ✅ Swing with 2 touches QUALIFIES as liquidity zone (correctly alerted)")
    
    # Test 4: Price in zone doesn't sweep
    print("  Test 4: Price in zone but doesn't sweep...")
    swing4 = SwingPoint(
        pair=pair,
        swing_type="high",
        price_top=100.0,
        price_btm=98.0,
        bar_index=17,  # Different index to create new swing
        timestamp=datetime.now(),
        count=3,
        volume=500.0,
        crossed=False
    )
    tracker.swing_points[pair] = {swing4}
    test_candle_in_zone = MarketData(5, 98, 99.5, 97, 99, 200)  # In zone but doesn't sweep
    swept = tracker._check_swept_liquidity(pair, test_candle_in_zone)
    assert len(swept) == 0, f"Should not sweep - price didn't cross the high (got {len(swept)} sweeps)"
    print("  ✅ Price in zone doesn't trigger sweep (correct)")
    
    # Test 5: Volume-based filter
    print("  Test 5: Volume-based filter...")
    config.FILTER_BY = "Volume"
    config.FILTER_VALUE = 400.0
    swing5 = SwingPoint(
        pair=pair,
        swing_type="high",
        price_top=100.0,
        price_btm=98.0,
        bar_index=18,
        timestamp=datetime.now(),
        count=5,
        volume=500.0,  # Above volume threshold
        crossed=False
    )
    tracker.swing_points[pair] = {swing5}
    swept = tracker._check_swept_liquidity(pair, test_candle_sweep)
    assert len(swept) == 1, f"Should sweep - volume meets threshold (got {len(swept)} sweeps)"
    print("  ✅ Volume-based filter works correctly")
    
    # Restore original filter
    config.FILTER_VALUE = original_filter
    config.FILTER_BY = original_filter_by
    print("  ✅ Liquidity qualification logic works correctly!")



def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 LIQUIDITY SCANNER COMPONENT TESTS")
    print("=" * 60)
    
    try:
        test_models()
        test_pivot_detector()
        test_liquidity_qualification()
        test_binance_client()
        test_telegram()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        print("\n💡 Key Test Results:")
        print("   • Pivot detection matches Pine Script logic")
        print("   • Liquidity filtering works correctly")
        print("   • Only swings meeting filter criteria trigger alerts")
        print("   • This prevents false signals from weak swing points")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
