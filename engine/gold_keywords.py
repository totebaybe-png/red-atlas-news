"""Keyword research for the gold pages.

Combines the Google Keyword Planner export (data/gold_keywords.json) with live Google
Autocomplete suggestions for every country. Cached in data/gold_keywords_by_page.json.

    python -m engine.gold_keywords
"""
import json
import re
import time

from . import config, sources
from .gold_countries import COUNTRIES

PLANNER_FILE = config.DATA_DIR / "gold_keywords.json"
CACHE_FILE = config.DATA_DIR / "gold_keywords_by_page.json"

# Other companies' names and shopping terms: not what our price pages answer
EXCLUDE = re.compile(
    r"apmex|kitco|mcx|dpgold|jm bullion|costco|earring|ring|chain|bangle|bracelet|necklace|pendant|"
    r"rose gold|white gold|jewel|tanishq|malabar|joyalukkas|kalyan|stock|etf|share|mutual|bond|loan|"
    r"lyrics|movie|song|game|wallpaper|png|logo|color|colour|paint|nail|hair|teeth|grillz|watch",
    re.I,
)


def planner_keywords(pattern=None, limit=80):
    rows = json.loads(PLANNER_FILE.read_text(encoding="utf-8")) if PLANNER_FILE.exists() else []
    out = [r["k"] for r in rows if not EXCLUDE.search(r["k"]) and (not pattern or re.search(pattern, r["k"]))]
    return out[:limit]


def country_keywords(c):
    name = c["short"].lower()
    seeds = [f"gold price in {name}", f"gold rate in {name}", f"{name} gold rate", f"gold price today {name}",
             f"22k gold price {name}", f"24k gold rate {name}", f"gold price per gram {name}"]
    if "tola" in c["units"]:
        seeds.append(f"gold rate per tola {name}")
    if "10g" in c["units"]:
        seeds.append(f"gold rate 10 gram {name}")
    found = []
    for seed in seeds:
        for s in [seed] + sources.autocomplete(seed):
            s = s.lower().strip()
            if s not in found and not EXCLUDE.search(s):
                found.append(s)
        time.sleep(0.3)
    found += [k for k in planner_keywords(re.escape(name)) if k not in found]
    return found[:45]


def build(force=False):
    cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() and not force else {}
    if "hub" not in cache:
        cache["hub"] = planner_keywords(r"gold", 70)
    if "silver" not in cache:
        cache["silver"] = planner_keywords(r"silver|chandi", 50)
    for c in COUNTRIES:
        if c["code"] not in cache:
            cache[c["code"]] = country_keywords(c)
            print(f"  {c['short']}: {len(cache[c['code']])} keywords", flush=True)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    return cache


if __name__ == "__main__":
    kw = build()
    for key in ("hub", "silver", "IN", "AE", "PK"):
        print(f"\n{key}: {kw[key][:15]}")
