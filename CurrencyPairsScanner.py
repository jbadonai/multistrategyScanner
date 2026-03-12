#!/usr/bin/env python3
"""
Scans futures pairs supported by both Bybit and Binance,
filters for high volatility, and prints results on a single line.
"""

import requests
import statistics

# ── Config ────────────────────────────────────────────────────────────────────
VOLATILITY_THRESHOLD = 2.0   # % 24h price change (absolute) to qualify as "high"
REQUEST_TIMEOUT      = 10    # seconds


# ── Bybit ─────────────────────────────────────────────────────────────────────
def get_bybit_futures() -> dict[str, float]:
    """
    Returns {normalised_symbol: abs_price_change_pct} for all
    Bybit linear perpetual / futures contracts.
    """
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": "linear"}
    r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    data = r.json()

    pairs: dict[str, float] = {}
    for item in data.get("result", {}).get("list", []):
        symbol: str = item.get("symbol", "")
        # Keep only USDT-margined perpetuals / futures (e.g. BTCUSDT)
        if not symbol.endswith("USDT"):
            continue
        try:
            change_pct = abs(float(item.get("price24hPcnt", 0)) * 100)
        except (ValueError, TypeError):
            continue
        pairs[symbol] = change_pct

    return pairs


# ── Binance ───────────────────────────────────────────────────────────────────
def get_binance_futures() -> dict[str, float]:
    """
    Returns {normalised_symbol: abs_price_change_pct} for all
    Binance USD-M futures.
    """
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    data = r.json()

    pairs: dict[str, float] = {}
    for item in data:
        symbol: str = item.get("symbol", "")
        if not symbol.endswith("USDT"):
            continue
        try:
            change_pct = abs(float(item.get("priceChangePercent", 0)))
        except (ValueError, TypeError):
            continue
        pairs[symbol] = change_pct

    return pairs


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("Fetching Bybit futures …")
    bybit = get_bybit_futures()
    print(f"  → {len(bybit)} USDT pairs found on Bybit")

    print("Fetching Binance futures …")
    binance = get_binance_futures()
    print(f"  → {len(binance)} USDT pairs found on Binance")

    # Pairs listed on BOTH exchanges
    common = set(bybit.keys()) & set(binance.keys())
    print(f"\nPairs listed on both exchanges: {len(common)}")

    # Average volatility across both exchanges, then filter
    volatile: list[tuple[str, float]] = []
    for symbol in common:
        avg_vol = (bybit[symbol] + binance[symbol]) / 2
        if avg_vol >= VOLATILITY_THRESHOLD:
            volatile.append((symbol, avg_vol))

    # Sort by volatility descending
    volatile.sort(key=lambda x: x[1], reverse=True)

    print(f"High-volatility pairs (≥ {VOLATILITY_THRESHOLD}% 24h change): {len(volatile)}")

    if not volatile:
        print("No high-volatility pairs found — try lowering VOLATILITY_THRESHOLD.")
        return

    # ── Single-line output ────────────────────────────────────────────────────
    result = [symbol for symbol, _ in volatile]
    print("\nResult:")
    print(result)

    # Optional: detailed table
    print("\nDetailed breakdown (sorted by avg volatility):")
    print(f"{'Symbol':<15} {'Bybit %':>9} {'Binance %':>10} {'Avg %':>8}")
    print("-" * 46)
    for symbol, avg in volatile:
        print(f"{symbol:<15} {bybit[symbol]:>8.2f}%  {binance[symbol]:>8.2f}%  {avg:>7.2f}%")


if __name__ == "__main__":
    main()