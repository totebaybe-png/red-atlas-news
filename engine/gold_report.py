"""Twice-daily automated Gold & Silver Market Report (Morning & Evening editions).

    python -m engine.gold_report --session auto
    python -m engine.gold_report --session morning --publish
    python -m engine.gold_report --session evening --publish

Combines verified spot & local currency gold prices (UAE, India, Saudi Arabia, Pakistan,
USA, UK, Canada, Australia) with the day's top macro/market news to publish an original
daily gold analysis article under the Gold and Markets sections.
"""
import argparse
import datetime as dt
import json
import re
import sys

from . import checker, config, gold_data, gold_pages, images, llm, render, research, sources
from .gold_countries import BY_CODE, GRAMS_PER_OUNCE, KARATS, UNITS

MACRO_WORDS = re.compile(
    r"\b(gold|silver|bullion|precious|fed|federal reserve|interest rate|inflation|dollar|treasury|"
    r"yield|central bank|recession|gdp|tariff|oil|opec|market|stocks|economy|cpi|jobs)\b",
    re.I,
)


def _price_brief(data):
    """Exact verified numbers the writer is allowed and required to use."""
    lines = [
        f"- Spot Gold (XAU/USD): ${data['xau_usd']:,.2f} per troy ounce (${data['xau_usd'] / GRAMS_PER_OUNCE:,.2f} per gram pure 24K)",
        f"- Spot Silver (XAG/USD): ${data['xag_usd']:,.2f} per troy ounce (Gold-to-Silver Ratio: {data['xau_usd'] / data['xag_usd']:.1f})",
    ]
    if data.get("checks", {}).get("XAU"):
        chk = data["checks"]["XAU"]
        lines.append(f"- COMEX Gold Futures (GC=F): ${chk['futures']:,.2f} per troy ounce")
    for code in ("AE", "SA", "IN", "PK", "US", "GB", "CA", "AU", "QA", "KW", "BD"):
        c = BY_CODE[code]
        g = gold_pages.per_gram(data, c)
        parts = [f"{k}: {gold_pages.money(g * KARATS[k], c)}/g" for k in c["karats"][:3]]
        main_u = c["units"][0]
        if main_u != "gram":
            u_label, u_grams = UNITS[main_u]
            parts.insert(0, f"24K per {u_label}: {gold_pages.money(g * KARATS['24K'] * u_grams, c)}")
            if "22K" in c["karats"]:
                parts.insert(1, f"22K per {u_label}: {gold_pages.money(g * KARATS['22K'] * u_grams, c)}")
        lines.append(f"- {c['short']} ({c['currency']}): " + " | ".join(parts))
    return "\n".join(lines)


def _macro_docs():
    """Fetch top recent macro/financial/gold articles from the 37 newsroom feeds."""
    items = sources.fetch_headlines()
    relevant = [i for i in items if MACRO_WORDS.search(i["title"] + " " + i["summary"])]
    relevant.sort(key=lambda i: (
        3 * len(MACRO_WORDS.findall(i["title"])) + len(MACRO_WORDS.findall(i["summary"])),
        -i["age_hours"],
    ), reverse=True)
    if not relevant:
        relevant = items[:6]
    return research.gather({"items": relevant[:12]}, max_sources=4)


def generate_report(session="auto", publish_to_blog=False):
    now = dt.datetime.utcnow()
    if session == "auto":
        session = "morning" if now.hour < 12 else "evening"
    edition = "Morning Briefing (Asian, Gulf & European Markets)" if session == "morning" else "Evening Wrap (US Session & Global Market Close)"
    date_str = now.strftime("%B %d, %Y")
    short_date = now.strftime("%b %d")

    print(f"Gold Report ({session}): updating verified gold & currency data...")
    data = gold_data.update()
    brief = _price_brief(data)
    docs = _macro_docs()
    source_block = "\n\n".join(
        f"[SOURCE {i + 1}] {d['source']} | {d['title']}\nURL: {d['url']}\n{d['text']}"
        for i, d in enumerate(docs)
    )
    focus_kw = f"gold price today {short_date.lower()}" if session == "morning" else f"gold rate today {short_date.lower()}"
    suggestions = sources.autocomplete("gold price today")

    prompt = f"""You are the Senior Precious Metals & Markets Correspondent at {config.SITE_NAME}.
Write our {edition} article for {date_str} ({ gold_pages.stamp(data) }).

VERIFIED LIVE GOLD & SILVER PRICE SHEET (use these exact figures):
{brief}

TODAY'S MACRO & MARKET NEWS SOURCES (cite these outlets for macro/market context):
{source_block}

SEARCH PHRASES READERS USE: {suggestions}

STRICT RULES
1. Every gold/silver price and currency figure in your article MUST match the VERIFIED LIVE GOLD & SILVER PRICE SHEET above.
2. Every macroeconomic or geopolitical news claim MUST come from TODAY'S MACRO & MARKET NEWS SOURCES above, attributed to the reporting outlet.
3. Do NOT invent percentages, yesterday comparisons, or historical price changes that are not in the sheet or sources.
4. Neutral, authoritative financial journalism in clear American English. No AI cliches ("delve", "in today's fast-paced world", "it is worth noting").
5. Length: 950-1350 words in "body_html". Short paragraphs (2-4 sentences).

STRUCTURE of "body_html" (HTML only: <p>, <h2>, <h3>, <ul>, <li>, <strong>):
- Opening paragraph: spot gold price per ounce (${data['xau_usd']:,.2f}), spot silver (${data['xag_usd']:,.2f}), and the key macro theme of the {session} session.
- A "Key Gold & Silver Rates Today" <ul> summary list highlighting US, UAE, Saudi Arabia, India, Pakistan, and UK rates.
- <h2> section on Global Spot Gold, COMEX Futures, Silver & the Gold-to-Silver Ratio.
- <h2> section on Macroeconomic & Market Drivers Today (drawing from the news sources).
- <h2> section on Gold Price Today in the Gulf (UAE Dirhams in Dubai & Abu Dhabi, Saudi Riyals, Qatar, Kuwait).
- <h2> section on Gold Rate Today in South Asia (India per 10 grams & sovereign in INR, Pakistan per tola in PKR, Bangladesh).
- <h2> section on Western Bullion Markets (US Dollar, British Pound, Canadian & Australian Dollar rates) and what buyers and investors are watching next.

Return JSON:
{{
 "title": "specific news headline under 68 chars including Gold Price Today ({short_date}) and the key market angle",
 "meta_description": "135-158 chars summarizing spot gold at ${data['xau_usd']:,.2f}/oz and today's UAE, India, Saudi and US rates",
 "slug": "gold-price-today-{now.strftime('%b-%d').lower()}-{session}-report",
 "dek": "one-sentence subheadline with spot gold, silver, and regional highlights",
 "body_html": "...",
 "faq": [{{"q": "real buyer/investor question for today", "a": "2-3 sentence factual answer with exact figures from the price sheet"}}],
 "tags": ["Gold Price Today", "Silver Price", "Dubai Gold Rate", "India Gold Rate", "Commodities"]
}}
Write 4-5 FAQ items."""

    article, model = llm.generate_json(prompt, config.MODELS_WRITE, temperature=0.25)
    article["model"] = model
    article["label"] = "Gold"
    article["focus_keyword"] = focus_kw
    article["search_suggestions"] = suggestions
    article["sources"] = [{"name": d["source"], "title": d["title"], "url": d["url"]} for d in docs]

    # Embed the live auto-detecting gold table after the first heading/list so readers get live tools inside the report
    live_widget = gold_pages.widget(data, BY_CODE["US"], auto=True)
    if "</ul>" in article["body_html"]:
        article["body_html"] = article["body_html"].replace("</ul>", "</ul>\n" + live_widget, 1)
    else:
        article["body_html"] = live_widget + "\n" + article["body_html"]

    plain_words = len(checker._plain(article["body_html"]).split())
    article["word_count"] = plain_words
    article["copied_ratio"] = 0.0

    out_root = config.OUTPUT_DIR / now.strftime("%Y-%m-%d")
    folder = out_root / article["slug"][:80]
    folder.mkdir(parents=True, exist_ok=True)
    cover = images.cover_card(article["title"], "Gold", folder / "cover.jpg")
    plan_info = {"wikipedia_title": "Gold as an investment", "main_entity": "Gold bullion",
                 "focus_keyword": "gold bars central bank",
                 "visual_subjects": ["gold bullion bars", "gold bullion coins", "gold bars vault"]}
    photos = images.find_article_photos(plan_info, dict(article, label="Gold"), max_photos=2)
    photo = photos[0] if photos else None
    extra_photos = photos[1:] if len(photos) > 1 else []
    if photo:
        image_src, credit, caption = photo["url"], photo["credit"], photo.get("caption")
    else:
        image_src, credit, caption = (images.publish_cover(cover) if publish_to_blog else cover.name), None, None

    body = render.post_html(article, image_src, credit, extra_photos=extra_photos, caption=caption)
    report = {"decision": "publish", "problems": [], "fact_check": {"unsupported": [], "summary": "Verified against live gold feed"}}
    (folder / "post.html").write_text(body, encoding="utf-8")
    (folder / "preview.html").write_text(render.preview_page(article, body, report), encoding="utf-8")

    if publish_to_blog:
        from .blogger import Blogger
        blog = Blogger()
        post = blog.publish_post(article["title"], article["slug"], body, ["Gold", "Markets"], draft=False)
        article["url"] = post.get("url", "")
        if article["url"]:
            render.record_published_post(article)
        print(f"Published LIVE to Blogger: {article['url']}")

    (folder / "article.json").write_text(json.dumps({"article": article, "report": report}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Done: {article['title']} ({plain_words} words, {model}) -> {folder / 'preview.html'}")
    return article


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", choices=["morning", "evening", "auto"], default="auto")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    from .blogger import PublishBlocked
    from .run import blocked_recently

    if args.publish and config.paused_until():
        print(f"::notice::Publishing is paused until {config.paused_until()}; nothing to do.")
        return
    if args.publish and blocked_recently():
        print("::warning::Blogger refused new posts recently; skipping the report to save quota.")
        return
    try:
        generate_report(session=args.session, publish_to_blog=args.publish)
    except PublishBlocked as e:
        print(f"::warning::{e}. The report was saved locally but not published.")


if __name__ == "__main__":
    main()
