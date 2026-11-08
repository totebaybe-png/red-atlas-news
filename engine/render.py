"""Turns an article into Blogger-ready HTML and a local preview page."""
from html import escape
import json
import re

from . import config
from .gold_countries import PAGE_COUNTRIES

PUBLISHED_FILE = config.DATA_DIR / "published_posts.json"


def load_published_posts():
    if PUBLISHED_FILE.exists():
        try:
            return json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def record_published_post(article):
    if not article.get("url") or not article.get("title"):
        return
    posts = [p for p in load_published_posts() if p.get("url") != article["url"]]
    posts.insert(0, {
        "title": article["title"],
        "url": article["url"],
        "label": article.get("label", "World"),
        "tags": article.get("tags", []),
    })
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    PUBLISHED_FILE.write_text(json.dumps(posts[:200], indent=1, ensure_ascii=False), encoding="utf-8")


def faq_schema(faq_pairs):
    """Valid JSON-LD FAQPage schema for Google Rich Results and AI search."""
    if not faq_pairs:
        return ""
    entities = [
        {
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": a},
        }
        for q, a in faq_pairs if q and a
    ]
    if not entities:
        return ""
    payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities,
    }
    return f'<script type="application/ld+json">{json.dumps(payload, ensure_ascii=False)}</script>'


def _internal_and_partner_links(article):
    """Builds contextual internal links to gold tools, related posts, and sister sites."""
    text = f"{article.get('title', '')} {article.get('dek', '')} {article.get('body_html', '')}".lower()
    label = article.get("label", "World")
    links = []

    # 1. Link to live gold & silver hubs when relevant or in financial sections
    if label in ("Gold", "Markets", "Economy", "Business") or "gold" in text or "bullion" in text:
        links.append(('<a href="/p/gold-price-today.html">Live Gold Price Today (24K, 22K, 18K &amp; Calculator)</a>',
                      "Track real-time spot gold rates and calculate weight values in 29 currencies."))
    if "silver" in text or label in ("Gold", "Markets"):
        links.append(('<a href="/p/silver-price-today.html">Live Silver Price Today (999 Fine &amp; 925 Sterling)</a>',
                      "Compare international silver spot prices per gram, ounce, and kilogram."))

    # 2. Link to specific country gold pages mentioned in the article
    matched_countries = 0
    for c in PAGE_COUNTRIES:
        names = [c["short"].lower(), c["name"].lower().replace("the ", ""), c["currency"].lower()]
        if any(re.search(r"\b" + re.escape(n) + r"\b", text) for n in names if len(n) >= 2):
            slug = f"/p/gold-price-in-{c['slug']}.html"
            links.append((f'<a href="{slug}">Gold Price in {escape(c["short"])} Today ({c["currency"]})</a>',
                          f"Live {', '.join(c['karats'][:3])} rates and local weight conversions."))
            matched_countries += 1
            if matched_countries >= 2:
                break

    # 3. Link to related published articles on Red Atlas News
    published = load_published_posts()
    same_label = [p for p in published if p.get("label") == label and p.get("title") != article.get("title")]
    other_recent = [p for p in published if p.get("label") != label and p.get("title") != article.get("title")]
    for p in (same_label[:2] + other_recent[:1])[:3]:
        links.append((f'<a href="{escape(p["url"])}">{escape(p["title"])}</a>',
                      f"More coverage in {escape(p.get('label', 'World'))}."))

    # 4. Section hub link
    links.append((f'<a href="/search/label/{escape(label)}?max-results=12">More {escape(label)} News &amp; Analysis</a>',
                  f"Browse the latest {escape(label.lower())} reporting from {config.SITE_NAME}."))

    # 5. Contextual Financial Calculator (Only in Gold, Markets, and Economy sections)
    partner_items = []
    if label in ("Gold", "Markets", "Economy") or any(w in text for w in ("gold", "bullion", "currency", "inflation", "interest rate")):
        for site in config.load_partner_sites():
            if site.get("name") and site.get("url"):
                rel = site.get("rel", "noopener")
                desc = site.get("description", "Financial and investment calculation tools.")
                partner_items.append((
                    f'<a href="{escape(site["url"])}" rel="{escape(rel)}" target="_blank">{escape(site["name"])}</a>',
                    escape(desc),
                ))

    final_links = links[:5] + partner_items[:1]
    items = "".join(f"<li><strong>{anchor}</strong> — {desc}</li>" for anchor, desc in final_links)
    return f"<h2>Related Coverage &amp; Market Tools</h2><ul>{items}</ul>"


def _inject_inline_photos(body_html, extra_photos):
    """Inserts a secondary editorial photo before the 3rd (or 2nd) <h2> heading to break up text."""
    if not extra_photos:
        return body_html
    p = extra_photos[0]
    if not p or not p.get("url"):
        return body_html
    cap = escape(p.get("caption") or "Related editorial photograph")
    cred = escape(p.get("credit") or "Wikimedia Commons")
    label = "File photo: " if p.get("file_photo") else ""
    fig = (
        f'<figure style="margin:24px 0;text-align:center">'
        f'<img alt="{cap}" loading="lazy" src="{escape(p["url"])}" style="width:100%;height:auto;border-radius:6px"/>'
        f'<figcaption style="font-size:13px;color:#666;margin-top:6px">{label}{cap} (Photo: {cred})</figcaption>'
        f'</figure>\n'
    )
    parts = re.split(r"(?=<h2\b)", body_html, flags=re.I)
    if len(parts) >= 4:
        return "".join(parts[:3]) + fig + "".join(parts[3:])
    if len(parts) >= 3:
        return "".join(parts[:2]) + fig + "".join(parts[2:])
    return body_html + "\n" + fig


def post_html(article, image_src, credit=None, extra_photos=None, caption=None):
    """The HTML pasted into (or sent to) Blogger as the post body. A caption marks an archive
    ("file") photo, so readers never mistake it for a picture of the event itself."""
    out = []
    if image_src:
        out.append(f'<div class="separator" style="text-align:center"><img alt="{escape(caption or article["title"])}" '
                   f'src="{escape(image_src)}" width="1200" height="675" style="width:100%;height:auto"/></div>')
    if credit:
        lead = f"File photo: {escape(caption)}. " if caption else ""
        out.append(f'<p style="font-size:13px;color:#777;margin-top:4px">{lead}Photo: {escape(credit)}</p>')
    out.append(f'<p><strong>{escape(article.get("dek", ""))}</strong></p>')
    out.append(_inject_inline_photos(article["body_html"], extra_photos))
    out.append(_internal_and_partner_links(article))
    if article.get("faq"):
        out.append("<h2>Frequently Asked Questions</h2>")
        for item in article["faq"]:
            out.append(f"<h3>{escape(item['q'])}</h3><p>{escape(item['a'])}</p>")
        out.append(faq_schema([(item.get("q", ""), item.get("a", "")) for item in article["faq"]]))
    out.append("<h2>Sources</h2><ul>")
    for s in article["sources"]:
        out.append(f'<li><a href="{escape(s["url"])}" rel="nofollow noopener" target="_blank">'
                   f'{escape(s["name"])}: {escape(s["title"])}</a></li>')
    out.append("</ul>")
    outlets = ", ".join(sorted({s["name"] for s in article["sources"]}))
    out.append(f'<p style="font-size:14px;color:#777"><em>This report was prepared by the {config.SITE_NAME} '
               f'news desk based on reporting from {escape(outlets)}.</em></p>')
    return "\n".join(out)


def preview_page(article, body, report):
    """A standalone page to read the article on the computer, with the checker's report."""
    color = "#1a7f37" if report["decision"] == "publish" else "#b35900"
    problems = "".join(f"<li>{escape(p)}</li>" for p in report["problems"]) or "<li>None</li>"
    low = [u for u in report["fact_check"].get("unsupported", []) if u.get("severity") != "high"]
    notes = "".join(f"<li>{escape(u.get('claim', ''))}: {escape(u.get('reason', ''))}</li>" for u in low) or "<li>None</li>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(article['title'])}</title>
<style>
body{{margin:0;font:18px/1.75 system-ui,Segoe UI,Arial,sans-serif;color:#2b2b2b;background:#fff}}
header{{background:#C8102E;border-bottom:3px solid #111;padding:14px 20px;color:#fff;font:900 24px Arial Black,Arial}}
header b{{background:#fff;color:#C8102E;padding:0 8px;margin-right:8px}}
main{{max-width:760px;margin:0 auto;padding:24px 16px}}
.tag{{display:inline-block;background:#111;color:#fff;font:700 12px Arial;padding:4px 10px;text-transform:uppercase}}
h1{{font-size:40px;line-height:1.15;color:#111;margin:12px 0}} h2{{color:#111;margin-top:2rem}}
a{{color:#C8102E}} blockquote{{border-left:4px solid #C8102E;margin:0;padding-left:16px;color:#444}}
.report{{border:2px solid {color};border-radius:8px;padding:12px 18px;margin-bottom:24px;font-size:15px;line-height:1.5}}
.report h3{{margin:0 0 6px;color:{color}}} img{{max-width:100%;height:auto}}
</style></head><body>
<header><b>RED</b>ATLAS <small style="font-size:14px">NEWS</small></header>
<main>
<div class="report"><h3>Auto-check: {report['decision'].upper()}</h3>
Words: {article.get('word_count')} &middot; Copied from sources: {article.get('copied_ratio', 0):.1%} &middot;
Focus keyword: <b>{escape(article.get('focus_keyword', ''))}</b> &middot; Writer: {escape(article.get('model', ''))}<br>
Google searches used: {escape(', '.join(article.get('search_suggestions', [])))}<br>
Meta description: {escape(article.get('meta_description', ''))}
<p style="margin:8px 0 0"><b>Blocking problems:</b></p><ul>{problems}</ul>
<p style="margin:0"><b>Minor notes:</b></p><ul>{notes}</ul></div>
<span class="tag">{escape(article['label'])}</span>
<h1>{escape(article['title'])}</h1>
<p style="color:#777;font-size:15px">By {config.SITE_NAME} Desk</p>
{body}
</main></body></html>"""
