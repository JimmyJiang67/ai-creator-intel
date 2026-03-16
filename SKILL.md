---
name: ai-creator-intel
description: Use when the user wants an AI creator intelligence brief, especially Twitter/X watchlist monitoring, AI news scanning, AIGC competition tracking, or delivery-ready daily and weekly digests for Feishu or email. Covers AI builders, influencers, official company accounts, founders, operators, prompt trends, viral AIGC workflows, and contest opportunities.
---

# AI Creator Intel

## When to use

Use this skill when the user wants:

- a daily or weekly AI creator brief
- Twitter/X monitoring for AI builders, founders, or official AI accounts
- a high-signal watchlist for AI creator research
- prompt, workflow, or viral AIGC trend scanning from curated accounts
- delivery-ready summaries for Feishu or email

Do not use this skill for:

- broad web news research without a watchlist
- deep competitive analysis across many products
- fully automated account discovery as the main workflow

## V1 Scope

This v1 is watchlist-first, with structured source configs for news and AIGC contests.

Primary coverage:

- Twitter/X posts from curated Chinese and global AI accounts
- first-hand launches, builder workflows, product updates, prompts, and viral AIGC content
- AI news sources configured for product, model, research, and tool discovery
- AIGC competition tracking, with priority on official pages and creator-relevant contests
- creator-oriented briefing output

If not all source modules are available in a run, prioritize Twitter/X first, then news, then contests.

## Workflow

1. Read `config/twitter-watchlist.yaml` to get the account universe, tiering, and curation rationale.
2. Read `config/twitter-fetch-config.yaml` to determine fetch windows, filtering, scoring, deduplication, and briefing sections.
3. Read `config/news-sources.yaml` to determine which news sources to use for launch, product, and research coverage.
4. Read `config/contest-sources.yaml` to determine which contest aggregators and official pages to use.
5. Select the operating mode:
   - `daily_brief`
   - `weekly_review`
   - `manual_deep_dive`
6. Fetch Twitter/X posts using the configured provider order and tier policy.
   - For live watchlist mode, use `twitterapiio://watchlist` with `TWITTERAPI_IO_KEY` set in the environment.
   - For browser watchlist mode, use `xbrowser://watchlist` with `X_BROWSER_PROFILE_DIR` pointing to a persistent Playwright profile that is already logged into X.
   - To initialize that profile on a new machine, run `python3 scripts/init_x_browser_profile.py --profile-dir /path/to/x-profile`, log into X in the opened browser window, then export the printed `X_BROWSER_PROFILE_DIR`.
   - Browser mode should fetch `core + candidate`, keep `original + quote + repost`, exclude replies, and stop once the timeline crosses the last 24 hours or the scroll guardrail.
   - For local development and testing, use JSON files shaped like the bundled sample data.
7. Pull news items from configured primary and secondary sources.
   - For live default news mode, use `news://default`.
   - V1 live news currently prefers stable sources first: OpenAI RSS, Anthropic newsroom, Google DeepMind RSS, Perplexity Hub blog, Runway newsroom, ElevenLabs blog, Product Hunt feed, GitHub Trending, and Hacker News RSS.
   - Treat unsupported or challenge-heavy sites as configured-but-disabled until a source-specific parser exists.
8. Pull contest items from configured aggregator and official sources.
9. Keep original posts, quote posts, and thread roots; exclude reply-only and like-only activity unless the user explicitly requests them.
10. Score for first-hand signal, creator usefulness, novelty, reproducibility, and credibility.
11. Deduplicate overlapping items, preferring official, founder, and builder sources over second-hand commentary.
12. Classify the surviving items into briefing labels and sections.
13. Produce a delivery-ready brief with source links, why-it-matters notes, and suggested creator angles.

## Output Requirements

Default briefing structure:

1. `must_know_launches`
2. `builder_moves`
3. `creator_workflows`
4. `viral_aigc`
5. `watch_next`
6. `contest_opportunities`

For each selected item, include:

- source account
- concise summary
- why it matters for an AI creator
- suggested content angle
- direct source URL

For contest items, also include when available:

- organizer
- deadline
- prize or support level
- entry requirements
- official entry page

## Watchlist Rules

- Treat `core` accounts as the default production layer.
- Treat `candidate` accounts as lower-frequency observation accounts.
- Treat `scout` accounts as discovery seeds, not primary briefing sources.
- Do not depend on crawling a creator's live following page in the main loop.
- Prefer explicit watchlist files over dynamic social graph exploration.

## Editorial Rules

- Prioritize first-hand product and builder signals over second-hand commentary.
- Prefer reproducible prompts, workflows, demos, and shipping updates.
- Downrank vague hype, engagement farming, and generic motivation.
- Write for an AI content creator who wants usable insight, not just awareness.

Read `references/editorial-rules.md` when refining briefing tone, deciding whether an item is worth keeping, or choosing creator angles.

Read `references/source-strategy.md` when deciding which source to trust, how to resolve aggregator items to official pages, or how to expand source coverage without bloating the skill.
