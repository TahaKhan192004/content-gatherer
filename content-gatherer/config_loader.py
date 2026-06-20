"""
Config Loader — fetches all agent configuration from Supabase tables.
Falls back to hardcoded defaults when tables are empty or unreachable.
Cached per process; call get_config(refresh=True) to reload from Supabase.
"""
import json
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Hardcoded defaults (mirrors schema_config.sql seed data) ─

_DEFAULT_RSS_FEEDS: dict = {
    "ai_tech_news": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://venturebeat.com/category/ai/feed/",
        "https://ai.googleblog.com/feeds/posts/default?alt=rss",
        "https://openai.com/blog/rss.xml",
        "https://www.anthropic.com/rss.xml",
        "https://blog.google/technology/ai/rss/",
        "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",
        "https://www.oneusefulthing.org/feed",
        "https://bensbites.beehiiv.com/feed",
        "https://simonwillison.net/atom/everything/",
        "https://lilianweng.github.io/index.xml",
        "https://newsletter.theaiedge.io/feed",
        "https://news.google.com/rss/search?q=artificial+intelligence+tools&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Claude+AI+OR+ChatGPT+OR+AI+automation&hl=en-US&gl=US&ceid=US:en",
    ],
    "competitor_positioning": [
        "https://news.google.com/rss/search?q=%22AI+coaching%22+OR+%22AI+for+entrepreneurs%22&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=%22AI+course+creators%22+OR+%22AI+consultants%22&hl=en-US&gl=US&ceid=US:en",
        "https://medium.com/feed/tag/ai-tools",
        "https://medium.com/feed/tag/solopreneur",
        "https://medium.com/feed/tag/ai-automation",
    ],
    "audience_pain_points": [
        "https://medium.com/feed/tag/freelancing",
        "https://medium.com/feed/tag/content-creation",
        "https://medium.com/feed/tag/online-business",
        "https://medium.com/feed/tag/productivity",
        "https://news.google.com/rss/search?q=solopreneur+AI+tools+workflow&hl=en-US&gl=US&ceid=US:en",
    ],
}

_DEFAULT_RELEVANCE_KEYWORDS: dict = {
    "claude": 10, "anthropic": 8, "ai workflow": 9, "ai automation": 9,
    "prompt engineering": 8, "ai tools": 7, "ai agent": 8,
    "solopreneur": 7, "solo founder": 7, "one-person business": 7,
    "content creation": 6, "service business": 6, "consultant": 5,
    "freelancer": 5, "course creator": 6, "coaching business": 6,
    "productivity": 4, "automation": 5, "no-code": 5, "low-code": 5,
    "chatgpt": 5, "openai": 4, "gemini": 4, "llm": 5,
    "ai copywriting": 7, "ai content": 7, "ai marketing": 7,
    "overwhelm": 6, "burnout": 5, "too many tools": 6,
    "hiring": 4, "delegate": 5, "time saving": 5,
}

_DEFAULT_CATEGORY_RULES: dict = {
    "AI Tool Launch": ["launches", "released", "announces", "new feature", "update",
                       "now available", "introducing", "rolls out", "ships"],
    "AI Strategy & Trends": ["trend", "future", "prediction", "landscape", "market",
                              "industry", "forecast", "report", "state of"],
    "Workflow & Automation": ["workflow", "automate", "automation", "pipeline", "integrate",
                               "no-code", "n8n", "zapier", "make.com", "system"],
    "Content & Marketing": ["content", "marketing", "social media", "instagram", "linkedin",
                             "copywriting", "caption", "hook", "engagement", "audience"],
    "Solopreneur & Business": ["solopreneur", "founder", "freelance", "consultant", "client",
                                "revenue", "business", "coaching", "course", "offer"],
    "Prompt Engineering": ["prompt", "prompting", "chain of thought", "few-shot",
                            "system prompt", "instruction", "context window"],
    "Research & Papers": ["arxiv", "paper", "research", "study", "findings",
                           "benchmark", "evaluation", "model"],
    "Pain Point / Discussion": ["struggle", "problem", "help", "advice", "stuck",
                                 "overwhelm", "burnout", "frustrated", "confused"],
}


# ── Config dataclass ──────────────────────────────────────

@dataclass
class AgentConfig:
    rss_feeds: dict = field(default_factory=lambda: dict(_DEFAULT_RSS_FEEDS))
    hackernews_keywords: list = field(default_factory=lambda: [
        "claude", "anthropic", "chatgpt", "ai agent", "ai workflow",
        "ai automation", "llm", "prompt engineering", "ai tools",
        "solopreneur", "one-person business", "content creation ai",
    ])
    hackernews_max_stories: int = 100
    reddit_subreddits: list = field(default_factory=lambda: [
        "artificial", "MachineLearning", "ChatGPT", "ClaudeAI",
        "Entrepreneur", "solopreneur", "ContentCreation", "socialmedia", "smallbusiness",
    ])
    reddit_sort: str = "hot"
    reddit_limit: int = 25
    devto_tags: list = field(default_factory=lambda: ["ai", "machinelearning", "productivity", "automation"])
    devto_per_tag: int = 10
    arxiv_queries: list = field(default_factory=lambda: [
        "large language model agents",
        "AI workflow automation",
        "prompt engineering",
    ])
    arxiv_max_results: int = 5
    relevance_keywords: dict = field(default_factory=lambda: dict(_DEFAULT_RELEVANCE_KEYWORDS))
    category_rules: dict = field(default_factory=lambda: dict(_DEFAULT_CATEGORY_RULES))
    min_relevance_score: int = 3
    dedup_similarity_threshold: float = 0.75
    max_content_age_days: int = 7
    run_interval_hours: int = 6
    content_ideas_per_run: int = 5


# ── Supabase loader ───────────────────────────────────────

def _load_from_supabase() -> AgentConfig:
    """Pull config from Supabase tables. Returns defaults on any failure."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        logger.warning("SUPABASE_URL/KEY not set — using built-in defaults")
        return AgentConfig()

    try:
        from supabase import create_client
        client = create_client(url, key)
    except Exception as e:
        logger.warning(f"Supabase client init failed: {e} — using defaults")
        return AgentConfig()

    cfg = AgentConfig()

    # Scalar & list settings from agent_config table
    try:
        rows = client.table("agent_config").select("key, value").execute().data
        s = {r["key"]: r["value"] for r in rows}

        def _pick(key, default):
            return s[key] if key in s else default

        cfg.min_relevance_score        = int(_pick("min_relevance_score", cfg.min_relevance_score))
        cfg.dedup_similarity_threshold = float(_pick("dedup_similarity_threshold", cfg.dedup_similarity_threshold))
        cfg.max_content_age_days       = int(_pick("max_content_age_days", cfg.max_content_age_days))
        cfg.run_interval_hours         = int(_pick("run_interval_hours", cfg.run_interval_hours))
        cfg.content_ideas_per_run      = int(_pick("content_ideas_per_run", cfg.content_ideas_per_run))
        cfg.hackernews_max_stories     = int(_pick("hackernews_max_stories", cfg.hackernews_max_stories))
        cfg.reddit_sort                = str(_pick("reddit_sort", cfg.reddit_sort))
        cfg.reddit_limit               = int(_pick("reddit_limit", cfg.reddit_limit))
        cfg.devto_per_tag              = int(_pick("devto_per_tag", cfg.devto_per_tag))
        cfg.arxiv_max_results          = int(_pick("arxiv_max_results", cfg.arxiv_max_results))

        for list_key, attr in [
            ("hackernews_keywords", "hackernews_keywords"),
            ("reddit_subreddits",   "reddit_subreddits"),
            ("devto_tags",          "devto_tags"),
            ("arxiv_queries",       "arxiv_queries"),
        ]:
            if list_key in s:
                v = s[list_key]
                setattr(cfg, attr, v if isinstance(v, list) else json.loads(v))

        logger.info("agent_config loaded from Supabase")
    except Exception as e:
        logger.warning(f"agent_config load failed: {e}")

    # RSS feeds
    try:
        rows = client.table("rss_feed_sources").select("url, category").eq("is_active", True).execute().data
        if rows:
            feeds: dict = {}
            for r in rows:
                feeds.setdefault(r["category"], []).append(r["url"])
            cfg.rss_feeds = feeds
            logger.info(f"Loaded {len(rows)} RSS feeds from Supabase")
    except Exception as e:
        logger.warning(f"RSS feeds load failed: {e}")

    # Relevance keywords
    try:
        rows = client.table("relevance_keywords").select("keyword, weight").eq("is_active", True).execute().data
        if rows:
            cfg.relevance_keywords = {r["keyword"]: r["weight"] for r in rows}
            logger.info(f"Loaded {len(rows)} relevance keywords from Supabase")
    except Exception as e:
        logger.warning(f"Relevance keywords load failed: {e}")

    # Category rules
    try:
        rows = client.table("category_rules").select("category, keyword").eq("is_active", True).execute().data
        if rows:
            rules: dict = {}
            for r in rows:
                rules.setdefault(r["category"], []).append(r["keyword"])
            cfg.category_rules = rules
            logger.info(f"Loaded {len(rows)} category rules from Supabase")
    except Exception as e:
        logger.warning(f"Category rules load failed: {e}")

    return cfg


# ── Cache ─────────────────────────────────────────────────

_cache: AgentConfig | None = None


def get_config(refresh: bool = False) -> AgentConfig:
    """Return cached AgentConfig. Pass refresh=True to reload from Supabase."""
    global _cache
    if _cache is None or refresh:
        _cache = _load_from_supabase()
    return _cache
