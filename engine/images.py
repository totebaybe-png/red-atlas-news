"""Image desk: legally reusable photos from Wikimedia Commons, plus a branded cover card."""
import os
import platform
import re
import subprocess
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from . import config

HEADERS = {"User-Agent": config.USER_AGENT}
SKIP_IMAGE = (r"flag|map|coat.of.arms|logo|emblem|seal|locator|diagram|chart|graph|plot|epicent|tsum|"
              r"poster|newspaper|stamp|banknote|signature|icon|screenshot|infographic|statistic|"
              r"\b1[0-9]{3}\b|\b19[0-9]{2}\b")  # file names with old years (1900s and earlier)
BAD_EXTENSIONS = (".svg", ".gif", ".pdf", ".tif", ".tiff", ".png", ".webm", ".ogv")
FREE_LICENSES = ("cc by", "cc-by", "cc0", "public domain", "pd", "cc by-sa", "cc-by-sa")

RED = (200, 16, 46)
WHITE = (255, 255, 255)
INK = (17, 17, 17)


def _commons_info(filename):
    resp = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={"action": "query", "titles": f"File:{filename}", "prop": "imageinfo",
                "iiprop": "url|extmetadata|size", "iiurlwidth": 1200, "format": "json"},
        headers=HEADERS, timeout=20,
    ).json()
    page = next(iter(resp["query"]["pages"].values()))
    if "imageinfo" not in page:  # not on Commons (e.g. non-free Wikipedia upload): skip
        return None
    info = page["imageinfo"][0]
    meta = info.get("extmetadata", {})
    license_name = meta.get("LicenseShortName", {}).get("value", "")
    if not license_name.lower().startswith(FREE_LICENSES):
        return None
    if info.get("width", 0) < 800:
        return None
    taken = re.sub(r"<[^>]+>", "", meta.get("DateTimeOriginal", {}).get("value", ""))
    year = re.search(r"\b(1[89]\d\d|20\d\d)\b", taken)
    if year and int(year.group(1)) < 2000:  # archive/historic pictures look wrong in today's news
        return None
    artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip() or "Unknown"
    desc = re.sub(r"<[^>]+>", " ", meta.get("ImageDescription", {}).get("value", "")).strip()
    desc = re.sub(r"\s+", " ", desc)[:160]
    clean_name = re.sub(r"\.[a-zA-Z0-9]+$", "", filename).replace("_", " ").strip()
    return {
        "url": info.get("thumburl") or info["url"],
        "page": info.get("descriptionurl"),
        "credit": f"{artist[:80]} / {license_name} via Wikimedia Commons",
        "caption": desc if len(desc) >= 20 else clean_name[:120],
        "license": license_name,
        "landscape": info.get("width", 0) >= info.get("height", 1) * 1.2,
    }


def _wiki_lead_photo(title):
    if not title:
        return None
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "titles": title, "prop": "pageimages",
                    "piprop": "name", "redirects": 1, "format": "json"},
            headers=HEADERS, timeout=20,
        ).json()
        page = next(iter(resp["query"]["pages"].values()))
        name = page.get("pageimage")
        if not name or name.lower().endswith(BAD_EXTENSIONS) or re.search(SKIP_IMAGE, name, re.I):
            return None
        return _commons_info(name)
    except (requests.RequestException, ValueError, KeyError, StopIteration):
        return None


def _commons_search_photos(query, limit=3, seen_urls=None):
    if not query:
        return []
    seen_urls = seen_urls or set()
    found = []
    try:
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": f"{query} filetype:bitmap",
                    "srnamespace": 6, "srlimit": 8, "format": "json"},
            headers=HEADERS, timeout=20,
        ).json()
        for hit in resp.get("query", {}).get("search", []):
            name = re.sub(r"^File:", "", hit.get("title", ""))
            if not name or name.lower().endswith(BAD_EXTENSIONS) or re.search(SKIP_IMAGE, name, re.I):
                continue
            info = _commons_info(name)
            if info and info["url"] not in seen_urls:
                seen_urls.add(info["url"])
                found.append(info)
                if len(found) >= limit:
                    break
    except (requests.RequestException, ValueError, KeyError):
        pass
    return found


def _commons_search_photo(query):
    res = _commons_search_photos(query, limit=1)
    return res[0] if res else None


SECTION_FALLBACKS = {
    "Gold": ["gold bullion bars", "gold coins treasure"],
    "Markets": ["stock exchange trading floor", "financial district skyscrapers"],
    "Economy": ["central bank building", "container ship global trade"],
    "Business": ["corporate headquarters financial district", "cargo port logistics"],
    "Tech": ["data center servers", "semiconductor microchip wafer"],
    "World": ["united nations general assembly", "diplomatic summit flags"],
}


def find_photo(wikipedia_title, fallback_query=""):
    """Lead image of the Wikipedia article, or a freely licensed Commons photo for the entity/topic."""
    photo = _wiki_lead_photo(wikipedia_title)
    if photo:
        return photo
    search_term = wikipedia_title or fallback_query
    if search_term:
        try:
            resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "list": "search", "srsearch": search_term, "srlimit": 3, "format": "json"},
                headers=HEADERS, timeout=15,
            ).json()
            for hit in resp.get("query", {}).get("search", []):
                photo = _wiki_lead_photo(hit.get("title", ""))
                if photo:
                    return photo
        except (requests.RequestException, ValueError, KeyError):
            pass
    return _commons_search_photo(fallback_query or wikipedia_title)


def find_article_photos(story_plan, article, max_photos=2):
    """Up to max_photos relevant, freely licensed archive photos. Returns [] rather than a weak match:
    the branded cover card is better than a photo that has nothing to do with the story.

    Order: the Wikipedia photo of the main person/organisation (not for disasters), then the
    photographable subjects the editor suggested ("Egyptian National Railways train"), then, for
    money and tech stories only, a safe generic topic image. The lead photo must be landscape.
    """
    plan = story_plan or {}
    label = article.get("label", "World")
    sensitive = bool(plan.get("sensitive"))
    # A bare country or city name returns pyramids and tourist shots, so require 2+ words
    subjects = [s.strip() for s in plan.get("visual_subjects", []) if s and len(s.split()) >= 2]
    photos, seen, portrait = [], set(), None

    def _add(p):
        nonlocal portrait
        if not p or not p.get("url") or p["url"] in seen or len(photos) >= max_photos:
            return
        seen.add(p["url"])
        if not photos and not p.get("landscape"):
            portrait = portrait or p  # a tall photo can still go inside the article
            return
        photos.append(p)

    if not sensitive:
        _add(_wiki_lead_photo(plan.get("wikipedia_title", "")))
    # One photo per subject first (variety), then a second pass if still short
    for per_subject in (1, 2):
        for subject in subjects:
            for p in _commons_search_photos(subject, limit=per_subject, seen_urls=set(seen)):
                p.setdefault("subject", subject)
                _add(p)
    if not photos and label != "World":
        for query in SECTION_FALLBACKS.get(label, []):
            for p in _commons_search_photos(query, limit=1, seen_urls=set(seen)):
                _add(p)
    if photos and portrait and len(photos) < max_photos:
        photos.append(portrait)
    for p in photos:
        p["file_photo"] = True  # none of these were taken at the event itself
        caption = p.get("caption", "")
        # Commons descriptions are often in other languages; fall back to the English subject
        if not caption or sum(c.isascii() for c in caption) < 0.9 * len(caption):
            p["caption"] = p.get("subject") or plan.get("main_entity") or "Archive photo"
    return photos


def publish_cover(path):
    """On GitHub Actions, commit and push the cover card BEFORE the post goes live, and return a
    jsDelivr URL pinned to that commit, so the image never shows as broken. None elsewhere."""
    if os.getenv("GITHUB_ACTIONS") != "true" or not os.getenv("GITHUB_REPOSITORY"):
        return None
    rel = Path(path).resolve().relative_to(config.ROOT.resolve()).as_posix()

    def git(*args):
        return subprocess.run(["git", *args], cwd=config.ROOT, check=True, capture_output=True, text=True).stdout

    try:
        git("config", "user.name", "Red Atlas Bot")
        git("config", "user.email", "bot@redatlasnews.com")
        git("add", rel)
        git("commit", "-m", f"cover: {Path(rel).parent.name}")
        git("pull", "--rebase", "--autostash", "origin", "main")
        git("push", "origin", "HEAD:main")
        sha = git("rev-parse", "HEAD").strip()
    except subprocess.CalledProcessError as e:
        print(f"   cover upload failed, publishing without it: {(e.stderr or '')[-200:]}")
        return None
    return f"https://cdn.jsdelivr.net/gh/{os.getenv('GITHUB_REPOSITORY')}@{sha}/{rel}"


def hosted_url(path):
    """Public URL for a cover card. Returns None until image hosting (GitHub + jsDelivr) is set up."""
    base = config.IMAGE_BASE_URL
    if not base:
        return None
    rel = Path(path).resolve().relative_to(config.OUTPUT_DIR.resolve()).as_posix()
    return f"{base.rstrip('/')}/{rel}"


def _font(size, bold=True):
    candidates = (
        ["C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"]
        if platform.system() == "Windows"
        else ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
              else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def cover_card(title, label, out_path):
    """1200x675 branded cover (the size Google Discover wants)."""
    img = Image.new("RGB", (1200, 675), RED)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 600, 1200, 675], fill=INK)
    # Logo
    d.rectangle([60, 50, 190, 112], fill=WHITE)
    d.text((125, 81), "RED", font=_font(44), fill=RED, anchor="mm")
    d.text((210, 81), "ATLAS", font=_font(44), fill=WHITE, anchor="lm")
    d.text((372, 85), "NEWS", font=_font(24), fill=WHITE, anchor="lm")
    # Section tag
    tag_font = _font(26)
    tag = label.upper()
    w = d.textlength(tag, font=tag_font)
    d.rectangle([60, 170, 60 + w + 36, 214], fill=INK)
    d.text((78, 192), tag, font=tag_font, fill=WHITE, anchor="lm")
    # Headline
    size = 64
    while size > 40:
        lines = textwrap.wrap(title, width=int(2000 / size))
        if len(lines) <= 4:
            break
        size -= 4
    y = 250
    for line in lines[:4]:
        d.text((60, y), line, font=_font(size), fill=WHITE)
        y += int(size * 1.2)
    d.text((60, 637), config.SITE_URL.replace("https://", ""), font=_font(24, bold=False), fill=WHITE, anchor="lm")
    img.save(out_path, "JPEG", quality=88, optimize=True)
    return out_path
