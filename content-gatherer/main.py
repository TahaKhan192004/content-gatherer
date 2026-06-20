#!/usr/bin/env python3
"""
Content Gathering Agent — main orchestrator.

Usage:
    python main.py              # Run once
    python main.py --schedule   # Run on a loop (every RUN_INTERVAL_HOURS)
    python main.py --dry-run    # Gather + process, print results, skip Supabase
"""
import argparse
import logging
import time
import json
from datetime import datetime, timezone

from config import RUN_INTERVAL_HOURS
from sources import (
    fetch_rss_feeds,
    fetch_hackernews,
    fetch_reddit,
    fetch_devto,
    fetch_arxiv,
    fetch_producthunt,
)
from processing import process_items
from storage import (
    get_client,
    store_content,
    store_ideas,
    log_run_start,
    log_run_end,
    log_run_error,
)

# ── Logging Setup ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Gather Phase ──────────────────────────────────────────

def gather_all() -> list[dict]:
    """Run all source fetchers and combine results."""
    all_items = []

    fetchers = [
        ("RSS Feeds", fetch_rss_feeds),
        ("Hacker News", fetch_hackernews),
        ("Reddit", fetch_reddit),
        ("DEV.to", fetch_devto),
        ("ArXiv", fetch_arxiv),
        ("Product Hunt", fetch_producthunt),
    ]

    for name, fetcher in fetchers:
        logger.info(f"─── Fetching: {name} ───")
        try:
            items = fetcher()
            all_items.extend(items)
            logger.info(f"    → {len(items)} items")
        except Exception as e:
            logger.error(f"    ✗ {name} failed: {e}")

    logger.info(f"\n{'='*50}")
    logger.info(f"Total raw items gathered: {len(all_items)}")
    return all_items


# ── Single Run ────────────────────────────────────────────

def run_once(dry_run: bool = False):
    """Execute one full gather → process → store cycle."""
    import config
    config.reload()  # Pull latest config from Supabase before each run
    start = datetime.now(timezone.utc)
    logger.info(f"\n{'='*50}")
    logger.info(f"🚀 Content Gathering Agent — Run started")
    logger.info(f"{'='*50}\n")

    # Phase 1: Gather
    raw_items = gather_all()

    # Phase 2: Process
    logger.info(f"\n─── Processing ───")
    processed_items, content_ideas = process_items(raw_items)

    logger.info(f"\n{'='*50}")
    logger.info(f"📊 Results Summary")
    logger.info(f"   Raw items gathered:  {len(raw_items)}")
    logger.info(f"   After processing:    {len(processed_items)}")
    logger.info(f"   Content ideas:       {len(content_ideas)}")
    logger.info(f"{'='*50}\n")

    # Show top items
    logger.info("🔥 Top 10 by relevance:")
    for i, item in enumerate(processed_items[:10], 1):
        logger.info(
            f"   {i:2d}. [{item['relevance_score']:2d}] "
            f"({item['source_type']}) {item['title'][:70]}"
        )

    if content_ideas:
        logger.info("\n💡 Content Ideas:")
        for idea in content_ideas:
            logger.info(f"   • [{idea['idea_type']}] {idea['title'][:70]}")
            logger.info(f"     Angle: {idea['angle'][:80]}")
            logger.info(f"     Formats: {', '.join(idea['formats'])}\n")

    # Phase 3: Store (skip if dry run)
    if dry_run:
        logger.info("DRY RUN — skipping Supabase storage")
        return

    try:
        client = get_client()
        run_id = log_run_start(client)

        stored_content = store_content(client, processed_items, run_id)
        stored_ideas = store_ideas(client, content_ideas, run_id)

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        stats = {
            "raw_count": len(raw_items),
            "processed_count": len(processed_items),
            "stored_count": stored_content,
            "ideas_count": stored_ideas,
            "elapsed_seconds": round(elapsed, 1),
        }
        log_run_end(client, run_id, stats)

        logger.info(f"\n✅ Stored {stored_content} items + {stored_ideas} ideas to Supabase")
        logger.info(f"   Run completed in {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"Storage failed: {e}")
        try:
            log_run_error(client, run_id, str(e))
        except Exception:
            pass


# ── Scheduled Loop ────────────────────────────────────────

def run_scheduled():
    """Run on a loop with configured interval."""
    logger.info(f"Scheduled mode: running every {RUN_INTERVAL_HOURS} hours")
    logger.info("Press Ctrl+C to stop\n")

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            break
        except Exception as e:
            logger.error(f"Run failed: {e}")

        next_run = RUN_INTERVAL_HOURS * 3600
        logger.info(f"\n⏳ Next run in {RUN_INTERVAL_HOURS} hours...")
        try:
            time.sleep(next_run)
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            break


# ── CLI ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Content Gathering Agent")
    parser.add_argument("--schedule", action="store_true", help="Run on a recurring loop")
    parser.add_argument("--dry-run", action="store_true", help="Gather + process only, skip Supabase")
    args = parser.parse_args()

    if args.schedule:
        run_scheduled()
    else:
        run_once(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
