"""Researcher: reads the full text of each source article."""
from concurrent.futures import ThreadPoolExecutor

import requests
import trafilatura

from . import config


def _read(item):
    try:
        resp = requests.get(item["url"], headers={"User-Agent": "Mozilla/5.0 " + config.USER_AGENT}, timeout=20)
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=False) or ""
    except requests.RequestException:
        text = ""
    if len(text) < 400:  # paywall or blocked: fall back to the feed summary
        text = item["summary"]
    return {**item, "text": text[: config.MAX_SOURCE_CHARS]}


def gather(story, max_sources=4, max_tries=8):
    """Full text from up to max_sources different outlets. Tries up to max_tries outlets, because
    some block readers or sit behind paywalls, and keeps the ones with the most reporting."""
    picked, outlets = [], set()
    for item in story["items"]:
        if item["source"] not in outlets:
            outlets.add(item["source"])
            picked.append(item)
        if len(picked) == max_tries:
            break
    with ThreadPoolExecutor(max_workers=8) as pool:
        docs = [d for d in pool.map(_read, picked) if len(d["text"]) >= 150]
    docs.sort(key=lambda d: len(d["text"]), reverse=True)
    return docs[:max_sources]
