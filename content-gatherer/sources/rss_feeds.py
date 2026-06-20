"""
RSS Feed Fetcher — parses all configured RSS feeds.
"""
import feedparser
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from config import RSS_FEEDS, MAX_CONTENT_AGE_DAYS

logger = logging.getLogger(__name__)


def _parse_date(entry) -> Optional[datetime]:
    """Extract published date from a feed entry."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, field, None) or entry.get(field)
        if parsed:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except Exception:
                continue
    return None


def _clean_html(raw: str) -> str:
    """Minimal HTML tag stripping without external deps."""
    import re
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:2000]  # cap length


def fetch_rss_feeds() -> list[dict]:
    """Fetch all RSS feeds and return normalized items."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_CONTENT_AGE_DAYS)
    items = []

    for category, feeds in RSS_FEEDS.items():
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                source_name = feed.feed.get("title", feed_url)

                for entry in feed.entries[:30]:  # cap per feed
                    pub_date = _parse_date(entry)
                    if pub_date and pub_date < cutoff:
                        continue

                    summary = ""
                    if hasattr(entry, "summary"):
                        summary = _clean_html(entry.summary)
                    elif hasattr(entry, "description"):
                        summary = _clean_html(entry.description)

                    items.append({
                        "source_type": "rss",
                        "source_name": source_name,
                        "source_category": category,
                        "title": entry.get("title", "Untitled"),
                        "url": entry.get("link", ""),
                        "summary": summary,
                        "published_at": pub_date.isoformat() if pub_date else None,
                        "author": entry.get("author", None),
                        "tags": [t.get("term", "") for t in entry.get("tags", [])],
                    })

                logger.info(f"✓ RSS: {source_name} — {len(feed.entries)} entries")
            except Exception as e:
                logger.warning(f"✗ RSS failed: {feed_url} — {e}")

    logger.info(f"Total RSS items: {len(items)}")
    return items
