#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml


TWITTERAPI_IO_ENDPOINT = "https://api.twitterapi.io/twitter/user/last_tweets"
X_BROWSER_URL_TEMPLATE = "https://x.com/{handle}"
DEFAULT_BROWSER_SCROLL_LIMIT = 5
DEFAULT_WINDOW_HOURS = 24


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_item(item: dict) -> dict:
    handle = item.get("handle") or item.get("userName")
    author = item.get("author") or {}
    handle = handle or author.get("userName") or author.get("username")
    return {
        "handle": handle,
        "text": item.get("text") or item.get("full_text") or "",
        "source_url": item.get("source_url") or item.get("url") or "",
        "created_at": item.get("created_at") or item.get("createdAt"),
        "content_type": item.get("content_type") or item.get("contentType") or "original",
        "engagement": {
            "likes": item.get("likes", item.get("likeCount", 0)),
            "retweets": item.get("retweets", item.get("retweetCount", 0)),
            "replies": item.get("replies", item.get("replyCount", 0)),
            "quotes": item.get("quotes", item.get("quoteCount", 0)),
        },
    }


def normalize_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [normalize_item(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        tweets = payload.get("tweets") or payload.get("data") or []
        if isinstance(tweets, list):
            return [normalize_item(item) for item in tweets if isinstance(item, dict)]
    raise ValueError("Unsupported Twitter payload shape")


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return data


def load_watchlist_accounts(base: Path, tiers: tuple[str, ...] = ("core",)) -> list[str]:
    watchlist = load_yaml(base / "config" / "twitter-watchlist.yaml")
    return [entry["handle"] for entry in watchlist["accounts"] if entry["tier"] in tiers]


def load_watchlist_core_accounts(base: Path) -> list[str]:
    return load_watchlist_accounts(base, tiers=("core",))


def fetch_twitterapiio_last_tweets(api_key: str, user_name: str, include_replies: bool = False) -> dict:
    query = urlencode({"userName": user_name, "includeReplies": str(include_replies).lower()})
    request = Request(
        f"{TWITTERAPI_IO_ENDPOINT}?{query}",
        headers={
            "X-API-Key": api_key,
            "User-Agent": "ai-creator-intel/0.1",
        },
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def require_browser_profile_dir(profile_dir: Path | None = None) -> Path:
    if profile_dir is not None:
        return profile_dir.expanduser()
    raw = os.getenv("X_BROWSER_PROFILE_DIR", "").strip()
    if not raw:
        raise ValueError("X_BROWSER_PROFILE_DIR is required for xbrowser://watchlist")
    return Path(raw).expanduser()


def fetch_browser_timeline(
    profile_dir: Path,
    handle: str,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_replies: bool = False,
) -> list[dict]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required for xbrowser://watchlist") from exc

    headless = os.getenv("X_BROWSER_HEADLESS", "true").lower() != "false"
    scroll_limit = int(os.getenv("X_BROWSER_SCROLL_LIMIT", str(DEFAULT_BROWSER_SCROLL_LIMIT)))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    collected: dict[str, dict] = {}

    script = """
    () => {
      const parseMetric = (value) => {
        if (!value) return 0;
        const normalized = value.trim().toLowerCase().replace(/,/g, "");
        const match = normalized.match(/([0-9]*\\.?[0-9]+)([km]?)/);
        if (!match) return 0;
        const base = parseFloat(match[1]);
        if (Number.isNaN(base)) return 0;
        if (match[2] === "k") return Math.round(base * 1000);
        if (match[2] === "m") return Math.round(base * 1000000);
        return Math.round(base);
      };

      const metricFor = (article, testid) => {
        const node = article.querySelector(`[data-testid="${testid}"]`);
        if (!node) return 0;
        const label = node.getAttribute("aria-label") || node.innerText || "";
        return parseMetric(label);
      };

      const inferType = (article) => {
        const socialContext = (article.querySelector('[data-testid="socialContext"]')?.innerText || "").toLowerCase();
        if (socialContext.includes("reposted") || socialContext.includes("retweeted")) {
          return "repost";
        }
        const textNodes = article.querySelectorAll('[data-testid="tweetText"]');
        if (textNodes.length > 1) {
          return "quote";
        }
        return "original";
      };

      return Array.from(document.querySelectorAll('article[data-testid="tweet"], article[role="article"]')).map((article) => {
        const text = Array.from(article.querySelectorAll('[data-testid="tweetText"]'))
          .map((node) => node.innerText.trim())
          .filter(Boolean)
          .join("\\n\\n");
        const time = article.querySelector("time");
        const statusLink = article.querySelector('a[href*="/status/"]');
        const socialContext = article.querySelector('[data-testid="socialContext"]')?.innerText || "";
        return {
          text,
          created_at: time ? time.getAttribute("datetime") : null,
          source_url: statusLink ? statusLink.href : "",
          content_type: inferType(article),
          social_context: socialContext,
          engagement: {
            replies: metricFor(article, "reply"),
            retweets: metricFor(article, "retweet"),
            likes: metricFor(article, "like"),
            quotes: metricFor(article, "app-text-transition-container"),
          },
        };
      });
    }
    """

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(str(profile_dir), headless=headless)
        try:
            page = context.new_page()
            page.goto(X_BROWSER_URL_TEMPLATE.format(handle=handle), wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_selector('article[data-testid="tweet"], article[role="article"]', timeout=15000)
            except PlaywrightTimeoutError as exc:
                raise RuntimeError(f"No tweet cards found for @{handle}; login state may be missing") from exc

            stagnant_rounds = 0
            for _ in range(scroll_limit):
                rows = page.evaluate(script)
                fresh_rows = 0
                for row in rows:
                    created_at = parse_timestamp(row.get("created_at"))
                    if not created_at or not row.get("source_url"):
                        continue
                    if not include_replies and "replying to" in (row.get("social_context") or "").lower():
                        continue
                    if created_at < cutoff:
                        continue
                    row["handle"] = handle
                    row["engagement"] = row.get("engagement") or {
                        "likes": 0,
                        "retweets": 0,
                        "replies": 0,
                        "quotes": 0,
                    }
                    row.pop("social_context", None)
                    if row["source_url"] not in collected:
                        collected[row["source_url"]] = normalize_item(row)
                        fresh_rows += 1

                oldest = None
                if rows:
                    timestamps = [parse_timestamp(row.get("created_at")) for row in rows]
                    valid = [stamp for stamp in timestamps if stamp]
                    oldest = min(valid) if valid else None

                if oldest is not None and oldest < cutoff:
                    break

                if fresh_rows == 0:
                    stagnant_rounds += 1
                else:
                    stagnant_rounds = 0
                if stagnant_rounds >= 2:
                    break

                page.mouse.wheel(0, 2400)
                page.wait_for_timeout(1200)
        finally:
            context.close()

    posts = list(collected.values())
    posts.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return posts


def collect_watchlist_posts(
    base: Path,
    fetcher=fetch_twitterapiio_last_tweets,
    account_limit: int | None = None,
    include_replies: bool = False,
) -> list[dict]:
    api_key = os.getenv("TWITTERAPI_IO_KEY")
    if not api_key:
        raise ValueError("TWITTERAPI_IO_KEY is required for twitterapiio://watchlist")

    handles = load_watchlist_core_accounts(base)
    if account_limit is not None:
        handles = handles[:account_limit]

    posts: list[dict] = []
    for handle in handles:
        payload = fetcher(api_key, handle, include_replies)
        posts.extend(normalize_payload(payload))
    return posts


def collect_browser_watchlist_posts(
    base: Path,
    scraper=fetch_browser_timeline,
    profile_dir: Path | None = None,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_replies: bool = False,
    tiers: tuple[str, ...] = ("core", "candidate"),
) -> list[dict]:
    resolved_profile_dir = require_browser_profile_dir(profile_dir)
    handles = load_watchlist_accounts(base, tiers=tiers)

    posts: list[dict] = []
    for handle in handles:
        rows = scraper(resolved_profile_dir, handle, window_hours, include_replies)
        posts.extend(normalize_payload(rows))
    return posts


def collect_posts(path: Path, base: Path | None = None) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_payload(payload)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: collect_twitter.py <posts.json|twitterapiio://watchlist|xbrowser://watchlist>", file=sys.stderr)
        return 1
    target = argv[1]
    base = Path(__file__).resolve().parents[1]
    if target == "twitterapiio://watchlist":
        posts = collect_watchlist_posts(base)
    elif target == "xbrowser://watchlist":
        posts = collect_browser_watchlist_posts(base)
    else:
        posts = collect_posts(Path(target), base)
    print(json.dumps(posts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
