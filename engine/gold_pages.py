"""Builds the gold price hub, the silver page and one page per country.

    python -m engine.gold_pages

Pages contain real prices at build time (so Google sees numbers) and a widget the theme
refreshes live in the visitor's browser. Output: output/gold-pages/<slug>.html + manifest.json
"""
import datetime as dt
import json
import re
import time
from html import escape

from . import config, gold_copy, gold_data, render
from .gold_countries import BY_CODE, COUNTRIES, GRAMS_PER_OUNCE, KARATS, PAGE_COUNTRIES, UNITS, weights_for

OUT = config.OUTPUT_DIR / "gold-pages"
HUB_SLUG = "gold-price-today"
SILVER_SLUG = "silver-price-today"
SILVER_PURITIES = {"999 Fine": 0.999, "925 Sterling": 0.925}
REGIONS = [
    ["AE", "SA", "QA", "KW", "OM", "BH", "EG", "JO"],
    ["IN", "PK", "BD", "NP", "LK"],
    ["US", "CA", "GB", "EU", "AU", "NZ"],
    ["MY", "SG", "PH", "ID", "HK", "TR"],
    ["ZA", "NG", "KE", "GH"],
]


def page_url(slug):
    return f"/p/{slug}.html"


def country_slug(c):
    return f"gold-price-in-{c['slug']}"


def _group(digits, indian):
    if not indian or len(digits) <= 3:
        return f"{int(digits):,}"
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def money(value, c):
    """Same rules as raFmt() in the theme: no decimals from 1,000 up, else 2."""
    decimals = 0 if value >= 1000 else 2
    text = f"{value:.{decimals}f}"
    whole, _, frac = text.partition(".")
    # Lakh grouping (1,23,456) where readers use it
    whole = _group(whole, c["currency"] in ("INR", "NPR", "PKR", "BDT"))
    sym = c["symbol"]
    sep = " " if len(sym) > 1 and sym.isalpha() else ""
    return f"{sym}{sep}{whole}{'.' + frac if frac else ''}"


def per_gram(data, c, metal="XAU"):
    usd_oz = data["xau_usd"] if metal == "XAU" else data["xag_usd"]
    return usd_oz / GRAMS_PER_OUNCE * data["fx"][c["currency"]]


def stamp(data):
    t = dt.datetime.fromisoformat(data["updated"].rstrip("Z"))
    return t.strftime("%B %d, %Y, %H:%M UTC").replace(" 0", " ")


def widget(data, c, auto=False):
    """Gold table. Markup must match raGoldRender() in theme-build/parts/templates.js."""
    g = per_gram(data, c)
    top = c["karats"][0]
    main_unit = c["units"][0]  # the unit local buyers search for (tola, 10 grams, ounce...)
    rows = "".join(
        f"<tr><th>{k}</th>" + "".join(f"<td>{money(g * KARATS[k] * UNITS[u][1], c)}</td>" for u in c["units"]) + "</tr>"
        for k in c["karats"]
    )
    head = "".join(f"<th>{UNITS[u][0]}</th>" for u in c["units"])
    return (
        f'<div class="ra-gold" data-country="{"auto" if auto else c["code"]}" data-metal="XAU">'
        f'<div class="ra-gold-head"><div><span class="ra-gold-label">Gold price in {escape(c["short"])} today</span>'
        f'<strong class="ra-gold-big">{money(g * KARATS[top] * UNITS[main_unit][1], c)}</strong>'
        f'<span class="ra-gold-sub">{UNITS[main_unit][0]}, {top} &middot; {c["currency"]}</span></div>'
        f'<div class="ra-gold-upd">Updated {stamp(data)}<br/>Spot gold ${data["xau_usd"]:,.2f}/oz</div></div>'
        f'<div class="ra-gold-scroll"><table class="ra-gold-table"><thead><tr><th>Purity</th>{head}</tr></thead>'
        f"<tbody>{rows}</tbody></table></div></div>"
    )


def silver_widget(data, c):
    g = per_gram(data, c, "XAG")
    units = ["gram", "ounce", "kg"]
    rows = "".join(
        f"<tr><th>{p}</th>" + "".join(f"<td>{money(g * f * UNITS[u][1], c)}</td>" for u in units) + "</tr>"
        for p, f in SILVER_PURITIES.items()
    )
    head = "".join(f"<th>{UNITS[u][0]}</th>" for u in units)
    return (
        f'<div class="ra-gold" data-country="{c["code"]}" data-metal="XAG">'
        f'<div class="ra-gold-head"><div><span class="ra-gold-label">Silver price in {escape(c["short"])} today</span>'
        f'<strong class="ra-gold-big">{money(g * 0.999, c)}</strong>'
        f'<span class="ra-gold-sub">per gram, 999 fine &middot; {c["currency"]}</span></div>'
        f'<div class="ra-gold-upd">Updated {stamp(data)}<br/>Spot silver ${data["xag_usd"]:,.2f}/oz</div></div>'
        f'<div class="ra-gold-scroll"><table class="ra-gold-table"><thead><tr><th>Purity</th>{head}</tr></thead>'
        f"<tbody>{rows}</tbody></table></div></div>"
    )


def country_links(codes=None, current=None):
    items = [BY_CODE[x] for x in codes if BY_CODE[x] in PAGE_COUNTRIES] if codes else PAGE_COUNTRIES
    links = "".join(
        f'<a href="{page_url(country_slug(c))}">Gold price in {escape(c["short"])} <small>{c["currency"]}</small></a>'
        for c in items if c["code"] != current
    )
    return f'<div class="ra-gold-links">{links}</div>'


def faq_html(faq):
    return "<h2>Frequently Asked Questions</h2>" + "".join(
        f"<h3>{escape(q)}</h3><p>{escape(a)}</p>" for q, a in faq
    ) + render.faq_schema(faq)


def disclaimer():
    return ('<p class="ra-gold-note">Prices are based on the international spot price and live exchange rates, '
            'refreshed automatically. Jewellers and dealers add making charges, premiums and local taxes, so shop '
            'prices are usually higher. For information only, not investment advice. '
            f'See our <a href="{page_url("disclaimer")}">Disclaimer</a>.</p>')


def tiles(data, c):
    """One tile per purity. Markup must match raTilesRender() in theme-build/parts/gold.js."""
    g = per_gram(data, c)
    main = c["units"][0]
    cells = "".join(
        f'<div class="ra-tile"><span class="ra-tile-k">{k}</span><strong>{money(g * KARATS[k], c)}</strong>'
        f'<small>per gram</small><em>{money(g * KARATS[k] * UNITS[main][1], c)} / {UNITS[main][0].replace("1 ", "")}</em></div>'
        for k in c["karats"]
    )
    return f'<div class="ra-gold-tiles" data-country="{c["code"]}">{cells}</div>'


def weights_table(data, c, metal="XAU"):
    """Price by weight for every purity. Markup must match raWeightsRender() in gold.js."""
    g = per_gram(data, c, metal)
    purities = list(SILVER_PURITIES.items()) if metal == "XAG" else [(k, KARATS[k]) for k in c["karats"]]
    head = "".join(f"<th>{p}</th>" for p, _ in purities)
    rows = "".join(
        f"<tr><th>{label}</th>" + "".join(f"<td>{money(g * f * grams, c)}</td>" for _, f in purities) + "</tr>"
        for label, grams in weights_for(c)
    )
    return (f'<div class="ra-gold-weights ra-gold-scroll" data-country="{c["code"]}" data-metal="{metal}">'
            f'<table class="ra-gold-table"><thead><tr><th>Weight</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>')


def calculator(c):
    """Filled in by raCalcRender() in gold.js; the text is what search engines and no-JS readers see."""
    return (f'<div class="ra-gold-calc" data-country="{c["code"]}"><p>Enter a weight and purity to calculate the '
            f'value of your gold in {c["currency"]} at today\'s live price.</p></div>'
            '<p class="ra-gold-note">For additional financial, percentage and unit conversions, use '
            '<a href="https://calculatoranubis.com/" rel="noopener" target="_blank">Anubis Calculator</a>, '
            'or manage documents and charts with <a href="https://anubispdf.com/" rel="noopener" target="_blank">Anubis PDF</a> '
            'and <a href="https://image.anubispdf.com/" rel="noopener" target="_blank">Anubis Image Tools</a>.</p>')


def copy_sections(copy, part):
    """Writer sections split in two halves around the silver block."""
    sections = copy.get("sections", []) if copy else []
    half = (len(sections) + 1) // 2
    chosen = sections[:half] if part == 1 else sections[half:]
    out = []
    for s in chosen:
        out.append(f"<h2>{escape(s['h2'])}</h2>")
        out += [f"<p>{escape(p)}</p>" for p in s.get("paragraphs", [])]
        if s.get("bullets"):
            out.append("<ul>" + "".join(f"<li>{escape(b)}</li>" for b in s["bullets"]) + "</ul>")
    return "\n".join(out)


def intro_html(copy):
    if not copy:
        return ""
    return "".join(f"<p>{escape(p.strip())}</p>" for p in re.split(r"<br\s*/?>\s*<br\s*/?>", copy["intro"]) if p.strip())


def faq_items(copy, data_faq):
    return data_faq + [(f["q"], f["a"]) for f in (copy or {}).get("faq", [])]


def build_country(data, c):
    copy = gold_copy.load(c["code"])
    g = per_gram(data, c)
    k = c["karats"]
    second = k[1] if len(k) > 1 else k[0]
    main = c["units"][0]
    region = next((r for r in REGIONS if c["code"] in r), [])
    data_faq = [
        (f"What is the gold price in {c['short']} today?",
         f"As of {stamp(data)}, 24K gold in {c['name']} is {money(g * KARATS['24K'], c)} per gram and "
         f"{money(g * KARATS['24K'] * UNITS[main][1], c)} per {UNITS[main][0].replace('1 ', '').lower()}, based on the live "
         f"international spot price of ${data['xau_usd']:,.2f} per ounce."),
        (f"What is the {second} gold rate in {c['short']} today?",
         f"{second} gold is {money(g * KARATS[second], c)} per gram today in {c['name']}, or "
         f"{money(g * KARATS[second] * UNITS[main][1], c)} per {UNITS[main][0].replace('1 ', '').lower()}."),
    ]
    body = f"""{intro_html(copy)}
<p><strong>Today in {escape(c['name'])}</strong> ({stamp(data)}): 24K gold is <strong>{money(g * KARATS['24K'], c)} per gram</strong>, {second} is <strong>{money(g * KARATS[second], c)}</strong>, and spot gold is ${data['xau_usd']:,.2f} per ounce.</p>
{tiles(data, c)}
{widget(data, c)}
<h2>Gold price in {escape(c['short'])} by weight</h2>
<p>From a single gram up to a full kilo, here is what gold costs in {c['currency']} for every popular weight and purity right now.</p>
{weights_table(data, c)}
<h2>Gold price calculator for {escape(c['short'])}</h2>
{calculator(c)}
{copy_sections(copy, 1)}
<h2>Silver price in {escape(c['short'])} today</h2>
{silver_widget(data, c)}
{copy_sections(copy, 2)}
<h2>Gold price in nearby countries</h2>
{country_links(region, c['code'])}
<p>See the <a href="{page_url(HUB_SLUG)}">live gold price in every country</a>, the <a href="{page_url(SILVER_SLUG)}">silver price today</a>, or the latest <a href="/search/label/Gold?max-results=12">gold market news</a>.</p>
{faq_html(faq_items(copy, data_faq))}
{disclaimer()}"""
    title = {
        "IN": "Gold Rate Today in India: 22K & 24K Price per 10 Grams",
        "PK": "Gold Rate in Pakistan Today: 24K & 22K Price per Tola",
        "BD": "Gold Price in Bangladesh Today: 22K Rate per Vori",
        "NP": "Gold Price in Nepal Today: Fine Gold Rate per Tola",
        "LK": "Gold Rate in Sri Lanka Today: 24K & 22K per Sovereign",
    }.get(c["code"], f"Gold Price in {c['short']} Today: {', '.join(k[:3])} Rate in {c['currency']}")
    desc = (f"Live gold price in {c['name']} today: 24K at {money(g * KARATS['24K'], c)} per gram. "
            f"{', '.join(k)} rates by weight in {c['currency']}, with a gold calculator.")
    return {"slug": country_slug(c), "title": title, "description": desc[:158], "html": body}


def build_hub(data):
    copy = gold_copy.load("hub")
    us = BY_CODE["US"]
    g = per_gram(data, us)
    usd_rows = "".join(
        f"<tr><th>{k}</th><td>{money(g * f, us)}</td><td>{money(g * f * 10, us)}</td>"
        f"<td>{money(g * f * GRAMS_PER_OUNCE, us)}</td><td>{money(g * f * 1000, us)}</td></tr>" for k, f in KARATS.items()
    )
    data_faq = [
        ("What is the gold price today?",
         f"As of {stamp(data)}, the spot price of gold is ${data['xau_usd']:,.2f} per troy ounce, or about "
         f"${g * 0.999:,.2f} per gram for 24K gold."),
    ]
    body = f"""{intro_html(copy)}
<p><strong>Right now</strong> ({stamp(data)}): spot gold is <strong>${data['xau_usd']:,.2f} per ounce</strong> and spot silver is ${data['xag_usd']:,.2f}. The live table below detects your country automatically; you can switch to any of {len(COUNTRIES)} currencies.</p>
{widget(data, us, auto=True)}
<h2>Gold price today in US dollars</h2>
{tiles(data, us)}
<div class="ra-gold-scroll"><table class="ra-gold-table"><thead><tr><th>Purity</th><th>1 Gram</th><th>10 Grams</th><th>1 Ounce</th><th>1 Kilogram</th></tr></thead><tbody>{usd_rows}</tbody></table></div>
<h2>Gold price by weight (USD)</h2>
{weights_table(data, us)}
<h2>Gold price calculator</h2>
{calculator(us)}
<h2>Gold price today by country</h2>
<p>Local units such as tola, sovereign and 10 grams, popular purities and buying guides for the biggest gold markets:</p>
{country_links()}
{copy_sections(copy, 1)}
{copy_sections(copy, 2)}
<p>Read the latest <a href="/search/label/Gold?max-results=12">gold news and analysis</a> or check the <a href="{page_url(SILVER_SLUG)}">silver price today</a>.</p>
{faq_html(faq_items(copy, data_faq))}
{disclaimer()}"""
    return {"slug": HUB_SLUG, "title": "Gold Price Today: Live Gold Rate per Gram, Ounce and Tola",
            "description": (f"Live gold price today: spot gold at ${data['xau_usd']:,.2f} per ounce. 24K, 22K, 21K "
                            f"and 18K gold rates by weight in {len(COUNTRIES)} currencies, with a gold calculator.")[:158],
            "html": body}


def build_silver(data):
    copy = gold_copy.load("silver")
    us = BY_CODE["US"]
    links = "".join(
        f'<a href="{page_url(country_slug(c))}">Silver in {escape(c["short"])} <small>{money(per_gram(data, c, "XAG") * 0.999, c)}/g</small></a>'
        for c in PAGE_COUNTRIES
    )
    data_faq = [
        ("What is the silver price today?",
         f"As of {stamp(data)}, the spot price of silver is ${data['xag_usd']:,.2f} per troy ounce, and the "
         f"gold-to-silver ratio is {data['xau_usd'] / data['xag_usd']:.1f}."),
    ]
    body = f"""{intro_html(copy)}
<p><strong>Right now</strong> ({stamp(data)}): spot silver is <strong>${data['xag_usd']:,.2f} per ounce</strong> and the gold-to-silver ratio is {data['xau_usd'] / data['xag_usd']:.1f}.</p>
{silver_widget(data, us)}
<h2>Silver price by weight (USD)</h2>
{weights_table(data, us, "XAG")}
<h2>Silver price today by country</h2>
<div class="ra-gold-links">{links}</div>
{copy_sections(copy, 1)}
{copy_sections(copy, 2)}
<p>Also see the <a href="{page_url(HUB_SLUG)}">live gold price today</a>.</p>
{faq_html(faq_items(copy, data_faq))}
{disclaimer()}"""
    return {"slug": SILVER_SLUG, "title": "Silver Price Today: Live Silver Spot Price per Ounce and Gram",
            "description": (f"Live silver price today: spot silver at ${data['xag_usd']:,.2f} per ounce. "
                            "999 fine and 925 sterling silver prices per gram, ounce and kilo by country.")[:158],
            "html": body}


def build_all():
    data = gold_data.update()
    OUT.mkdir(parents=True, exist_ok=True)
    pages = [build_hub(data), build_silver(data)] + [build_country(data, c) for c in PAGE_COUNTRIES]
    active_files = {f"{p['slug']}.html" for p in pages}
    for old_file in OUT.glob("*.html"):
        if old_file.name not in active_files:
            old_file.unlink()
    for p in pages:
        (OUT / f"{p['slug']}.html").write_text(p["html"], encoding="utf-8")
    manifest = [{k: p[k] for k in ("slug", "title", "description")} for p in pages]
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    return data, pages


def publish(pages, limit=None):
    """Create or refresh every gold page on Blogger. Stops at the first error (e.g. a page limit)."""
    from .blogger import Blogger

    blog = Blogger()
    done = []
    for p in pages[:limit]:
        try:
            page = blog.upsert_page(p["slug"], p["title"], p["html"])
        except RuntimeError as e:
            print(f"  STOPPED at {p['slug']}: {e}")
            break
        done.append(page["url"])
        print(f"  live: {page['url']}", flush=True)
        time.sleep(3)  # stay under Blogger's write rate limit
    return done


if __name__ == "__main__":
    import sys

    data, pages = build_all()
    if "--publish" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
        start = int(sys.argv[sys.argv.index("--start") + 1]) if "--start" in sys.argv else 0
        pages = pages[start:]
        urls = publish(pages, limit)
        print(f"Published {len(urls)} of {len(pages) if limit is None else limit} pages")
        sys.exit(0)
    print(f"Built {len(pages)} pages with gold at ${data['xau_usd']:,} -> {OUT}")
    for p in pages[:4]:
        print(f"  {p['slug']}: {p['title']} ({len(p['title'])} chars)")
