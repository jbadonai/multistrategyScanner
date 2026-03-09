"""
Filter currency pairs that are:
1. Supported on Binance (spot or futures)
2. Supported on Bybit FUTURES (not spot only)
"""

import urllib.request
import json

PAIRS = [
    "ENSOUSDT","AGLDUSDT","ALLOUSDT","KITEUSDT","AWEUSDT","ORCAUSDT","BIOUSDT","SNXUSDT",
    "LAUSDT","OMUSDT","RPLUSDT","DEXEUSDT","SAPIENUSDT","DUSKUSDT","INJUSDT","FIDAUSDT",
    "BELUSDT","JTOUSDT","EULUSDT","MORPHOUSDT","OPUSDT","DOLOUSDT","PROMUSDT","KERNELUSDT",
    "COTIUSDT","COWUSDT","AXLUSDT","PORTALUSDT","DOTUSDT","APTUSDT","HOLOUSDT","METUSDT",
    "0GUSDT","IOUSDT","BERAUSDT","CHRUSDT","HUMAUSDT","CYBERUSDT","INITUSDT","CTKUSDT",
    "PUNDIXUSDT","ETHFIUSDT","ARUSDT","PARTIUSDT","BREVUSDT","AXSUSDT","EDENUSDT",
    "GIGGLEUSDT","NILUSDT","KMNOUSDT","KSMUSDT","ARPAUSDT","MITOUSDT","OGNUSDT",
    "MUBARAKUSDT","ARBUSDT","BBUSDT","EIGENUSDT","NEARUSDT","FILUSDT","ROSEUSDT",
    "CTSIUSDT","PENGUUSDT","ENAUSDT","BANKUSDT","RONINUSDT","DYDXUSDT","FLOWUSDT",
    "RENDERUSDT","ICPUSDT","CETUSUSDT","SIGNUSDT","ETCUSDT","ORDIUSDT","BIGTIMEUSDT",
    "IMXUSDT","GUNUSDT","C98USDT","DASHUSDT","ENSUSDT","ARKMUSDT","CVXUSDT","AIXBTUSDT",
    "EDUUSDT","2ZUSDT","METISUSDT","JUPUSDT","APEUSDT","MAVUSDT","ADAUSDT","LPTUSDT",
    "MIRAUSDT","BICOUSDT","GLMUSDT","CRVUSDT","LRCUSDT","HFTUSDT","ACEUSDT","SANDUSDT",
    "BANDUSDT","ONTUSDT","SKLUSDT","NTRNUSDT","GMXUSDT","MANTAUSDT","PENDLEUSDT",
    "POLUSDT","AAVEUSDT","BCHUSDT","CHZUSDT","LDOUSDT","AVNTUSDT","ONDOUSDT","CUSDT",
    "FLUXUSDT","SAGAUSDT","PHAUSDT","PNUTUSDT","HIGHUSDT","AEVOUSDT","KAITOUSDT",
    "GRTUSDT","HAEDALUSDT","DIAUSDT","NXPCUSDT","MANAUSDT","ACXUSDT","SHELLUSDT",
    "AVAUSDT","COOKIEUSDT","AVAXUSDT","MMTUSDT","KAVAUSDT","ENJUSDT","ALTUSDT",
    "PEOPLEUSDT","DOGEUSDT","HEMIUSDT","CAKEUSDT","SOLUSDT","CFXUSDT","BANANAUSDT",
    "PHBUSDT","REDUSDT","LINKUSDT","ILVUSDT","EPICUSDT","SAHARAUSDT","PLUMEUSDT",
    "HEIUSDT","ATOMUSDT","SCRUSDT","LUMIAUSDT","PYTHUSDT","AUSDT","SFPUSDT","MASKUSDT",
    "MINAUSDT","LISTAUSDT","GMTUSDT","HIVEUSDT","RAREUSDT","LSKUSDT","MOVRUSDT",
    "HOOKUSDT","PROVEUSDT","MOVEUSDT","COMPUSDT","QTUMUSDT","MEUSDT","DYMUSDT",
    "BLURUSDT","ACTUSDT","MAGICUSDT","EGLDUSDT","IDUSDT","ASTRUSDT","NEWTUSDT",
    "ICXUSDT","CELOUSDT","FORMUSDT","LTCUSDT","RDNTUSDT","OPENUSDT","NFPUSDT",
    "BABYUSDT","CGPTUSDT","ALICEUSDT","HOMEUSDT","SCRTUSDT","BATUSDT","1INCHUSDT",
    "MLNUSDT","POLYXUSDT","ALGOUSDT","ETHUSDT","FIOUSDT","BNTUSDT","BMTUSDT",
    "IOTAUSDT","GASUSDT","RUNEUSDT","HBARUSDT","MBOXUSDT","SEIUSDT","KAIAUSDT",
    "KNCUSDT","POWRUSDT","ASTERUSDT","API3USDT","ERAUSDT","LQTYUSDT","CATIUSDT",
    "NEOUSDT","HYPERUSDT","RLCUSDT","QNTUSDT","OGUSDT","MTLUSDT","OXTUSDT",
    "ALPINEUSDT","AUCTIONUSDT","JSTUSDT","ONGUSDT","FFUSDT","ASRUSDT"
]

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def get_binance_symbols():
    """Get all symbols from Binance (spot + futures)."""
    symbols = set()

    # Spot
    try:
        data = fetch_json("https://api.binance.com/api/v3/exchangeInfo")
        for s in data["symbols"]:
            symbols.add(s["symbol"])
        print(f"  Binance spot: {len(symbols)} symbols")
    except Exception as e:
        print(f"  Binance spot error: {e}")

    # USD-M Futures
    try:
        data = fetch_json("https://fapi.binance.com/fapi/v1/exchangeInfo")
        fut = set()
        for s in data["symbols"]:
            fut.add(s["symbol"])
        print(f"  Binance USD-M futures: {len(fut)} symbols")
        symbols |= fut
    except Exception as e:
        print(f"  Binance futures error: {e}")

    return symbols

def get_bybit_futures_symbols():
    """Get all LINEAR (USDT perpetual) futures symbols from Bybit."""
    symbols = set()
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&limit=1000"
        data = fetch_json(url)
        for s in data["result"]["list"]:
            symbols.add(s["symbol"])
        print(f"  Bybit linear futures: {len(symbols)} symbols")
    except Exception as e:
        print(f"  Bybit futures error: {e}")
    return symbols

def main():
    print("Fetching Binance symbols...")
    binance = get_binance_symbols()

    print("\nFetching Bybit futures symbols...")
    bybit_futures = get_bybit_futures_symbols()

    print("\nFiltering pairs...")
    result = []
    not_binance = []
    not_bybit_futures = []

    for pair in PAIRS:
        on_binance = pair in binance
        on_bybit_fut = pair in bybit_futures

        if on_binance and on_bybit_fut:
            result.append(pair)
        else:
            if not on_binance:
                not_binance.append(pair)
            if not on_bybit_fut:
                not_bybit_futures.append(pair)

    print(f"\n{'='*60}")
    print(f"RESULT: {len(result)} pairs found on BOTH Binance AND Bybit Futures")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2))

    print(f"\n--- Excluded: not on Binance ({len(not_binance)}) ---")
    print(not_binance)

    print(f"\n--- Excluded: not on Bybit Futures ({len(not_bybit_futures)}) ---")
    print(not_bybit_futures)

if __name__ == "__main__":
    main()