# Source Strategy

## Principle

The skill should not treat all sources equally.

Use source roles:

- discover
- verify
- enrich
- distribute

## News

For AI news:

1. Discover from Twitter/X watchlists, Product Hunt, GitHub Trending, Hacker News, and media sources.
2. Verify major product or model claims on official blogs, release pages, or company posts.
3. Enrich with context from trusted media or linked articles.
4. Write the brief for creator usefulness, not exhaustive coverage.

## Twitter/X

For Twitter/X:

1. Default to explicit watchlists, not open-ended discovery.
2. In live mode, use the configured watchlist with `twitterapiio://watchlist`.
3. Require `TWITTERAPI_IO_KEY` in the environment before attempting live fetches.
4. Treat Twitter/X as a discovery and first-hand signal layer, then verify major claims through official or linked sources where possible.

## Contests

For AIGC contests:

1. Discover from trusted aggregators such as AIBetas and community platforms.
2. Resolve to official event pages whenever possible.
3. Extract structured fields:
   - title
   - organizer
   - deadline
   - format
   - prize
   - requirements
   - official URL
   - submission URL
4. Downrank any contest that cannot be resolved to a trustworthy source.

## Trust Heuristic

Highest trust:

- official organizer page
- company or institution event page
- directly linked submission page

Medium trust:

- well-maintained aggregator with clear outbound links
- established media source summarizing the event

Low trust:

- repost pages with no organizer info
- social posts without official links
- contest listings with unclear deadlines or prizes

## Expansion Rule

When adding new sources:

- prefer sources with repeatable structure
- prefer sources that map to your creator workflow
- avoid adding sources just because they are popular
- remove sources that create more noise than discovery value
