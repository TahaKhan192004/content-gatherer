"""
Configuration for the Content Gathering Agent.
All values load dynamically from Supabase on startup.
Call reload() to refresh within a long-running process.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Supabase credentials stay in env — they are secrets, not config
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# Google Sheets — fixed target; auth via env secrets (never commit these)
GOOGLE_SPREADSHEET_ID = "1A-MF9MdQTrvcu4ZlEYUH-agdTg7CY0qXa_HBPh3F80c"
GOOGLE_WORKSHEET_NAME = "content gathered"
GOOGLE_CREDS_JSON: str = os.getenv("GOOGLE_CREDS_JSON", "")
GOOGLE_TOKEN_JSON: str = os.getenv("GOOGLE_TOKEN_JSON", "")
GOOGLE_SHEETS_ENABLED: bool = os.getenv("GOOGLE_SHEETS_ENABLED", "true").lower() in (
    "true", "1", "yes",
)

# Static API base URLs (not configurable — no dashboard benefit)
HACKERNEWS_API  = "https://hacker-news.firebaseio.com/v0"
REDDIT_BASE     = "https://www.reddit.com"
DEVTO_API       = "https://dev.to/api/articles"
ARXIV_API       = "http://export.arxiv.org/api/query"
PRODUCTHUNT_RSS = "https://www.producthunt.com/feed"

# ── Dynamic config (loaded from Supabase) ─────────────────

from config_loader import get_config as _get_config


def _apply(cfg) -> None:
    """Write config values into this module's namespace."""
    m = sys.modules[__name__]
    m.RSS_FEEDS                  = cfg.rss_feeds
    m.HACKERNEWS_KEYWORDS        = cfg.hackernews_keywords
    m.HACKERNEWS_MAX_STORIES     = cfg.hackernews_max_stories
    m.REDDIT_SUBREDDITS          = cfg.reddit_subreddits
    m.REDDIT_SORT                = cfg.reddit_sort
    m.REDDIT_LIMIT               = cfg.reddit_limit
    m.DEVTO_TAGS                 = cfg.devto_tags
    m.DEVTO_PER_TAG              = cfg.devto_per_tag
    m.ARXIV_QUERIES              = cfg.arxiv_queries
    m.ARXIV_MAX_RESULTS          = cfg.arxiv_max_results
    m.RELEVANCE_KEYWORDS         = cfg.relevance_keywords
    m.CATEGORY_RULES             = cfg.category_rules
    m.MIN_RELEVANCE_SCORE        = cfg.min_relevance_score
    m.DEDUP_SIMILARITY_THRESHOLD = cfg.dedup_similarity_threshold
    m.MAX_CONTENT_AGE_DAYS       = cfg.max_content_age_days
    m.RUN_INTERVAL_HOURS         = cfg.run_interval_hours
    m.CONTENT_IDEAS_PER_RUN      = cfg.content_ideas_per_run


def reload() -> None:
    """Re-fetch config from Supabase and update all module globals."""
    _apply(_get_config(refresh=True))


# Load on first import
_apply(_get_config())
