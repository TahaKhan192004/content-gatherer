"""
Reddit Public API — no auth required.
Uses .json endpoint on subreddit pages.
"""
import httpx
import logging
from datetime import datetime, timezone
from config import REDDIT_BASE, REDDIT_SUBREDDITS, REDDIT_SORT, REDDIT_LIMIT

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "ContentGatherer/1.0 (research bot; no scraping)"
}


def fetch_reddit() -> list[dict]:
    """Fetch hot/top posts from configured subreddits."""
    items = []
    client = httpx.Client(timeout=15, headers=HEADERS)

    for sub in REDDIT_SUBREDDITS:
        try:
            url = f"{REDDIT_BASE}/r/{sub}/{REDDIT_SORT}.json?limit={REDDIT_LIMIT}"
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Reddit r/{sub}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                p = post.get("data", {})
                if p.get("stickied"):
                    continue

                pub_time = datetime.fromtimestamp(
                    p.get("created_utc", 0), tz=timezone.utc
                )
                selftext = (p.get("selftext") or "")[:1500]

                # Determine category from subreddit
                category = _subreddit_to_category(sub)

                items.append({
                    "source_type": "reddit",
                    "source_name": f"r/{sub}",
                    "source_category": category,
                    "title": p.get("title", ""),
                    "url": f"https://reddit.com{p.get('permalink', '')}",
                    "summary": selftext or p.get("title", ""),
                    "published_at": pub_time.isoformat(),
                    "author": p.get("author", None),
                    "tags": [sub],
                    "meta": {
                        "score": p.get("score", 0),
                        "comments": p.get("num_comments", 0),
                        "upvote_ratio": p.get("upvote_ratio", 0),
                        "subreddit": sub,
                    },
                })

            logger.info(f"✓ Reddit r/{sub}: {len(posts)} posts")
        except Exception as e:
            logger.warning(f"✗ Reddit r/{sub} failed: {e}")

    client.close()
    logger.info(f"Total Reddit items: {len(items)}")
    return items


def _subreddit_to_category(sub: str) -> str:
    """Map subreddit to content category."""
    mapping = {
        "artificial": "ai_tech_news",
        "MachineLearning": "ai_tech_news",
        "ChatGPT": "competitor_positioning",
        "ClaudeAI": "ai_tech_news",
        "Entrepreneur": "audience_pain_points",
        "solopreneur": "audience_pain_points",
        "ContentCreation": "audience_pain_points",
        "socialmedia": "audience_pain_points",
        "smallbusiness": "audience_pain_points",
    }
    return mapping.get(sub, "ai_tech_news")
