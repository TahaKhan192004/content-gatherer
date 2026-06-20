# Content Gathering Agent

A standalone, agentic content gathering system for AI Savvy CEO. Zero paid API dependencies. Zero scraping. 100% RSS feeds + free public APIs → Supabase.

## What It Does

Every run, the agent:

1. **Gathers** content from 6 source types (30+ feeds/endpoints)
2. **Deduplicates** using URL + title similarity (Jaccard)
3. **Scores** relevance against your brand keywords (weighted)
4. **Categorizes** into 8 auto-detected categories
5. **Generates content ideas** from patterns (trending, pain points, launches, theme clusters)
6. **Stores** everything in Supabase with full metadata

## Sources (All Free)

| Source | What You Get | Auth? |
|--------|-------------|-------|
| RSS Feeds | TechCrunch, Verge, Wired, Anthropic, OpenAI, Substacks, Google News, Medium tags | None |
| Hacker News | Top stories filtered by AI/solopreneur keywords | None |
| Reddit | Hot posts from r/ClaudeAI, r/solopreneur, r/Entrepreneur, etc. | None |
| DEV.to | Articles tagged AI, automation, productivity | None |
| ArXiv | Latest LLM/agent research papers | None |
| Product Hunt | New AI product launches (RSS) | None |

## Supabase Tables

| Table | Purpose |
|-------|---------|
| `gathered_content` | Every item with source, score, categories, engagement metrics |
| `content_ideas` | Auto-generated content angles with suggested formats |
| `agent_runs` | Execution log with timing and stats |

Plus 4 pre-built **views**: `top_unused_content`, `new_content_ideas`, `source_stats`, `run_history`

---

## Setup (5 minutes)

### 1. Supabase

- Go to [supabase.com](https://supabase.com) → create a project (free tier works)
- Open **SQL Editor** → paste the contents of `schema.sql` → run
- Go to **Project Settings → API** → copy your project URL and anon key

### 2. Local Setup

```bash
# Clone / download the project
cd content-gatherer

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your Supabase URL and key
```

### 3. Run

```bash
# Dry run (gather + process, prints results, skips Supabase)
python main.py --dry-run

# Full run (gather + process + store to Supabase)
python main.py

# Scheduled mode (runs every 6 hours)
python main.py --schedule
```

---

## Customization

### Add/Remove RSS Feeds
Edit `config.py` → `RSS_FEEDS` dict. Organized by category.

### Change Relevance Keywords
Edit `config.py` → `RELEVANCE_KEYWORDS`. Higher weight = more relevant to your brand.

### Add Subreddits
Edit `config.py` → `REDDIT_SUBREDDITS` and update the category mapping in `sources/reddit.py`.

### Adjust Filters
- `MIN_RELEVANCE_SCORE` — items below this get dropped (default: 3)
- `MAX_CONTENT_AGE_DAYS` — ignore content older than this (default: 7)
- `DEDUP_SIMILARITY_THRESHOLD` — how similar titles must be to count as duplicates (default: 0.75)

### Add New Category Rules
Edit `config.py` → `CATEGORY_RULES` dict. Each category has a list of trigger keywords.

---

## Architecture

```
main.py (orchestrator)
  │
  ├── sources/           ← Gather phase
  │   ├── rss_feeds.py       30+ RSS feeds
  │   ├── hackernews.py      HN Firebase API
  │   ├── reddit.py          Reddit JSON (no auth)
  │   └── free_apis.py       DEV.to + ArXiv + Product Hunt
  │
  ├── processing/        ← Intelligence phase
  │   └── engine.py
  │       ├── deduplicate()           Jaccard + URL dedup
  │       ├── score_relevance()       Weighted keyword scoring
  │       ├── categorize()            Rule-based auto-tagging
  │       └── generate_content_ideas() Pattern-based idea gen
  │
  └── storage/           ← Store phase
      └── supabase_store.py
          ├── store_content()    Upsert to gathered_content
          ├── store_ideas()      Insert to content_ideas
          └── log_run_*()        Execution tracking
```

## Running on a Server

For always-on scheduled runs, deploy to any cheap VPS or use:

- **Railway** / **Render** — run as a worker process with `python main.py --schedule`
- **GitHub Actions** — set up a cron workflow (free for public repos)
- **Your own machine** — use `cron` or `pm2` to keep it running

### GitHub Actions Example

Create `.github/workflows/gather.yml`:

```yaml
name: Content Gather
on:
  schedule:
    - cron: '0 */6 * * *'  # every 6 hours
  workflow_dispatch:        # manual trigger

jobs:
  gather:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```

---

## License

Private use. Built for AI Savvy CEO.
