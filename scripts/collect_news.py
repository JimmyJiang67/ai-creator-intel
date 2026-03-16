#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree

import yaml


DEFAULT_HEADERS = {
    "User-Agent": "ai-creator-intel/0.1",
}


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return data


def load_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} did not parse to a JSON list")
    return [item for item in data if isinstance(item, dict)]


def fetch_url(url: str, headers: dict | None = None) -> bytes:
    merged_headers = dict(DEFAULT_HEADERS)
    if headers:
        merged_headers.update(headers)
    request = Request(url, headers=merged_headers)
    with urlopen(request, timeout=20) as response:
        return response.read()


def parse_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return value
    return parsed.isoformat()


def parse_human_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%b %d, %Y")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc).isoformat()


def normalize_news_item(
    source: dict,
    *,
    title: str,
    source_url: str,
    published_at: str | None,
    summary: str = "",
) -> dict:
    return {
        "title": unescape(title.strip()),
        "summary": unescape(summary.strip()),
        "source_name": source["name"],
        "source_url": source_url.strip(),
        "published_at": published_at,
        "topic_tags": list(source.get("topic_tags", [])),
        "priority": source.get("priority", 0.7),
        "kind": source.get("kind", "news"),
    }


def parse_rss_feed(payload: bytes, source: dict) -> list[dict]:
    root = ElementTree.fromstring(payload)
    items: list[dict] = []

    if root.tag.endswith("feed"):
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0] + "}"
        entries = root.findall(f"{namespace}entry")
        for entry in entries:
            title = entry.findtext(f"{namespace}title", default="")
            summary = entry.findtext(f"{namespace}summary", default="") or entry.findtext(
                f"{namespace}content", default=""
            )
            published_at = (
                entry.findtext(f"{namespace}updated", default="")
                or entry.findtext(f"{namespace}published", default="")
            )
            source_url = ""
            for link in entry.findall(f"{namespace}link"):
                href = link.attrib.get("href")
                if href:
                    source_url = href
                    break
            if title and source_url:
                items.append(
                    normalize_news_item(
                        source,
                        title=title,
                        summary=summary,
                        source_url=source_url,
                        published_at=parse_datetime(published_at),
                    )
                )
        return items

    channel = root.find("channel")
    if channel is None:
        return items
    for item in channel.findall("item"):
        title = item.findtext("title", default="")
        source_url = item.findtext("link", default="")
        summary = item.findtext("description", default="")
        published_at = parse_datetime(item.findtext("pubDate", default=""))
        if title and source_url:
            items.append(
                normalize_news_item(
                    source,
                    title=title,
                    summary=summary,
                    source_url=source_url,
                    published_at=published_at,
                )
            )
    return items


def parse_github_trending(payload: str, source: dict) -> list[dict]:
    items: list[dict] = []
    pattern = re.compile(
        r"<article[^>]*Box-row[^>]*>.*?<h2[^>]*>\s*<a[^>]*href=[\"']/(?P<repo>[^\"']+)[\"'][^>]*>(?P<title>.*?)</a>.*?"
        r"(?:<p[^>]*>(?P<description>.*?)</p>)?",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(payload):
        repo = re.sub(r"\s+", "", unescape(match.group("repo")))
        title = re.sub(r"\s+", " ", unescape(match.group("title") or "")).strip()
        title = title.replace(" / ", "/")
        description = re.sub(r"\s+", " ", unescape(match.group("description") or "")).strip()
        items.append(
            normalize_news_item(
                source,
                title=title or repo,
                summary=description,
                source_url=f"https://github.com/{repo}",
                published_at=None,
            )
        )
    return items


def prettify_slug(slug: str) -> str:
    parts = [segment for segment in slug.strip("/").split("/") if segment]
    tail = parts[-1] if parts else slug
    words = [word.upper() if word.isupper() else word.capitalize() for word in tail.split("-")]
    return " ".join(words)


def parse_anthropic_news(payload: str, source: dict) -> list[dict]:
    items: list[dict] = []
    seen_urls: set[str] = set()
    pattern = re.compile(
        r"<a[^>]*href=[\"'](?P<href>/news/[^\"'#?]+)[\"'][^>]*>(?P<label>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(payload):
        href = match.group("href")
        if href == "/news":
            continue
        source_url = f"https://www.anthropic.com{href}"
        if source_url in seen_urls:
            continue
        label_html = match.group("label")
        label = re.sub(r"<[^>]+>", " ", label_html)
        label = re.sub(r"\s+", " ", unescape(label)).strip()
        items.append(
            normalize_news_item(
                source,
                title=label or prettify_slug(href),
                summary="",
                source_url=source_url,
                published_at=None,
            )
        )
        seen_urls.add(source_url)
    return items


def parse_runway_news(payload: str, source: dict) -> list[dict]:
    items: list[dict] = []
    seen_urls: set[str] = set()
    pattern = re.compile(
        r"<a[^>]*href=[\"'](?P<href>/?news/[^\"'#?]+)[\"'][^>]*>(?P<label>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(payload):
        href = match.group("href")
        if href in {"/news", "news"}:
            continue
        normalized_href = href if href.startswith("/") else f"/{href}"
        source_url = f"https://runwayml.com{normalized_href}"
        if source_url in seen_urls:
            continue
        label_html = match.group("label")
        label = re.sub(r"<[^>]+>", " ", label_html)
        label = re.sub(r"\s+", " ", unescape(label)).strip()
        items.append(
            normalize_news_item(
                source,
                title=label or prettify_slug(normalized_href),
                summary="",
                source_url=source_url,
                published_at=None,
            )
        )
        seen_urls.add(source_url)
    return items


def parse_elevenlabs_blog(payload: str, source: dict) -> list[dict]:
    items: list[dict] = []
    seen_urls: set[str] = set()
    pattern = re.compile(
        r"<a[^>]*href=[\"'](?P<href>/blog/[^\"'#?]+)[\"'][^>]*>(?P<label>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(payload):
        href = match.group("href")
        if href in {"/blog"} or href.startswith("/blog/category/") or href.startswith("/blog/page/"):
            continue
        source_url = f"https://elevenlabs.io{href}"
        if source_url in seen_urls:
            continue
        label_html = match.group("label")
        label = re.sub(r"<[^>]+>", " ", label_html)
        label = re.sub(r"\s+", " ", unescape(label)).strip()
        items.append(
            normalize_news_item(
                source,
                title=label or prettify_slug(href),
                summary="",
                source_url=source_url,
                published_at=None,
            )
        )
        seen_urls.add(source_url)
    return items


def parse_perplexity_blog(payload: str, source: dict, fetcher=fetch_url) -> list[dict]:
    index_match = re.search(
        r'<meta[^>]+name=["\']framer-search-index["\'][^>]+content=["\'](?P<url>[^"\']+)["\']',
        payload,
        re.IGNORECASE,
    )
    if not index_match:
        index_match = re.search(
            r'<meta[^>]+name=["\']framer-search-index-fallback["\'][^>]+content=["\'](?P<url>[^"\']+)["\']',
            payload,
            re.IGNORECASE,
        )
    if not index_match:
        return []

    search_index_url = index_match.group("url")
    index_payload = fetcher(search_index_url, headers=DEFAULT_HEADERS)
    raw_entries = json.loads(index_payload.decode("utf-8"))
    if not isinstance(raw_entries, dict):
        return []

    items: list[dict] = []
    for path, entry in raw_entries.items():
        if not isinstance(path, str) or not path.startswith("/hub/blog/"):
            continue
        if not isinstance(entry, dict):
            continue

        title = ""
        h1 = entry.get("h1")
        if isinstance(h1, list) and h1:
            title = str(h1[0]).strip()
        if not title:
            title = str(entry.get("title", "")).strip()
        if not title:
            title = prettify_slug(path)

        published_at = None
        paragraphs = entry.get("p")
        if isinstance(paragraphs, list):
            for index, part in enumerate(paragraphs):
                if str(part).strip() == "Published on" and index + 1 < len(paragraphs):
                    published_at = parse_human_date(str(paragraphs[index + 1]))
                    break

        items.append(
            normalize_news_item(
                source,
                title=title,
                summary=str(entry.get("description", "")).strip(),
                source_url=f"https://www.perplexity.ai{path}",
                published_at=published_at,
            )
        )

    return items


def parse_with_source_config(payload: bytes, source: dict, fetcher=fetch_url) -> list[dict]:
    parser = source.get("fetch", {}).get("parser", "rss")
    if parser == "rss":
        return parse_rss_feed(payload, source)
    if parser == "github_trending":
        return parse_github_trending(payload.decode("utf-8", errors="ignore"), source)
    if parser == "anthropic_news":
        return parse_anthropic_news(payload.decode("utf-8", errors="ignore"), source)
    if parser == "perplexity_blog":
        return parse_perplexity_blog(payload.decode("utf-8", errors="ignore"), source, fetcher=fetcher)
    if parser == "runway_news":
        return parse_runway_news(payload.decode("utf-8", errors="ignore"), source)
    if parser == "elevenlabs_blog":
        return parse_elevenlabs_blog(payload.decode("utf-8", errors="ignore"), source)
    raise ValueError(f"Unsupported news parser: {parser}")


def enabled_news_sources(base: Path) -> list[dict]:
    config = load_yaml(base / "config" / "news-sources.yaml")
    sources: list[dict] = []
    for group in config["source_groups"].values():
        for source in group.get("sources", []):
            if source.get("fetch", {}).get("enabled"):
                sources.append(source)
    return sources


def collect_default_news(base: Path, fetcher=fetch_url) -> list[dict]:
    items: list[dict] = []
    for source in enabled_news_sources(base):
        url = source["fetch"]["url"]
        payload = fetcher(url, headers=DEFAULT_HEADERS)
        items.extend(parse_with_source_config(payload, source, fetcher=fetcher))
    return items


def collect_news(path: Path) -> list[dict]:
    return load_json(path)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: collect_news.py <news.json|news://default>", file=sys.stderr)
        return 1
    base = Path(__file__).resolve().parents[1]
    target = argv[1]
    if target == "news://default":
        items = collect_default_news(base)
    else:
        items = collect_news(Path(target))
    print(json.dumps(items, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
