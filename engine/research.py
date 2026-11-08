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


def gather(story, max_sources=4):
    """Full text from up to max_sources different outlets."""
    picked, outlets = [], set()
    for item in story["items"]:
        if item["source"] not in outlets:
            outlets.add(item["source"])
            picked.append(item)
        if len(picked) == max_sources:
            break
    with ThreadPoolExecutor(max_workers=4) as pool:
        docs = list(pool.map(_read, picked))
    return [d for d in docs if len(d["text"]) >= 150]
