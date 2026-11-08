"""Writer: plans the story's SEO angle, then writes the article with Gemini."""
import datetime as dt
import json
import re

from . import config, llm, sources


def _source_block(docs):
    return "\n\n".join(
        f"[SOURCE {i + 1}] {d['source']} | {d['title']}\nURL: {d['url']}\n{d['text']}"
        for i, d in enumerate(docs)
    )


def plan(story, docs):
    """Cheap call: section, focus keyword, people/places for images, or skip."""
    headlines = "\n".join(f"- {i['source']}: {i['title']}" for i in story["items"][:8])
    prompt = f"""You are the night editor of {config.SITE_NAME}, an English-language global news site
covering world news, gold, markets, economy, business and tech.

Headlines about one story:
{headlines}

Return JSON with:
- "skip": true only if this is celebrity gossip, sports results, or local crime with no wider significance
- "label": one of {config.LABELS}
- "focus_keyword": the natural 2-4 word phrase people type into Google for this story, lowercase
  (e.g. "kyiv missile attack", "gold price record", "fed rate cut"), not a list of keywords
- "main_entity": the single most important person, company, place or organization (exact name)
- "wikipedia_title": the English Wikipedia article title for main_entity, or "" if unsure
- "angle": one sentence on what makes this story matter to a global reader
- "sensitive": true for deaths, disasters, accidents, attacks or wars (no tourist or cheerful images)
- "visual_subjects": 2-3 concrete, photographable subjects for an archive photo that fits the story,
  2-5 words each, as they would be named on Wikimedia Commons. Name the real object, place or
  institution involved, never a bare country name and never the event itself. Examples:
  train crash in Egypt -> ["Egyptian National Railways train", "Ramses Station Cairo"];
  earthquake in central Japan -> ["Nagoya city skyline", "Japan Meteorological Agency"];
  Fed decision -> ["Federal Reserve Eccles Building", "Jerome Powell"]"""
    data, _ = llm.generate_json(prompt, config.MODELS_LIGHT)
    if data.get("label") not in config.LABELS:
        data["label"] = "World"
    return data


def write(story, docs, story_plan, gold):
    keyword = story_plan.get("focus_keyword", "")
    suggestions = sources.autocomplete(keyword) if keyword else []
    entity = story_plan.get("main_entity", "")
    if entity and entity.lower() not in keyword:
        # What people search about the main person/organisation too (secondary keywords)
        suggestions += [s for s in sources.autocomplete(entity.lower())[:5] if s not in suggestions]
    # Searches about past events ("egypt train crash 2019") would pull old facts into today's story
    this_year = dt.datetime.utcnow().year
    suggestions = [s for s in suggestions
                   if all(int(y) >= this_year for y in re.findall(r"\b(?:19|20)\d\d\b", s))]
    gold_line = ""
    if gold.get("XAU") and story_plan["label"] in ("Gold", "Markets", "Economy"):
        gold_line = f"Live spot gold right now: ${gold['XAU']['price']:,} per ounce (use only if relevant)."
    today = dt.datetime.utcnow().strftime("%B %d, %Y")

    prompt = f"""You are a senior correspondent at {config.SITE_NAME}. Write an original, in-depth news article
in clear American English for a global audience. Today is {today} (UTC).

STORY ANGLE: {story_plan.get('angle', '')}
SECTION: {story_plan['label']}
FOCUS KEYWORD: {keyword}
WHAT PEOPLE SEARCH ON GOOGLE (use naturally in subheadings and FAQ when relevant): {suggestions}
{gold_line}

SOURCE MATERIAL (your ONLY source of facts):
{_source_block(docs)}

STRICT RULES
1. Every fact, number, name, date and quote must come from the source material. Never invent or guess.
   Do not add colour or background that is not in the sources (no invented causes, places, reactions or details).
   If the sources do not say something, leave it out. A shorter accurate article beats a longer one.
2. Quotes: only copy quotes that appear word-for-word in the sources, and say who said them and which outlet reported it.
3. Do not copy sentences from the sources. Rewrite everything in your own words, and combine the sources into one complete picture.
4. Attribute key claims ("police told the BBC", "according to Al Jazeera").
5. If sources disagree (for example on casualty numbers), say so and give each figure with its source.
6. Neutral, factual tone. No hype, no clickbait, no speculation presented as fact.
7. Length: 900-1400 words in the body. Short paragraphs (2-4 sentences).
8. Add real value: background and context from the sources, why it matters, and what happens next.
9. Use the focus keyword naturally and with correct capitalization ("Pope Leo's Mass in Uruguay", not
   "pope leo uruguay mass"). Never paste it into a sentence where it does not read naturally. Readers first, Google second.

WRITE LIKE AN EXPERIENCED WIRE JOURNALIST, NOT LIKE AN AI
- Open with the single most newsworthy fact, stated plainly with names, numbers and place. No scene-setting.
- Concrete over abstract: exact figures, full names and titles at first mention, places, times, who said what.
- Vary sentence length; mix short punchy sentences with longer explanatory ones. No rhetorical questions.
- Headings are specific statements of fact ("Death toll rises to 4 as rescuers search Giza line"),
  never vague labels ("A Complex Situation", "Looking Ahead").
- Never use these words or phrases: delve, tapestry, testament, landscape (figurative), navigate/navigating,
  pivotal, crucial, robust, underscores, highlights the importance, a stark reminder, sends shockwaves,
  in the wake of, amid growing concerns, remains to be seen, only time will tell, it is worth noting,
  it is important to note, in today's fast-paced world, in conclusion, overall, all in all, game-changer,
  unprecedented (unless a source says it), plays a vital role.
- End on a concrete next step from the sources (a vote date, an investigation, a deadline), not a summary.

SEARCH (SEO) WITHOUT HURTING READABILITY
- Focus keyword: in the title, in the first 100 words, in one <h2>, and in the meta description.
- Work 3-6 of the Google search phrases above into headings, body and FAQ where they fit the facts.
- Name the main people, organisations and places in full at first mention (search engines match entities).
- FAQ questions must be phrased exactly the way people type them into Google.

STRUCTURE of "body_html" (HTML only: <p>, <h2>, <h3>, <ul>, <li>, <strong>, <blockquote>):
- Opening paragraph: the key facts (who, what, where, when) in 2-3 sentences, focus keyword included.
- 4-6 <h2> sections with specific, informative headings (not generic like "Background" alone).
- Include a "Key facts" <ul> list near the top.
- If relevant to money, markets or gold, a section on the economic or market impact.
- Final section: what happens next.
Do NOT include the title, FAQ or source list inside body_html.

Return JSON:
{{
 "title": "natural, grammatical news headline, max 65 characters, main name/topic near the start, specific and factual (not a keyword list)",
 "meta_description": "140-158 characters, includes the focus keyword, summarizes the news",
 "slug": "3-7 lowercase words joined by hyphens",
 "dek": "one-sentence subheadline that adds information beyond the title",
 "body_html": "...",
 "faq": [{{"q": "question people would search", "a": "2-3 sentence answer based only on sources"}}],
 "tags": ["3-6 specific topic tags, e.g. people, countries, companies"]
}}
FAQ: 3-5 items."""
    article, model = llm.generate_json(prompt, config.MODELS_WRITE, temperature=0.3)
    article["model"] = model
    _attach(article, story_plan, keyword, suggestions, docs)
    return article


def revise(article, docs, problems):
    """Fix what the checker flagged: remove unsupported claims, reword copied passages."""
    prompt = f"""You are the copy chief of {config.SITE_NAME}. The fact-checker and plagiarism check flagged
problems in this article. Fix ALL of them:
- Delete or correct every unsupported claim so that it matches the SOURCE MATERIAL exactly.
- Rewrite in your own words any passage that copies source wording.
- Do not add any new facts. Keep the same structure, tone and HTML tags.

PROBLEMS:
{chr(10).join('- ' + p for p in problems)}

SOURCE MATERIAL:
{_source_block(docs)}

ARTICLE JSON:
{json.dumps({k: article[k] for k in ('title', 'meta_description', 'slug', 'dek', 'body_html', 'faq', 'tags')}, ensure_ascii=False)}

Return the corrected article as JSON with the same keys."""
    fixed, model = llm.generate_json(prompt, config.MODELS_WRITE, temperature=0.2)
    for key in ("title", "meta_description", "slug", "dek", "body_html", "faq", "tags"):
        if fixed.get(key):
            article[key] = fixed[key]
    article["model"] = f"{article['model']} + revised by {model}"
    return article


def fix_keyword_case(article):
    """Search keywords are lowercase ("egypt train crash"); restore capitals for names the article
    itself writes with a capital ("Egypt"), wherever the model pasted the keyword verbatim."""
    keyword = article.get("focus_keyword", "")
    if not keyword:
        return article
    body = re.sub(r"<[^>]+>", " ", article.get("body_html", ""))
    words = []
    for w in keyword.split():
        proper = len(re.findall(r"\b" + re.escape(w.capitalize()) + r"\b", body))
        plain = len(re.findall(r"\b" + re.escape(w) + r"\b", body))
        words.append(w.capitalize() if proper > plain else w)
    cased = " ".join(words)
    if cased == keyword:
        return article
    pattern = re.compile(r"\b" + re.escape(keyword) + r"\b")
    for key in ("body_html", "meta_description", "dek"):
        if article.get(key):
            article[key] = pattern.sub(cased, article[key])
    for item in article.get("faq", []):
        item["q"], item["a"] = pattern.sub(cased, item["q"]), pattern.sub(cased, item["a"])
    return article


def _attach(article, story_plan, keyword, suggestions, docs):
    article["label"] = story_plan["label"]
    article["focus_keyword"] = keyword
    article["search_suggestions"] = suggestions
    article["sources"] = [{"name": d["source"], "title": d["title"], "url": d["url"]} for d in docs]
