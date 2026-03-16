# AI Creator Intel Production Trial Checklist

## Goal

Run one real daily brief on the target OpenClaw machine, verify that the pipeline completes end-to-end, and collect enough signal to decide what to fix before wider use.

## Scope For Trial 1

- Use the real browser-based Twitter/X watchlist
- Use live default news sources
- Use live AIBetas contest source
- Render one complete daily brief locally first
- Only after local output looks usable, connect Feishu or email delivery

## Preflight

1. Confirm the skill folder exists on the OpenClaw machine.
   - Path: `/Users/feiyangjiang/Desktop/Skill Factory/ai-creator-intel`
2. Confirm Python 3 is available.
   - Run: `python3 --version`
3. Confirm Playwright is installed on that machine.
   - Run: `python3 -c "import playwright; print('ok')"`
4. Confirm the X browser profile is initialized and logged in.
   - If not, run:
     - `python3 '/Users/feiyangjiang/Desktop/Skill Factory/ai-creator-intel/scripts/init_x_browser_profile.py' --profile-dir '/path/to/x-profile'`
5. Export the browser profile path.
   - Run: `export X_BROWSER_PROFILE_DIR="/path/to/x-profile"`
6. Confirm config sanity before the real run.
   - Run: `python3 '/Users/feiyangjiang/Desktop/Skill Factory/ai-creator-intel/scripts/validate_configs.py'`

## Trial Run Order

Run in this order. Do not start with delivery.

### 1. Twitter/X only

Purpose:
Check that the browser collector can reuse the logged-in session and actually read recent posts from `core + candidate`.

Run:

```bash
python3 '/Users/feiyangjiang/Desktop/Skill Factory/ai-creator-intel/scripts/build_twitter_brief.py' \
  'xbrowser://watchlist' \
  daily_brief
```

Pass criteria:

- Command exits successfully
- Output is non-empty
- Output includes `original`, `quote`, or `repost` derived items
- No obvious login wall or empty watchlist failure

### 2. News only

Purpose:
Check that live news sources still resolve and the current filtering is usable.

Run:

```bash
python3 '/Users/feiyangjiang/Desktop/Skill Factory/ai-creator-intel/scripts/build_news_brief.py' \
  'news://default' \
  daily_brief
```

Pass criteria:

- Command exits successfully
- `must_know_launches` is populated
- Top items are mostly official or clearly useful discovery items
- No obvious policy statements, random HN noise, or repeated duplicate launch entries

### 3. Contests only

Purpose:
Check that live AIBetas parsing still works.

Run:

```bash
python3 '/Users/feiyangjiang/Desktop/Skill Factory/ai-creator-intel/scripts/build_contest_brief.py' \
  'https://www.aibetas.com.cn/aigc-events' \
  daily_brief \
  --render
```

Pass criteria:

- Command exits successfully
- `Contest Opportunities` is populated
- At least some items have organizer, deadline, or prize data

### 4. Full brief render

Purpose:
Check the real combined output before connecting delivery.

Run:

```bash
python3 '/Users/feiyangjiang/Desktop/Skill Factory/ai-creator-intel/scripts/build_full_brief.py' \
  --mode daily_brief \
  --twitter-source 'xbrowser://watchlist' \
  --news-source 'news://default' \
  --contest-source 'https://www.aibetas.com.cn/aigc-events' \
  --render
```

Pass criteria:

- Command exits successfully
- Combined output is readable end-to-end
- Sections feel balanced enough for one daily digest
- No single source dominates the entire brief

## What To Inspect In The Output

### Twitter/X

- Are the selected posts genuinely useful for your content workflow
- Are quote posts useful, or mostly noise
- Is `candidate` pool adding value, or just adding clutter
- Are there obvious misses from your core creators

### News

- Are official launches surfacing above platform discovery
- Are repeated launch announcements mostly deduplicated
- Are there still statement/policy items leaking through
- Is Product Hunt still too high in the final ordering

### Contests

- Are the contests current enough to act on
- Are deadlines parseable and useful
- Do the entries look like things your team would actually join

### Whole brief

- Is the overall length acceptable for Feishu/email
- Are section names understandable at a glance
- Would you personally open at least 3-5 of the included links

## Trial Log Template

Create one note for the run with these fields:

- Date and machine
- Command used
- Did the command succeed
- Runtime rough duration
- Which section felt strongest
- Which section felt weakest
- Top 3 useful items
- Top 3 noisy items
- Bugs or broken links
- Follow-up action

## Common Failure Modes

### Twitter/X fails

Check:

- `X_BROWSER_PROFILE_DIR` is set correctly
- The stored browser profile is still logged in
- X is not presenting a login or challenge page

Fallback:

- Re-run `init_x_browser_profile.py`
- For one debugging pass, reduce focus to Twitter-only first

### News feels noisy

Check:

- Whether the noise came from `Product Hunt` or `Hacker News`
- Whether the item should be blocked, downranked, or deduplicated differently

Fallback:

- Collect the exact source URL and title
- Do not tune blindly based on memory

### Contests are sparse or broken

Check:

- Whether AIBetas page structure changed
- Whether the fields are missing on the card itself

Fallback:

- Capture the problematic item URL
- Compare against `collect_contests.py`

## Exit Criteria For Trial 1

The first production trial is successful if all of these are true:

- Twitter/X run succeeds on the OpenClaw machine
- News run succeeds with sensible top launches
- Contest run succeeds with usable entries
- Full brief renders successfully
- You judge at least half of the final brief to be worth reading

## After The Trial

Only do one of these next:

1. If the brief is mostly good, wire Feishu/email delivery and stop changing ranking logic.
2. If one section is clearly weak, fix only that section.
3. If the whole brief is noisy, collect one real sample output and tune against that sample instead of continuing abstract optimization.
