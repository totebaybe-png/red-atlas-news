"""Fact checker: an AI audit against the sources plus hard rules. Decides publish vs draft."""
import re

from . import config, llm
from .writer import _source_block

BANNED = ["as an ai", "delve", "in today's fast-paced", "it is worth noting", "in conclusion",
          "language model", "i cannot", "[source", "lorem ipsum"]


def _plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _ngrams(text, n=8):
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def rule_checks(article, docs):
    problems = []
    body = _plain(article.get("body_html", ""))
    words = len(body.split())
    article["word_count"] = words
    if words < config.MIN_WORDS:
        problems.append(f"Too short: {words} words (minimum {config.MIN_WORDS})")
    if len(article.get("title", "")) > 75:
        problems.append(f"Title too long: {len(article['title'])} characters")
    if not 110 <= len(article.get("meta_description", "")) <= 170:
        problems.append("Meta description length outside 110-170 characters")
    if article.get("body_html", "").count("<h2") < 3:
        problems.append("Fewer than 3 section headings")
    lowered = body.lower()
    problems += [f"Banned phrase: '{p}'" for p in BANNED if p in lowered]

    # Copy check: share of 8-word sequences lifted from any single source
    mine = _ngrams(body)
    if mine:
        worst = max((len(mine & _ngrams(d["text"])) / len(mine) for d in docs), default=0)
        article["copied_ratio"] = round(worst, 3)
        if worst > 0.08:
            problems.append(f"Too close to a source: {worst:.0%} of 8-word phrases copied")
    return problems


def fact_check(article, docs):
    prompt = f"""You are a strict fact-checker. Compare the ARTICLE with the SOURCE MATERIAL.

SOURCE MATERIAL:
{_source_block(docs)}

ARTICLE:
TITLE: {article.get('title')}
DEK: {article.get('dek')}
BODY: {_plain(article.get('body_html', ''))}
FAQ: {article.get('faq')}

List every claim in the article (number, name, date, place, quote, event) that is NOT supported by the
sources or contradicts them. Ignore general background knowledge that is common and uncontroversial.
Quotes must match the sources word for word.

Return JSON: {{"unsupported": [{{"claim": "...", "severity": "high|low", "reason": "..."}}], "summary": "one line"}}
Severity "high" = wrong or invented fact, number, name or quote; a statement credited to the wrong person
or outlet; details from different sources merged into something no source said; internal contradictions
(e.g. "five regions" followed by a list of seven). "low" = only minor wording or emphasis."""
    data, model = llm.generate_json(prompt, config.MODELS_WRITE, 0.1)
    data["model"] = model
    return data


def review(article, docs):
    problems = rule_checks(article, docs)
    audit = fact_check(article, docs)
    high = [u for u in audit.get("unsupported", []) if u.get("severity") == "high"]
    problems += [f"Unsupported claim: {u.get('claim')} ({u.get('reason')})" for u in high]
    return {
        "decision": "publish" if not problems else "draft",
        "problems": problems,
        "fact_check": audit,
    }
