"""
Processing Pipeline — dedup, score, categorize, generate ideas.
All rule-based. Zero paid API calls.
"""
import hashlib
import re
import logging
from datetime import datetime, timezone
from collections import Counter
from config import (
    RELEVANCE_KEYWORDS,
    CATEGORY_RULES,
    MIN_RELEVANCE_SCORE,
    DEDUP_SIMILARITY_THRESHOLD,
    CONTENT_IDEAS_PER_RUN,
)

logger = logging.getLogger(__name__)


# ── Deduplication ─────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = re.sub(r"[^\w\s]", "", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _fingerprint(title: str) -> str:
    """Create a content fingerprint from normalized title."""
    words = sorted(set(_normalize(title).split()))
    return hashlib.md5(" ".join(words).encode()).hexdigest()


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two word sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def deduplicate(items: list[dict]) -> list[dict]:
    """Remove near-duplicate items based on title similarity."""
    seen_fps = {}
    seen_urls = set()
    unique = []

    for item in items:
        url = item.get("url", "")
        title = item.get("title", "")

        # Exact URL dedup
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Fingerprint dedup
        fp = _fingerprint(title)
        title_words = set(_normalize(title).split())

        is_dup = False
        for existing_fp, existing_words in seen_fps.items():
            if _jaccard(title_words, existing_words) > DEDUP_SIMILARITY_THRESHOLD:
                is_dup = True
                break

        if not is_dup:
            seen_fps[fp] = title_words
            unique.append(item)

    removed = len(items) - len(unique)
    if removed:
        logger.info(f"Dedup: removed {removed} duplicates, {len(unique)} remaining")
    return unique


# ── Relevance Scoring ─────────────────────────────────────

def score_relevance(item: dict) -> int:
    """Score an item's relevance to the AI Savvy CEO brand."""
    searchable = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    score = 0

    for keyword, weight in RELEVANCE_KEYWORDS.items():
        if keyword in searchable:
            score += weight

    # Engagement bonus (social proof signal)
    meta = item.get("meta", {})
    engagement = meta.get("score", 0) + meta.get("comments", 0) + meta.get("reactions", 0)
    if engagement > 500:
        score += 3
    elif engagement > 100:
        score += 2
    elif engagement > 20:
        score += 1

    return score


# ── Auto-Categorization ──────────────────────────────────

def categorize(item: dict) -> list[str]:
    """Assign categories based on keyword rules."""
    searchable = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    categories = []

    for category, keywords in CATEGORY_RULES.items():
        if any(kw in searchable for kw in keywords):
            categories.append(category)

    # Fallback: use source category
    if not categories:
        source_cat = item.get("source_category", "")
        fallback_map = {
            "ai_tech_news": "AI Strategy & Trends",
            "competitor_positioning": "Content & Marketing",
            "audience_pain_points": "Pain Point / Discussion",
        }
        categories.append(fallback_map.get(source_cat, "Uncategorized"))

    return categories


# ── Content Idea Generator ────────────────────────────────

def generate_content_ideas(items: list[dict]) -> list[dict]:
    """
    Generate content ideas from gathered items.
    Rule-based: pattern matching + templates.
    """
    ideas = []
    now = datetime.now(timezone.utc)

    # Strategy 1: High-engagement topics → "Here's what everyone is talking about"
    top_engagement = sorted(
        [i for i in items if i.get("meta", {}).get("score", 0) > 50],
        key=lambda x: x.get("meta", {}).get("score", 0),
        reverse=True,
    )[:3]

    for item in top_engagement:
        ideas.append({
            "idea_type": "trending_topic",
            "title": f"Trending: {item['title']}",
            "angle": "Break down this trending topic for your audience — what it means for solo founders using AI",
            "source_url": item.get("url"),
            "source_title": item.get("title"),
            "formats": ["Reel", "LinkedIn Post", "Carousel"],
            "generated_at": now.isoformat(),
        })

    # Strategy 2: Pain points from Reddit → "Your audience is asking this"
    pain_items = [
        i for i in items
        if i.get("source_type") == "reddit"
        and any(cat == "Pain Point / Discussion" for cat in categorize(i))
    ][:3]

    for item in pain_items:
        ideas.append({
            "idea_type": "audience_pain_point",
            "title": f"Your audience is asking: {item['title'][:80]}",
            "angle": "Address this real question/frustration from your target audience",
            "source_url": item.get("url"),
            "source_title": item.get("title"),
            "formats": ["Instagram Caption", "LinkedIn Post"],
            "generated_at": now.isoformat(),
        })

    # Strategy 3: New tool/product launches → "I tested this so you don't have to"
    launches = [
        i for i in items
        if any(cat == "AI Tool Launch" for cat in categorize(i))
    ][:2]

    for item in launches:
        ideas.append({
            "idea_type": "tool_review",
            "title": f"New AI tool alert: {item['title'][:60]}",
            "angle": "Quick take or 'I tested this' breakdown — does it help solo founders?",
            "source_url": item.get("url"),
            "source_title": item.get("title"),
            "formats": ["Reel", "Carousel"],
            "generated_at": now.isoformat(),
        })

    # Strategy 4: Keyword clustering → emerging themes
    all_text = " ".join(f"{i.get('title', '')} {' '.join(i.get('tags', []))}" for i in items).lower()
    word_freq = Counter(re.findall(r"\b[a-z]{4,}\b", all_text))
    # Remove common stop words
    for stop in ["this", "that", "with", "from", "have", "been", "will", "about", "just", "more", "they", "what", "your", "http", "https", "like", "some", "into"]:
        word_freq.pop(stop, None)

    trending_words = [w for w, c in word_freq.most_common(5) if c >= 3]
    if trending_words:
        ideas.append({
            "idea_type": "trend_cluster",
            "title": f"Emerging theme: {', '.join(trending_words[:3])}",
            "angle": f"These words keep appearing across sources this week: {', '.join(trending_words)}. There might be a content angle here.",
            "source_url": None,
            "source_title": None,
            "formats": ["Brainstorm", "LinkedIn Post", "Carousel"],
            "generated_at": now.isoformat(),
        })

    return ideas[:CONTENT_IDEAS_PER_RUN]


# ── Full Pipeline ─────────────────────────────────────────

def process_items(raw_items: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Run the full processing pipeline.
    Returns: (processed_items, content_ideas)
    """
    # Step 1: Deduplicate
    items = deduplicate(raw_items)

    # Step 2: Score & categorize
    for item in items:
        item["relevance_score"] = score_relevance(item)
        item["categories"] = categorize(item)
        item["processed_at"] = datetime.now(timezone.utc).isoformat()

    # Step 3: Filter low-relevance
    before = len(items)
    items = [i for i in items if i["relevance_score"] >= MIN_RELEVANCE_SCORE]
    logger.info(f"Relevance filter: {before} → {len(items)} items (min score: {MIN_RELEVANCE_SCORE})")

    # Step 4: Sort by relevance
    items.sort(key=lambda x: x["relevance_score"], reverse=True)

    # Step 5: Generate content ideas
    ideas = generate_content_ideas(items)
    logger.info(f"Generated {len(ideas)} content ideas")

    return items, ideas
