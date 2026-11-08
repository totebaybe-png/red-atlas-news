"""Build the Red Atlas News Blogger theme from the JetTheme v2.9 source.

Usage: python theme-build/build_theme.py
Reads  theme-source/core-main/jettheme-v2.xml
Writes Red-Atlas-Theme.xml (upload this file in Blogger > Theme > Restore)
"""
import json
import re
import sys
from xml.parsers import expat
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "theme-source" / "core-main" / "jettheme-v2.xml"
OUT = ROOT / "Red-Atlas-Theme.xml"
PARTS = Path(__file__).resolve().parent / "parts"


def replace_once(text, old, new):
    count = text.count(old)
    if count != 1:
        sys.exit(f"Expected exactly one match, found {count}: {old[:80]!r}")
    return text.replace(old, new)


def set_variable(text, name, value):
    pattern = re.compile(r'(<Variable name="' + re.escape(name) + r'"[^>]*? value=")[^"]*(")')
    new_text, count = pattern.subn(lambda m: m.group(1) + value + m.group(2), text)
    if count != 1:
        sys.exit(f"Variable {name!r} matched {count} times")
    return new_text


def replace_widget_settings(text, widget_id, settings):
    pattern = re.compile(
        r"(<b:widget id='" + widget_id + r"'[^>]*>\s*<b:widget-settings>).*?(</b:widget-settings>)",
        re.S,
    )
    body = "".join(
        f"\n      <b:widget-setting name='{k}'>{v}</b:widget-setting>" for k, v in settings
    )
    new_text, count = pattern.subn(lambda m: m.group(1) + body + "\n    " + m.group(2), text)
    if count != 1:
        sys.exit(f"Widget {widget_id} settings matched {count} times")
    return new_text


def link_list(items):
    settings = [("sorting", "NONE")]
    for i, (label, url) in enumerate(items):
        settings.append((f"text-{i}", label))
        settings.append((f"link-{i}", url))
    return settings


def part(name):
    return (PARTS / name).read_text(encoding="utf-8").strip()


def gold_script():
    """Gold widget code with the country list from the engine (one source of truth)."""
    sys.path.insert(0, str(ROOT))
    from engine.gold_countries import COUNTRIES, GRAMS_PER_OUNCE, KARATS, PAGE_COUNTRIES, UNITS, weights_for
    from engine.gold_pages import SILVER_PURITIES, country_slug, page_url

    cfg = {
        "oz": GRAMS_PER_OUNCE,
        "units": UNITS,
        "karats": KARATS,
        "silver": list(SILVER_PURITIES.items()),
        "countries": [dict({k: c[k] for k in ("code", "short", "currency", "symbol", "units", "karats", "zones")},
                           weights=weights_for(c)) for c in COUNTRIES],
        "hub": page_url("gold-price-today"),
        "pageFor": {c["code"]: page_url(country_slug(c)) if c in PAGE_COUNTRIES else page_url("gold-price-today")
                    for c in COUNTRIES},
    }
    return part("gold.js").replace("__RA_GOLD_CONFIG__", json.dumps(cfg, ensure_ascii=False, separators=(",", ":")))


def build():
    t = SRC.read_text(encoding="utf-8")

    # --- Brand settings (Blogger > Theme > Customize reads these) ---
    variables = {
        "tagline": "World News, Gold Prices &amp; Markets",
        "description": "Red Atlas News delivers breaking world news, live gold prices, and sharp market analysis. Fast, accurate, and independent.",
        "keycolor": "#C8102E",
        "body.text.color": "#2B2B2B",
        "posts.title.color": "#111111",
        "body.link.color": "#C8102E",
        "body.hover.color": "#9B0D23",
        "border.color": "#E6E6E6",
        "posts.text.color": "#C8102E",
        "logo.width": "230px",
        "logo.width.mobile": "180px",
        "header.bg": "#C8102E",
        "header.color": "#FFFFFF",
        "header.border": "#A50D26",
        "tabs.color": "#FFFFFF",
        "tabs.hover": "#FFFFFF",
        "tabs.selected.color": "#FFFFFF",
        "dropdown.bg": "#FFFFFF",
        "dropdown.color": "#222222",
        "dropdown.hover": "#C8102E",
        "dropdown.selected": "#C8102E",
        "footer.bg": "#111111",
        "footer.color": "#B5B5B5",
        "footer.link": "#E6E6E6",
        "footer.border": "#262626",
        "socket.bg": "#000000",
        "socket.color": "#9A9A9A",
        "posts.icons.color": "#C8102E",
        "labels.background.color": "#9B0D23",
    }
    for name, value in variables.items():
        t = set_variable(t, name, value)

    # --- Red Atlas CSS, appended to the theme skin ---
    t = replace_once(t, "]]></b:skin>", part("red-atlas.css") + "\n]]></b:skin>")

    # --- Layout editor labels ---
    t = t.replace("background-color: #f67938;", "background-color: #C8102E;")
    t = replace_once(t, 'content: "JetTheme Version 2.9";', 'content: "Red Atlas News Theme";')

    # --- Head: SEO, Google Discover, speed ---
    t = replace_once(
        t,
        "<meta content='width=device-width,initial-scale=1' name='viewport'/>",
        "<meta content='width=device-width,initial-scale=1' name='viewport'/>\n"
        "<meta content='max-image-preview:large, max-snippet:-1, max-video-preview:-1' name='robots'/>\n"
        "<link href='https://cdn.jsdelivr.net' rel='preconnect'/>\n"
        "<link href='https://s3.tradingview.com' rel='dns-prefetch'/>",
    )
    t = replace_once(
        t,
        "<meta expr:content='data:skin.vars.body_background' name='theme-color'/>",
        "<meta expr:content='data:skin.vars.keycolor' name='theme-color'/>",
    )
    t = replace_once(
        t,
        "<meta content='website' property='og:type'/>",
        "<meta expr:content='data:view.isPost ? &quot;article&quot; : &quot;website&quot;' property='og:type'/>",
    )
    for empty_meta in (
        "<meta content='' property='fb:app_id'/>\n",
        "<meta content='' property='article:author'/>\n",
        "<meta content='' name='twitter:site'/>\n",
        "<meta content='' name='twitter:creator'/>\n",
    ):
        t = replace_once(t, empty_meta, "")

    # --- NewsArticle schema: newsroom author + large images for Google Discover ---
    t = replace_once(
        t,
        """  &quot;author&quot;: {
    &quot;@type&quot;: &quot;Person&quot;,
    &quot;name&quot;: &quot;<data:post.author.name/>&quot;,
    &quot;url&quot;: &quot;<data:post.author.profileUrl/>&quot;
  },""",
        """  &quot;author&quot;: {
    &quot;@type&quot;: &quot;Organization&quot;,
    &quot;name&quot;: &quot;<data:post.author.name/>&quot;,
    &quot;url&quot;: &quot;<data:blog.canonicalHomepageUrl/>p/about.html&quot;
  },""",
    )
    t = replace_once(
        t,
        "  &quot;image&quot;: &quot;<data:post.featuredImage/>&quot;,",
        "<b:if cond='data:post.featuredImage'>"
        "  &quot;image&quot;: [&quot;<b:eval expr='resizeImage(data:post.featuredImage, 1200, &quot;16:9&quot;)'/>&quot;, "
        "&quot;<b:eval expr='resizeImage(data:post.featuredImage, 1200, &quot;4:3&quot;)'/>&quot;, "
        "&quot;<b:eval expr='resizeImage(data:post.featuredImage, 1200, &quot;1:1&quot;)'/>&quot;],"
        "</b:if>",
    )
    t = replace_once(
        t,
        "data:view.isHomepage ? &quot;Homepage &quot; + data:blog.title",
        "data:view.isHomepage ? data:blog.title + &quot; - World News, Gold Prices and Markets&quot;",
    )

    # --- Header: logo, no social icons, news menu ---
    t = replace_widget_settings(t, "HTML10", [("content", "<![CDATA[" + part("logo.svg") + "]]>")])
    t = replace_once(
        t,
        "<b:widget id='LinkList10' locked='true' title='Icons, Dark, Search'",
        "<b:widget id='LinkList10' locked='true' title='#Icons Dark Search'",
    )
    # Blogger skips rendering an empty LinkList, which would drop the search,
    # dark-mode and mobile-menu buttons; keep one link (hidden by #Icons).
    t = replace_widget_settings(t, "LinkList10", link_list([("rss", "/feeds/posts/default")]))

    def section(name):
        return f"/search/label/{name}?max-results=12"

    t = replace_widget_settings(t, "LinkList11", link_list([
        ("Home", "/"),
        ("World", section("World")),
        ("Gold", "/p/gold-price-today.html"),
        ("Gold", "#sub-start"),
        ("Gold Price Today", "/p/gold-price-today.html"),
        ("Silver Price Today", "/p/silver-price-today.html"),
        ("Gold Price in UAE", "/p/gold-price-in-uae.html"),
        ("Gold Rate in India", "/p/gold-price-in-india.html"),
        ("Gold Rate in Pakistan", "/p/gold-price-in-pakistan.html"),
        ("Gold Price in Saudi Arabia", "/p/gold-price-in-saudi-arabia.html"),
        ("Gold News", section("Gold")),
        ("Gold", "#sub-end"),
        ("Markets", section("Markets")),
        ("Economy", section("Economy")),
        ("Business", section("Business")),
        ("Tech", section("Tech")),
        ("More", "#"),
        ("More", "#sub-start"),
        ("About Us", "/p/about.html"),
        ("Contact", "/p/contact.html"),
        ("Editorial Policy", "/p/editorial-policy.html"),
        ("Privacy Policy", "/p/privacy-policy.html"),
        ("More", "#sub-end"),
    ]))

    # Market ticker above the header, breaking-news bar below it
    t = replace_once(
        t,
        "<header class='header-animate sticky-top",
        part("markets-bar.html") + "\n\n<header class='header-animate sticky-top",
    )
    t = replace_once(t, "</header>\n\n<!--Main Content-->", "</header>\n" + part("breaking-bar.html") + "\n\n<!--Main Content-->")

    # --- Homepage section blocks (World, Gold, Markets, Economy) ---
    t = replace_once(
        t,
        "<b:section class='pt-4' cond='data:view.isPost' id='before-post'",
        part("section-blocks-widget.xml") + "\n<b:section class='pt-4' cond='data:view.isPost' id='before-post'",
    )

    # --- Contact form, shown only on /p/contact.html ---
    t = replace_once(
        t,
        "<b:section class='d-none' cond='data:view.isPost' id='ads-post'",
        part("contact-form-widget.xml") + "\n<b:section class='d-none' cond='data:view.isPost' id='ads-post'",
    )

    # --- Empty ad slots (fill with AdSense code after approval) ---
    t = t.replace(
        "<![CDATA[<hr class=\"example-ads\"/>]]>",
        "<![CDATA[<!-- Ad slot: paste AdSense code here after approval -->]]>",
    )

    # --- Sidebar titles ---
    t = replace_once(t, "title='Popular Posts' type='PopularPosts'", "title='Most Read' type='PopularPosts'")
    t = replace_once(t, "title='Categories' type='Label'", "title='Sections' type='Label'")
    t = replace_once(t, "title='#Recent Post' type='HTML'", "title='#Latest News' type='HTML'")
    t = replace_once(t, 'data-title="Recent Post"', 'data-title="Latest News"')
    t = replace_once(t, "data-title='Related Post'", "data-title='Related Stories'")

    # --- Footer ---
    t = replace_widget_settings(t, "HTML21", [("content", "<![CDATA[" + part("footer-about.html") + "]]>")])
    t = replace_once(t, "title='Learn More' type='LinkList'", "title='Company' type='LinkList'")
    t = replace_widget_settings(t, "LinkList13", link_list([
        ("About Us", "/p/about.html"),
        ("Contact", "/p/contact.html"),
        ("Editorial Policy", "/p/editorial-policy.html"),
        ("Privacy Policy", "/p/privacy-policy.html"),
        ("Terms of Use", "/p/terms.html"),
        ("Disclaimer", "/p/disclaimer.html"),
    ]))
    t = replace_once(t, "title='Follow Us' type='LinkList'", "title='Sections' type='LinkList'")
    t = replace_widget_settings(t, "LinkList14", link_list([
        ("World", section("World")),
        ("Gold", section("Gold")),
        ("Markets", section("Markets")),
        ("Economy", section("Economy")),
        ("Business", section("Business")),
        ("Tech", section("Tech")),
    ]))
    t = replace_once(
        t,
        "<b:include name='JetSocial'/>\n        </b:includable>",
        "<b:include name='JetLinkList'/>\n        </b:includable>",
    )
    t = replace_once(t, "title='Newsletter' type='HTML'", "title='Market Data' type='HTML'")
    t = replace_widget_settings(t, "HTML22", [("content", "<![CDATA[" + part("footer-market-note.html") + "]]>")])
    t = replace_once(
        t,
        "<b:include name='JetFollowIt'/>\n    </b:includable>\n      </b:widget>\n    </b:section>",
        "<b:include name='JetHtml'/>\n    </b:includable>\n      </b:widget>\n    </b:section>",
    )
    t = replace_widget_settings(t, "HTML23", [(
        "content",
        "<![CDATA[Copyright &copy; <span id=\"ra-year\">2026</span> Red Atlas News. All rights reserved.]]>",
    )])

    # --- Scripts: section block template + tickers, run after page load ---
    t = replace_once(t, "function jtCallback(){", part("templates.js") + "\n\n" + gold_script() + "\n\nfunction jtCallback(){")

    OUT.write_text(t, encoding="utf-8")
    # Blogger accepts the undeclared xlink: prefix JetTheme uses, so check
    # well-formedness without namespace processing.
    expat.ParserCreate().Parse(OUT.read_bytes(), True)
    print(f"Built {OUT.name} ({OUT.stat().st_size:,} bytes), XML is well-formed")


if __name__ == "__main__":
    build()
