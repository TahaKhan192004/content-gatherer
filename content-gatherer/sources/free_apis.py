"""
DEV.to API — free, no auth for reading.
ArXiv API — free, open access research papers.
Product Hunt — RSS feed.
"""
import httpx
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from config import (
    DEVTO_API, DEVTO_TAGS, DEVTO_PER_TAG,
    ARXIV_API, ARXIV_QUERIES, ARXIV_MAX_RESULTS,
    PRODUCTHUNT_RSS,
)
import feedparser

logger = logging.getLogger(__name__)


# ── DEV.to ────────────────────────────────────────────────

def fetch_devto() -> list[dict]:
    """Fetch recent articles from DEV.to by tag."""
    items = []
    client = httpx.Client(timeout=15)

    for tag in DEVTO_TAGS:
        try:
            resp = client.get(
                DEVTO_API,
                params={"tag": tag, "per_page": DEVTO_PER_TAG, "top": 7},
            )
            articles = resp.json()

            for a in articles:
                items.append({
                    "source_type": "devto",
                    "source_name": "DEV.to",
                    "source_category": "ai_tech_news",
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "summary": a.get("description", "")[:1000],
                    "published_at": a.get("published_at"),
                    "author": a.get("user", {}).get("name"),
                    "tags": a.get("tag_list", []),
                    "meta": {
                        "reactions": a.get("positive_reactions_count", 0),
                        "comments": a.get("comments_count", 0),
                        "reading_time": a.get("reading_time_minutes", 0),
                    },
                })

            logger.info(f"✓ DEV.to [{tag}]: {len(articles)} articles")
        except Exception as e:
            logger.warning(f"✗ DEV.to [{tag}] failed: {e}")

    client.close()
    return items


# ── ArXiv ─────────────────────────────────────────────────

def fetch_arxiv() -> list[dict]:
    """Fetch recent papers from ArXiv API."""
    items = []
    client = httpx.Client(timeout=20)

    for query in ARXIV_QUERIES:
        try:
            resp = client.get(
                ARXIV_API,
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": ARXIV_MAX_RESULTS,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                },
            )

            ns = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(resp.text)

            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                published = entry.find("atom:published", ns)
                link = entry.find("atom:id", ns)
                authors = entry.findall("atom:author/atom:name", ns)

                items.append({
                    "source_type": "arxiv",
                    "source_name": "ArXiv",
                    "source_category": "ai_tech_news",
                    "title": title.text.strip() if title is not None else "",
                    "url": link.text.strip() if link is not None else "",
                    "summary": (summary.text.strip()[:1500]) if summary is not None else "",
                    "published_at": published.text if published is not None else None,
                    "author": authors[0].text if authors else None,
                    "tags": ["research", query],
                })

            logger.info(f"✓ ArXiv [{query}]: found papers")
        except Exception as e:
            logger.warning(f"✗ ArXiv [{query}] failed: {e}")

    client.close()
    return items


# ── Product Hunt (RSS) ────────────────────────────────────

def fetch_producthunt() -> list[dict]:
    """Fetch Product Hunt RSS feed for new AI products."""
    items = []
    try:
        feed = feedparser.parse(PRODUCTHUNT_RSS)
        for entry in feed.entries[:20]:
            title_lower = entry.get("title", "").lower()
            # Only keep AI-related launches
            if not any(kw in title_lower for kw in ["ai", "gpt", "llm", "automat", "content", "writing"]):
                continue

            items.append({
                "source_type": "producthunt",
                "source_name": "Product Hunt",
                "source_category": "competitor_positioning",
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", "")[:1000],
                "published_at": entry.get("published"),
                "author": None,
                "tags": ["product_launch", "ai"],
            })

        logger.info(f"✓ Product Hunt: {len(items)} AI launches")
    except Exception as e:
        logger.warning(f"✗ Product Hunt failed: {e}")

    return items
