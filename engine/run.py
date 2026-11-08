"""Run the newsroom once.

    python -m engine.run --count 3

Writes each article to output/<date>/<slug>/ (preview.html, post.html, article.json, cover.jpg).
"""
import argparse
import datetime as dt
import json
import sys
import time
from html import escape

from . import checker, config, editor, images, render, research, sources, writer

MAX_REVISIONS = 2
MAX_FAILURES = 3          # stop after this many failed stories in one run
BLOCK_FILE = config.DATA_DIR / "publish_block.json"
BLOCK_HOURS = 3           # after Blogger refuses a post, skip runs for this long


def blocked_recently():
    """True if Blogger refused a post less than BLOCK_HOURS ago (saves Gemini quota)."""
    if not BLOCK_FILE.exists():
        return False
    since = dt.datetime.fromisoformat(json.loads(BLOCK_FILE.read_text(encoding="utf-8"))["since"])
    return dt.datetime.utcnow() - since < dt.timedelta(hours=BLOCK_HOURS)


DEFER = "defer"  # good story, but its section is full this run: try again next run


def produce(story, gold, out_root, label_counts, label_cap, blog=None):
    docs = research.gather(story)
    # Thin stories are not marked as seen: they can be written later, once more outlets cover them
    if len(docs) < 2:
        print("   waiting: fewer than 2 readable sources")
        return DEFER
    source_words = sum(len(d["text"].split()) for d in docs)
    if source_words < config.MIN_SOURCE_WORDS:
        print(f"   waiting: only {source_words} words of source material (need {config.MIN_SOURCE_WORDS})")
        return DEFER
    story_plan = writer.plan(story, docs)
    if story_plan.get("skip"):
        print(f"   skipped by editor: {story_plan.get('angle', '')}")
        return None
    if label_counts.get(story_plan["label"], 0) >= label_cap:
        print(f"   deferred: {story_plan['label']} already has {label_cap} stories this run")
        return DEFER
    print(f"   [{story_plan['label']}] keyword: {story_plan.get('focus_keyword')} | sources: {len(docs)}")

    article = writer.write(story, docs, story_plan, gold)
    report = checker.review(article, docs)
    for _ in range(MAX_REVISIONS):
        if report["decision"] == "publish":
            break
        print(f"   revising {len(report['problems'])} problem(s)...")
        article = writer.revise(article, docs, report["problems"])
        report = checker.review(article, docs)

    folder = out_root / article["slug"][:80]
    folder.mkdir(parents=True, exist_ok=True)
    cover = images.cover_card(article["title"], article["label"], folder / "cover.jpg")
    photos = images.find_article_photos(story_plan, article, max_photos=2)
    photo = photos[0] if photos else None
    extra_photos = photos[1:] if len(photos) > 1 else []
    if photo:
        image_src, credit = photo["url"], photo["credit"]
    else:
        # Cover cards need public hosting (GitHub); until then online posts go without one
        image_src, credit = (images.hosted_url(cover) if blog else cover.name), None

    body = render.post_html(article, image_src, credit, extra_photos=extra_photos)
    (folder / "post.html").write_text(body, encoding="utf-8")
    (folder / "preview.html").write_text(render.preview_page(article, body, report), encoding="utf-8")
    label_counts[article["label"]] = label_counts.get(article["label"], 0) + 1

    if blog:
        draft = report["decision"] != "publish"
        post = blog.publish_post(article["title"], article["slug"], body, [article["label"]], draft=draft)
        article["url"] = post.get("url", "")
        if not draft and article["url"]:
            render.record_published_post(article)
        print(f"   published to Blogger as {'DRAFT' if draft else 'LIVE'}: {article['url'] or post['id']}")
    (folder / "article.json").write_text(json.dumps(
        {"article": article, "report": report, "photo": photo, "plan": story_plan,
         "story": {"headline": story["headline"], "score": story["score"], "sources": story["sources"]}},
        indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"   -> {report['decision'].upper()} | {article['word_count']} words | "
          f"photo: {'Wikimedia' if photo else 'cover card'} | {article['title']}")
    for p in report["problems"]:
        print(f"      ! {p}")
    return {"folder": folder, "article": article, "report": report}


def write_index(out_root, results):
    rows = "".join(
        f"<li><b style='color:{'#1a7f37' if r['report']['decision'] == 'publish' else '#b35900'}'>"
        f"{r['report']['decision'].upper()}</b> &middot; <a href='{r['folder'].name}/preview.html'>"
        f"{escape(r['article']['title'])}</a> ({r['article']['word_count']} words)</li>"
        for r in results
    )
    (out_root / "index.html").write_text(
        f"<!doctype html><meta charset='utf-8'><title>Red Atlas output</title>"
        f"<body style='font:18px/1.7 system-ui;max-width:800px;margin:30px auto'>"
        f"<h1 style='color:#C8102E'>Red Atlas News: generated articles</h1><ul>{rows}</ul></body>",
        encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--publish", action="store_true", help="send articles to Blogger")
    args = parser.parse_args()
    blog = None
    if args.publish:
        from .blogger import Blogger
        if blocked_recently():
            print(f"::warning::Blogger refused new posts less than {BLOCK_HOURS}h ago; skipping this run to save quota.")
            return 0
        blog = Blogger()
        print(f"Connected to Blogger: {blog.blog['name']}")

    started = time.time()
    print("Reporter: collecting news, trends and gold prices...")
    items = sources.fetch_headlines()
    trends = sources.fetch_trends()
    gold = sources.gold_snapshot()
    print(f"   {len(items)} headlines, {len(trends)} trending searches, gold ${gold.get('XAU', {}).get('price', '?')}")

    stories = editor.top_stories(items, trends, limit=args.count * 6)
    out_root = config.OUTPUT_DIR / dt.datetime.utcnow().strftime("%Y-%m-%d")
    out_root.mkdir(parents=True, exist_ok=True)
    seen = editor.load_seen()
    # Keep the site varied: no section gets more than about a third of a run
    label_cap = max(1, -(-args.count // 3))
    label_counts = {}

    from .blogger import PublishBlocked

    results = []
    failures = 0
    blocked = False
    for story in stories:
        if len(results) >= args.count:
            break
        print(f"\nStory (score {story['score']}, {len(story['sources'])} outlets): {story['headline']}")
        try:
            result = produce(story, gold, out_root, label_counts, label_cap, blog)
        except PublishBlocked as e:
            # Writing more articles that cannot be published only burns quota
            print(f"::warning::{e}. Stopping this run; next attempt in {BLOCK_HOURS}h.")
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            BLOCK_FILE.write_text(json.dumps({"since": dt.datetime.utcnow().isoformat(), "reason": str(e)[:300]}),
                                  encoding="utf-8")
            blocked = True
            break
        except Exception as e:  # one bad story must not stop the newsroom
            print(f"   failed: {type(e).__name__}: {e}")
            failures += 1
            if failures >= MAX_FAILURES:
                print(f"::warning::{failures} stories failed in a row; stopping this run.")
                break
            continue
        if blog and BLOCK_FILE.exists() and result and result != DEFER:
            BLOCK_FILE.unlink()  # publishing works again
        if result == DEFER:
            continue
        seen["urls"] += [i["url"] for i in story["items"]]
        seen["titles"].append(story["headline"])
        editor.save_seen(seen)
        if result:
            results.append(result)

    write_index(out_root, results)
    print(f"\nDone: {len(results)} articles in {time.time() - started:.0f}s -> {out_root / 'index.html'}")
    # A Blogger block is handled (paused and saved), so it is not a failed run
    return 0 if results or blocked else 1


if __name__ == "__main__":
    sys.exit(main())
