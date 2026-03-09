#!/usr/bin/env python3
"""
Multi-Strategy Trading Scanner
Main entry point for the scanning system

Supports multiple strategies:
- POI/FVG: Points of Interest with Fair Value Gaps
- CRT: Change of Retail Tendency (ICT)
- SR Channel: Support/Resistance with Liquidity Traps

Each strategy can be enabled/disabled independently
Each strategy has independent auto-trading control
"""
import sys

from core.scanner_engine import ScannerEngine
import config_new as config


def main():
    """Main entry point"""
    try:
        # Create and start scanner engine
        engine = ScannerEngine(config)
        engine.start()
        
    except KeyboardInterrupt:
        print("\n\n👋 Scanner stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
