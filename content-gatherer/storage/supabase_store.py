"""
Supabase Storage — stores gathered content, ideas, and run logs.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)


def get_client() -> Client:
    """Initialize Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _content_hash(item: dict) -> str:
    """Generate a unique hash for dedup in DB."""
    key = f"{item.get('url', '')}{item.get('title', '')}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


# ── Store Content ─────────────────────────────────────────

def store_content(client: Client, items: list[dict], run_id: str) -> int:
    """
    Upsert content items into the `gathered_content` table.
    Returns count of new items inserted.
    """
    inserted = 0

    for item in items:
        content_hash = _content_hash(item)

        row = {
            "content_hash": content_hash,
            "run_id": run_id,
            "source_type": item.get("source_type"),
            "source_name": item.get("source_name"),
            "source_category": item.get("source_category"),
            "title": item.get("title", "")[:500],
            "url": item.get("url", ""),
            "summary": item.get("summary", "")[:3000],
            "published_at": item.get("published_at"),
            "author": item.get("author"),
            "tags": item.get("tags", []),
            "categories": item.get("categories", []),
            "relevance_score": item.get("relevance_score", 0),
            "meta": item.get("meta", {}),
            "processed_at": item.get("processed_at"),
        }

        try:
            client.table("gathered_content").upsert(
                row, on_conflict="content_hash"
            ).execute()
            inserted += 1
        except Exception as e:
            logger.debug(f"Upsert failed for '{item.get('title', '')[:40]}': {e}")

    logger.info(f"Stored {inserted}/{len(items)} content items")
    return inserted


# ── Store Content Ideas ───────────────────────────────────

def store_ideas(client: Client, ideas: list[dict], run_id: str) -> int:
    """Store generated content ideas."""
    inserted = 0

    for idea in ideas:
        row = {
            "run_id": run_id,
            "idea_type": idea.get("idea_type"),
            "title": idea.get("title", "")[:500],
            "angle": idea.get("angle", ""),
            "source_url": idea.get("source_url"),
            "source_title": idea.get("source_title"),
            "formats": idea.get("formats", []),
            "status": "new",
            "generated_at": idea.get("generated_at"),
        }

        try:
            client.table("content_ideas").insert(row).execute()
            inserted += 1
        except Exception as e:
            logger.debug(f"Idea insert failed: {e}")

    logger.info(f"Stored {inserted}/{len(ideas)} content ideas")
    return inserted


# ── Run Logging ───────────────────────────────────────────

def log_run_start(client: Client) -> str:
    """Log a new run and return the run_id."""
    now = datetime.now(timezone.utc).isoformat()
    result = client.table("agent_runs").insert({
        "started_at": now,
        "status": "running",
    }).execute()

    run_id = result.data[0]["id"]
    logger.info(f"Run started: {run_id}")
    return run_id


def log_run_end(client: Client, run_id: str, stats: dict):
    """Update run record with results."""
    client.table("agent_runs").update({
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "stats": stats,
    }).eq("id", run_id).execute()
    logger.info(f"Run completed: {run_id}")


def log_run_error(client: Client, run_id: str, error: str):
    """Log run failure."""
    client.table("agent_runs").update({
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "stats": {"error": error},
    }).eq("id", run_id).execute()
    logger.warning(f"Run failed: {run_id}")
