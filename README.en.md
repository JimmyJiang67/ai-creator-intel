# AI Creator Intel

An OpenClaw-oriented skill for AI creator intelligence across Twitter/X, AI news, and AIGC contests.

It is designed for creator-style daily or weekly briefs, with a strong bias toward:

- first-hand product and model launches
- builder and founder signals on Twitter/X
- reusable workflows, prompts, and viral AIGC content
- creator-relevant competition opportunities

## What It Does

This skill combines three streams into one brief:

1. Twitter/X watchlist monitoring
2. AI news aggregation and filtering
3. AIGC contest tracking

Default output sections:

- `must_know_launches`
- `builder_moves`
- `creator_workflows`
- `viral_aigc`
- `watch_next`
- `contest_opportunities`

## Current V1 Approach

The skill is intentionally watchlist-first.

- `Twitter/X` uses a curated watchlist, not broad discovery as the main loop
- `News` prefers official and stable sources first
- `Contests` prioritize creator-relevant aggregators and official pages

This keeps the output higher-signal than a generic AI news scraper.

## Included Sources

### Twitter/X

- Curated `core`, `candidate`, and `scout` account pools
- Browser-based watchlist mode for real production use
- Optional API mode if you want it later

### News

Live default news mode currently includes:

- OpenAI News
- Anthropic News
- Google DeepMind Blog
- Perplexity Hub Blog
- Runway News
- ElevenLabs Blog
- Product Hunt
- GitHub Trending
- Hacker News

### Contests

Live default contest workflow currently prioritizes:

- AIBetas AIGC events
- plus lower-priority contest discovery sources configured in `config/contest-sources.yaml`

## Repository Structure

```text
ai-creator-intel/
├── SKILL.md
├── README.md
├── README.en.md
├── agents/
├── assets/
├── config/
├── references/
├── sample-data/
├── scripts/
└── tests/
```

Key files:

- [`SKILL.md`](./SKILL.md): skill behavior and usage rules
- [`config/twitter-watchlist.yaml`](./config/twitter-watchlist.yaml): curated X accounts
- [`config/twitter-fetch-config.yaml`](./config/twitter-fetch-config.yaml): fetch and scoring policy
- [`config/news-sources.yaml`](./config/news-sources.yaml): news sources and priorities
- [`config/contest-sources.yaml`](./config/contest-sources.yaml): contest sources

## Quick Start

### 1. Validate configuration

```bash
python3 scripts/validate_configs.py
```

### 2. Run news only

```bash
python3 scripts/build_news_brief.py 'news://default' daily_brief
```

### 3. Run contests only

```bash
python3 scripts/build_contest_brief.py 'https://www.aibetas.com.cn/aigc-events' daily_brief --render
```

### 4. Run the full brief

```bash
python3 scripts/build_full_brief.py \
  --mode daily_brief \
  --twitter-source 'xbrowser://watchlist' \
  --news-source 'news://default' \
  --contest-source 'https://www.aibetas.com.cn/aigc-events' \
  --render
```

## Twitter/X Setup

For production use, the recommended path is browser mode.

Initialize a persistent logged-in X profile:

```bash
python3 scripts/init_x_browser_profile.py --profile-dir /path/to/x-profile
```

Then export:

```bash
export X_BROWSER_PROFILE_DIR="/path/to/x-profile"
```

Browser mode currently:

- reads `core + candidate`
- keeps `original + quote + repost`
- excludes replies
- stops after crossing the last 24 hours or a scroll guardrail

## Development Notes

This repository includes:

- sample payloads for local development
- parser and briefing scripts
- tests for Twitter/X, news, contests, and full brief assembly

Run the test suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Production Trial

Before wiring Feishu or email delivery, run the production checklist:

- [`references/production-trial-checklist.md`](./references/production-trial-checklist.md)

Recommended first trial:

1. Twitter/X only
2. News only
3. Contests only
4. Full brief render

Only connect delivery after the local combined brief looks useful.

## Known V1 Limits

- Twitter/X depends on a browser session or a third-party API
- Some contest entries still have sparse metadata
- News filtering is tuned for creator usefulness, not exhaustive coverage
- Source expansion is intentionally conservative to avoid a noisy brief

## License

MIT. See [`LICENSE`](LICENSE).
