"""Settings for the Red Atlas News engine."""
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure UTF-8 console output on Windows even when workspace path contains Arabic characters
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _load_gemini_keys():
    """Collect all configured Gemini API keys (single, numbered 1..20, or comma-separated)."""
    raw = [os.getenv("GEMINI_API_KEY", "")]
    for i in range(1, 21):
        raw.append(os.getenv(f"GEMINI_API_KEY_{i}", ""))
    raw += re.split(r"[,;\s]+", os.getenv("GEMINI_API_KEYS", ""))
    seen, keys = set(), []
    for k in raw:
        k = k.strip()
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    return keys


GEMINI_API_KEYS = _load_gemini_keys()
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""

# Tried in order across all API keys; on quota errors (429) the engine rotates keys and models.
# Each key + model pair has its own free daily quota.
MODELS_WRITE = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
]
MODELS_LIGHT = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
]

SITE_NAME = "Red Atlas News"
SITE_URL = "https://redatlasnews.blogspot.com"
USER_AGENT = "RedAtlasNewsBot/1.0 (+https://redatlasnews.blogspot.com/p/about.html)"

# Site sections (must match the theme menu labels)
LABELS = ["World", "Gold", "Markets", "Economy", "Business", "Tech"]

FEEDS = {
    "BBC News": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "Al Jazeera": ["https://www.aljazeera.com/xml/rss/all.xml"],
    "The Guardian": [
        "https://www.theguardian.com/world/rss",
        "https://www.theguardian.com/uk/business/rss",
    ],
    "NPR": ["https://feeds.npr.org/1001/rss.xml"],
    "CNBC": [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.cnbc.com/id/15839069/device/rss/rss.html",
    ],
    "DW": ["https://rss.dw.com/rdf/rss-en-all"],
    "France 24": ["https://www.france24.com/en/rss"],
    "Sky News": ["https://feeds.skynews.com/feeds/rss/world.xml"],
    "ABC News": ["https://abcnews.go.com/abcnews/internationalheadlines"],
    "CBS News": ["https://www.cbsnews.com/latest/rss/world"],
    "MarketWatch": ["https://feeds.content.dowjones.io/public/rss/mw_topstories"],
    "FXStreet": ["https://www.fxstreet.com/rss/news"],
    "TechCrunch": ["https://techcrunch.com/feed/"],
    "The Verge": ["https://www.theverge.com/rss/index.xml"],
    "UN News": ["https://news.un.org/feed/subscribe/en/news/all/rss.xml"],
    # US and Europe
    "The New York Times": [
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    ],
    "The Wall Street Journal": [
        "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
        "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
    ],
    "Fox Business": ["https://moxie.foxbusiness.com/google-publisher/latest.xml"],
    "Business Insider": ["https://feeds.businessinsider.com/custom/all"],
    "The Independent": ["https://www.independent.co.uk/news/world/rss"],
    "Euronews": ["https://www.euronews.com/rss"],
    "Politico Europe": ["https://www.politico.eu/feed/"],
    # Asia
    "Times of India": ["https://timesofindia.indiatimes.com/rssfeedstopstories.cms"],
    "NDTV": ["https://feeds.feedburner.com/ndtvnews-world-news"],
    "The Hindu": ["https://www.thehindu.com/news/international/feeder/default.rss"],
    "The Economic Times": ["https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"],
    "South China Morning Post": ["https://www.scmp.com/rss/91/feed"],
    "The Japan Times": ["https://www.japantimes.co.jp/feed/"],
    "Nikkei Asia": ["https://asia.nikkei.com/rss/feed/nar"],
    "The Straits Times": ["https://www.straitstimes.com/news/world/rss.xml"],
    # Middle East, Africa, Oceania
    "The National": ["https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml"],
    "The Times of Israel": ["https://www.timesofisrael.com/feed/"],
    "Africanews": ["https://www.africanews.com/feed/rss"],
    "ABC Australia": ["https://www.abc.net.au/news/feed/51120/rss.xml"],
    # Markets and tech
    "Investing.com": ["https://www.investing.com/rss/news.rss"],
    "Wired": ["https://www.wired.com/feed/rss"],
    "Ars Technica": ["https://feeds.arstechnica.com/arstechnica/index"],
}

# Live Google Trends: the richest English-speaking ad markets
TREND_GEOS = ["US", "GB", "IN", "CA", "AU", "AE"]

# Topics our audience cares about most (gold, money, power)
BOOST_WORDS = {
    "gold": 6, "silver": 4, "bullion": 6, "precious": 3,
    "fed": 4, "federal reserve": 5, "interest rate": 5, "rates": 2, "inflation": 5,
    "dollar": 3, "oil": 3, "opec": 4, "stocks": 3, "market": 2, "markets": 2,
    "recession": 4, "gdp": 4, "tariff": 4, "tariffs": 4, "trade": 2, "central bank": 5,
    "economy": 3, "bitcoin": 3, "crypto": 2, "earnings": 2, "ipo": 3,
    "war": 2, "sanctions": 3, "election": 2, "china": 2,
    "nvidia": 2, "apple": 2, "tesla": 2, "ai": 2,
}

MAX_STORY_AGE_HOURS = 18
MIN_WORDS = 800
MAX_SOURCE_CHARS = 7000

# Where cover cards are served from once the GitHub repo exists (jsDelivr CDN), e.g.
# https://cdn.jsdelivr.net/gh/<user>/<repo>@main/output
_gh_repo = os.getenv("GITHUB_REPOSITORY", "totebaybe-png/red-atlas-news").strip()
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "").strip() or (
    f"https://cdn.jsdelivr.net/gh/{_gh_repo}@main/output" if _gh_repo else ""
)

OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
PARTNER_SITES_FILE = DATA_DIR / "partner_sites.json"


def load_partner_sites():
    """Return configured sister/partner sites for cross-network links."""
    if PARTNER_SITES_FILE.exists():
        try:
            sites = json.loads(PARTNER_SITES_FILE.read_text(encoding="utf-8"))
            return [s for s in sites if s.get("url") and s.get("name")]
        except Exception:
            return []
    return []
