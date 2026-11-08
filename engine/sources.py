"""Reporter: collects headlines, live trends, autocomplete keywords and gold prices."""
import calendar
import time
from concurrent.futures import ThreadPoolExecutor
from html import unescape
import re

import feedparser
import requests

from . import config

HEADERS = {"User-Agent": config.USER_AGENT}


def _clean(text):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def _fetch_feed(source, url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        feed = feedparser.parse(resp.content)
    except requests.RequestException:
        return []
    items = []
    now = time.time()
    for e in feed.entries:
        stamp = e.get("published_parsed") or e.get("updated_parsed")
        published = calendar.timegm(stamp) if stamp else now
        age_h = (now - published) / 3600
        if age_h > config.MAX_STORY_AGE_HOURS or not e.get("link"):
            continue
        items.append({
            "source": source,
            "title": _clean(e.get("title")),
            "summary": _clean(e.get("summary"))[:500],
            "url": e.get("link"),
            "published": published,
            "age_hours": round(age_h, 1),
        })
    return items


def fetch_headlines():
    jobs = [(s, u) for s, urls in config.FEEDS.items() for u in urls]
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = pool.map(lambda job: _fetch_feed(*job), jobs)
    seen, items = set(), []
    for batch in results:
        for item in batch:
            if item["url"] not in seen and item["title"]:
                seen.add(item["url"])
                items.append(item)
    return items


def fetch_trends():
    """Live trending searches from Google Trends across key countries."""
    terms = {}
    for geo in config.TREND_GEOS:
        try:
            resp = requests.get(f"https://trends.google.com/trending/rss?geo={geo}", headers=HEADERS, timeout=20)
            feed = feedparser.parse(resp.content)
        except requests.RequestException:
            continue
        for e in feed.entries:
            term = _clean(e.get("title")).lower()
            traffic = e.get("ht_approx_traffic", "0").replace("+", "").replace(",", "")
            value = int(traffic) if traffic.isdigit() else 0
            terms[term] = terms.get(term, 0) + value
    return terms


def autocomplete(query):
    """What people actually type into Google for this topic."""
    try:
        resp = requests.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "hl": "en", "q": query},
            headers=HEADERS,
            timeout=15,
        )
        return [s for s in resp.json()[1] if s.lower() != query.lower()][:8]
    except (requests.RequestException, ValueError, IndexError):
        return []


def gold_snapshot():
    """Spot gold and silver in USD (free, no key)."""
    out = {}
    for sym in ("XAU", "XAG"):
        try:
            data = requests.get(f"https://api.gold-api.com/price/{sym}", headers=HEADERS, timeout=15).json()
            out[sym] = {"price": round(float(data["price"]), 2), "updated": data.get("updatedAt")}
        except (requests.RequestException, ValueError, KeyError):
            pass
    return out
