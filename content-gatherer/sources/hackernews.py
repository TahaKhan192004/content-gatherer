"""
Hacker News API — free, no auth needed.
Scans top/new stories for relevant keywords.
"""
import httpx
import logging
from datetime import datetime, timezone
from config import HACKERNEWS_API, HACKERNEWS_KEYWORDS, HACKERNEWS_MAX_STORIES

logger = logging.getLogger(__name__)


def fetch_hackernews() -> list[dict]:
    """Fetch top HN stories and filter by relevance keywords."""
    items = []
    client = httpx.Client(timeout=15)

    try:
        # Get top story IDs
        resp = client.get(f"{HACKERNEWS_API}/topstories.json")
        story_ids = resp.json()[:HACKERNEWS_MAX_STORIES]

        for sid in story_ids:
            try:
                story = client.get(f"{HACKERNEWS_API}/item/{sid}.json").json()
                if not story or story.get("type") != "story":
                    continue

                title = story.get("title", "").lower()
                text = story.get("text", "") or ""

                # Keyword match filter
                searchable = f"{title} {text.lower()}"
                matched = [kw for kw in HACKERNEWS_KEYWORDS if kw in searchable]
                if not matched:
                    continue

                pub_time = datetime.fromtimestamp(
                    story.get("time", 0), tz=timezone.utc
                )

                items.append({
                    "source_type": "hackernews",
                    "source_name": "Hacker News",
                    "source_category": "ai_tech_news",
                    "title": story.get("title", ""),
                    "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    "summary": text[:1000] if text else f"HN discussion ({story.get('descendants', 0)} comments)",
                    "published_at": pub_time.isoformat(),
                    "author": story.get("by", None),
                    "tags": matched,
                    "meta": {
                        "score": story.get("score", 0),
                        "comments": story.get("descendants", 0),
                        "hn_id": sid,
                    },
                })
            except Exception as e:
                logger.debug(f"HN item {sid} skipped: {e}")

        logger.info(f"✓ Hacker News: {len(items)} relevant stories")
    except Exception as e:
        logger.warning(f"✗ Hacker News failed: {e}")
    finally:
        client.close()

    return items
