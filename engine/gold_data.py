"""Gold desk data: live spot prices and exchange rates, cross-checked against independent sources.

    python -m engine.gold_data      -> writes data/gold.json and prints the checks
"""
import datetime as dt
import json
import time

import requests

from . import config
from .gold_countries import COUNTRIES

HEADERS = {"User-Agent": "Mozilla/5.0 " + config.USER_AGENT}
GOLD_FILE = config.DATA_DIR / "gold.json"

MAX_METAL_GAP = 0.02   # spot vs. second source (futures trade at a small premium)
MAX_FX_GAP = 0.015


def _get(url, **kw):
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, **kw)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def spot(symbol):
    return float(_get(f"https://api.gold-api.com/price/{symbol}")["price"])


def futures(ticker):
    """COMEX futures from Yahoo Finance: an independent sanity check for the spot price."""
    data = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}", params={"range": "1d", "interval": "1h"})
    return float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])


def fx_primary():
    data = _get("https://open.er-api.com/v6/latest/USD")
    return data["rates"]


def fx_secondary():
    data = _get("https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.min.json")
    return {k.upper(): v for k, v in data["usd"].items()}


def _gap(a, b):
    return abs(a - b) / b


def fetch():
    """Returns verified prices, or raises if the data cannot be trusted."""
    checks, warnings = {}, []
    prices = {"XAU": spot("XAU"), "XAG": spot("XAG")}
    for sym, ticker in (("XAU", "GC=F"), ("XAG", "SI=F")):
        try:
            ref = futures(ticker)
            gap = _gap(prices[sym], ref)
            checks[sym] = {"spot": prices[sym], "futures": ref, "gap": round(gap, 4)}
            if gap > MAX_METAL_GAP:
                raise ValueError(f"{sym} spot {prices[sym]} disagrees with futures {ref} by {gap:.1%}")
        except requests.RequestException as e:
            warnings.append(f"{sym} cross-check unavailable: {e}")

    rates = fx_primary()
    try:
        second = fx_secondary()
    except requests.RequestException as e:
        second = {}
        warnings.append(f"FX cross-check unavailable: {e}")
    needed = sorted({c["currency"] for c in COUNTRIES})
    fx = {}
    for cur in needed:
        if cur not in rates:
            raise ValueError(f"No exchange rate for {cur}")
        fx[cur] = rates[cur]
        if cur in second and cur != "USD":
            gap = _gap(rates[cur], second[cur])
            if gap > MAX_FX_GAP:
                warnings.append(f"{cur}: sources differ by {gap:.1%} ({rates[cur]} vs {second[cur]})")
    return {
        "updated": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "xau_usd": round(prices["XAU"], 2),
        "xag_usd": round(prices["XAG"], 3),
        "fx": fx,
        "checks": checks,
        "warnings": warnings,
    }


def update():
    try:
        data = fetch()
    except (requests.RequestException, ValueError, KeyError) as e:
        # A source is down or disagrees: keep serving the last verified prices if they are recent
        if GOLD_FILE.exists():
            last = json.loads(GOLD_FILE.read_text(encoding="utf-8"))
            age = dt.datetime.utcnow() - dt.datetime.fromisoformat(last["updated"].rstrip("Z"))
            if age < dt.timedelta(hours=6):
                last.setdefault("warnings", []).append(f"Live update failed, kept last verified prices: {e}")
                return last
        raise
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


if __name__ == "__main__":
    d = update()
    print(f"Gold ${d['xau_usd']:,} | Silver ${d['xag_usd']} | {len(d['fx'])} currencies | {d['updated']}")
    for sym, c in d["checks"].items():
        print(f"  {sym}: spot {c['spot']:,} vs COMEX futures {c['futures']:,} -> gap {c['gap']:.2%}")
    for w in d["warnings"]:
        print("  warning:", w)
