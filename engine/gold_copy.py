"""Long-form, unique copy for each gold page, written once by Gemini and cached.

The copy never contains prices or other figures: every number on the page comes from the
live, verified price tables, so the text cannot go stale or be wrong.

    python -m engine.gold_copy            write missing copy
    python -m engine.gold_copy --force    rewrite everything
"""
import json
import re
import sys

from . import config, gold_keywords, llm
from .gold_countries import PAGE_COUNTRIES, UNITS

COPY_DIR = config.DATA_DIR / "gold_copy"
MIN_WORDS = 1200

# Figures allowed in the prose: purity names, fineness marks, standard weights and verified constants
ALLOWED_NUMBER = re.compile(
    r"^(24|22|21|18|14|12|10|9)k$|^(24|22|21|18|14|10)-karat$|"
    r"^(999|9999|995|916|875|750|585|417|375|925|958|99\.9|99\.99|99\.5|91\.6|91\.67|87\.5|75|58\.5|92\.5)%?$",
    re.I,
)

STYLE = """WRITING RULES
- Expert, trustworthy, warm tone. Short paragraphs (2-4 sentences). American English spelling except local terms (jewellery is fine for India, UK, Gulf, South Asia).
- Use the search phrases below naturally in headings, the opening and the FAQ, the way a human editor would. Never stuff or repeat a phrase awkwardly.
- NO prices, NO exchange rates, NO percentages, NO dates, NO years, NO statistics. The live price tables on the page show all numbers.
  You SHOULD write purities as digits (24K, 22K, 21K, 18K, "22 karat"), weights as digits (1 gram, 10 grams, 8 grams, 1 tola) and fineness marks (999, 916, 750).
- The search phrases are lowercase; always write names with correct capitals (India, UAE, Dubai, Pakistan).
- Do not name specific shops, brands or companies. Do not invent laws, taxes or regulations. Only state facts that are well established and stable; when unsure, stay general.
- Each section must give genuinely useful, practical information for a buyer or investor in this market.
- Return valid JSON only."""

UNIT_FIGURES = {
    "11.66", "11.664", "11.6638", "37.43", "37.429", "31.1", "31.103", "31.1035",
    "7.32", "7.988", "3.6725", "3.67", "3.75", "3.64",
    "99.9", "99.99", "99.5", "91.6", "91.67", "87.5", "58.5", "92.5",
    "50", "100", "250", "500", "1000", "1,000", "400",
}


def _numbers(text):
    """Figures that could be prices, rates or dates. Purities, fineness marks and standard unit weights are fine."""
    bad = []
    for m in re.findall(r"\d[\d.,]*\s?%", text):
        clean = m.replace(" ", "")
        if not ALLOWED_NUMBER.match(clean):
            bad.append(m)
    for t in re.findall(r"\b\d[\d.,]*\b", text):
        if t in UNIT_FIGURES or ALLOWED_NUMBER.match(t) or (t.isdigit() and int(t) <= 32):
            continue
        bad.append(t)
    return bad


def _plain(copy):
    parts = [copy.get("intro", "")]
    for s in copy.get("sections", []):
        parts += [s.get("h2", "")] + s.get("paragraphs", []) + s.get("bullets", [])
    for f in copy.get("faq", []):
        parts += [f.get("q", ""), f.get("a", "")]
    return " ".join(parts)


def words(copy):
    return len(re.sub(r"<[^>]+>", " ", _plain(copy)).split())


def _prompt(kind, keywords, country=None):
    if kind == "country":
        c = country
        units = ", ".join(UNITS[u][0] for u in c["units"])
        subject = f"""PAGE: "Gold price in {c['name']} today" on {config.SITE_NAME}.
Market facts you may use (verified): {c['note']}
Currency: {c['currency']}. Units local buyers use: {units}. Popular purities: {', '.join(c['karats'])}.
The page already shows live tables: price per unit for each purity, a price-by-weight table, a gold calculator
and live silver prices for {c['short']}. Refer to them ("the table above", "our calculator") instead of giving numbers.

Write sections such as (adapt the headings to this country, make them specific and keyword-rich):
- Gold rate in {c['short']} today: how to read the live prices (per unit, per purity)
- Which gold purity to buy in {c['short']} and why ({', '.join(c['karats'])})
- Gold weights used in {c['short']} explained ({units})
- Why local shop prices differ from the spot-based price (making charges, premiums, local taxes in general terms)
- Jewellery vs bars and coins in {c['short']}
- What moves the gold price in {c['short']} (global spot price, the {c['currency']} exchange rate, demand seasons and festivals if relevant)
- Practical tips before buying gold in {c['short']} (hallmarks/purity marks, receipts, weighing, buy-back)"""
    elif kind == "hub":
        subject = f"""PAGE: "Gold Price Today" global hub on {config.SITE_NAME}. It shows a live gold price table that detects the
visitor's country, a US dollar table per gram/ounce/kilo, a price-by-weight table, a calculator and links to
gold price pages for many countries. Explain everything a global reader needs: what the spot price is, live
gold price per gram vs ounce vs tola vs kilo, 24K vs 22K vs 21K vs 18K, how to calculate the price of any
gold item, why prices differ by country and shop, what moves the gold price (interest rates, the dollar,
inflation, central banks, geopolitics, demand), gold and silver together, and tips for buyers and investors."""
    else:
        subject = f"""PAGE: "Silver Price Today" on {config.SITE_NAME}. It shows live silver spot prices per gram, ounce and kilo
for many currencies. Explain silver spot price, 999 fine vs 925 sterling, silver per gram vs ounce vs kilo,
why silver is more volatile than gold, industrial demand, the gold-to-silver ratio in general terms,
silver bars and coins vs silverware and jewellery, and buying tips."""

    return f"""{subject}

SEARCH PHRASES PEOPLE USE (use the important ones naturally): {keywords[:40]}

{STYLE}

Return JSON:
{{
 "intro": "2 short paragraphs (as one string with <br/><br/> between) opening the page, main search phrase in the first sentence",
 "sections": [{{"h2": "specific heading", "paragraphs": ["...", "..."], "bullets": ["optional short list items"]}}],
 "faq": [{{"q": "real search-style question", "a": "2-4 sentence answer"}}]
}}
Write 7-8 sections and 7 FAQ items. Total length at least {MIN_WORDS + 200} words."""


def write(kind, key, keywords, country=None):
    prompt = _prompt(kind, keywords, country)
    for attempt in range(3):
        copy, model = llm.generate_json(prompt, config.MODELS_WRITE, temperature=0.6)
        nums = _numbers(_plain(copy))
        n = words(copy)
        if not nums and n >= MIN_WORDS:
            copy["model"] = model
            copy["words"] = n
            return copy
        feedback = []
        if nums:
            feedback.append(f"Your text contained figures that are not allowed: {sorted(set(nums))[:10]}. Remove every one.")
        if n < MIN_WORDS:
            feedback.append(f"Your text had only {n} words. Write at least {MIN_WORDS + 200}.")
        prompt += "\n\nPREVIOUS ATTEMPT REJECTED: " + " ".join(feedback)
        print(f"    retry {key}: {' '.join(feedback)[:120]}")
    raise RuntimeError(f"Could not write acceptable copy for {key}")


def build(force=False, only=None):
    COPY_DIR.mkdir(parents=True, exist_ok=True)
    kws = gold_keywords.build()
    jobs = [("hub", "hub", None), ("silver", "silver", None)] + [("country", c["code"], c) for c in PAGE_COUNTRIES]
    for kind, key, country in jobs:
        path = COPY_DIR / f"{key}.json"
        if (path.exists() and not force) or (only and key not in only):
            continue
        copy = write(kind, key, kws[key], country)
        path.write_text(json.dumps(copy, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"  {key}: {copy['words']} words ({copy['model']})", flush=True)


def load(key):
    path = COPY_DIR / f"{key}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


if __name__ == "__main__":
    only = [a for a in sys.argv[1:] if not a.startswith("--")] or None
    build(force="--force" in sys.argv, only=only)
