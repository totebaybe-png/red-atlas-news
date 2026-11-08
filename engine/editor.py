"""Editor: groups headlines about the same event and ranks the stories."""
import json
import re
import unicodedata

from . import config

STOP = set("""a an the of to in on for and or but with at by from as is are was were be been has have had
it its this that these those after before over under into about amid says said say new will would could
can may might not no than then up down out off more most than vs via how why what who when where which
his her their they them he she we you i our your after while during just""".split())

SEEN_FILE = config.DATA_DIR / "seen.json"


def _root(word):
    # Crude word root so "collision"/"collide", "trains"/"train" and "injured"/"injures" match
    return word if len(word) <= 5 else word[:5]


def tokens(text):
    # Strip accents so "Kraków" and "Krakow" match
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", text.lower())
    # Numbers ("88 injured", "5.7 quake") are strong fingerprints of one event, so keep short ones too
    return {_root(w) for w in words if w not in STOP and (len(w) > 2 or (w.isdigit() and len(w) == 2))}


def _core(c):
    """Words that at least 40% of the group's headlines share: what the story is really about."""
    counts = {}
    for t in c["titles"]:
        for w in t:
            counts[w] = counts.get(w, 0) + 1
    need = max(1, -(-len(c["titles"]) * 2 // 5))
    return {w for w, n in counts.items() if n >= need}


def _merge_similar(clusters):
    """Second pass: join groups whose headlines describe the same event in different words."""
    merged = True
    while merged:
        merged = False
        cores = [_core(c) for c in clusters]
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                shared = cores[i] & cores[j]
                smaller = min(len(cores[i]), len(cores[j])) or 1
                ratio = len(shared) / smaller
                if (len(shared) >= 3 and ratio >= 0.5) or (len(shared) >= 4 and ratio >= 0.4):
                    a, b = clusters[i], clusters[j]
                    a["items"] += b["items"]
                    a["tokens"] |= b["tokens"]
                    a["titles"] += b["titles"]
                    del clusters[j]
                    merged = True
                    break
            if merged:
                break
    return clusters


def cluster(items):
    """Greedy grouping by headline word overlap, then a merge pass."""
    clusters = []
    for item in sorted(items, key=lambda i: i["published"], reverse=True):
        item_tokens = tokens(item["title"] + " " + item["summary"][:160])
        title_tokens = tokens(item["title"])
        best, best_score = None, 0.0
        for c in clusters:
            inter = len(item_tokens & c["tokens"])
            # Share of this headline's key words found in the group's core
            score = len(title_tokens & _core(c)) / (len(title_tokens) or 1)
            # Same outlet: many templated headlines ("X Share Price Highlights") look alike
            needed = 0.7 if any(i["source"] == item["source"] for i in c["items"]) else 0.4
            if inter >= 3 and score >= needed and score > best_score:
                best, best_score = c, score
        if best:
            best["items"].append(item)
            best["tokens"] |= item_tokens
            best["titles"].append(title_tokens)
        else:
            clusters.append({"items": [item], "tokens": set(item_tokens), "titles": [title_tokens]})
    return _merge_similar(clusters)


def score(c, trends):
    sources = {i["source"] for i in c["items"]}
    text = " ".join(i["title"] + " " + i["summary"] for i in c["items"]).lower()
    s = len(sources) * 4 + min(len(c["items"]), 8)
    newest = min(i["age_hours"] for i in c["items"])
    s += max(0, 6 - newest / 2)
    s += sum(w for k, w in config.BOOST_WORDS.items() if re.search(r"\b" + re.escape(k) + r"\b", text))
    matched = [t for t in trends if len(t) > 3 and t in text]
    s += min(10, 4 * len(matched))
    c["trend_matches"] = matched[:5]
    c["sources"] = sorted(sources)
    c["score"] = round(s, 1)
    c["headline"] = c["items"][0]["title"]
    return s


def load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    return {"urls": [], "titles": []}


def save_seen(seen):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    seen["urls"] = seen["urls"][-3000:]
    seen["titles"] = seen["titles"][-500:]
    SEEN_FILE.write_text(json.dumps(seen, indent=1), encoding="utf-8")


def already_covered(c, seen):
    if any(i["url"] in seen["urls"] for i in c["items"]):
        return True
    for title in seen["titles"]:
        old = tokens(title)
        if len(old & c["tokens"]) / (len(old) or 1) >= 0.6:
            return True
    return False


def top_stories(items, trends, limit):
    seen = load_seen()
    clusters = [c for c in cluster(items) if not already_covered(c, seen)]
    for c in clusters:
        score(c, trends)
    # Prefer stories confirmed by at least two outlets
    clusters.sort(key=lambda c: (len(c["sources"]) >= 2, c["score"]), reverse=True)
    return clusters[:limit]
