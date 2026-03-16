#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml


AI_KEYWORDS = {
    "ai",
    "agent",
    "agents",
    "llm",
    "gpt",
    "claude",
    "openai",
    "anthropic",
    "gemini",
    "perplexity",
    "runway",
    "prompt",
    "workflow",
    "image model",
    "video model",
    "video generation",
    "image generation",
    "mcp",
    "codex",
    "cursor",
    "rag",
}

OFFICIAL_ALLOW_KEYWORDS = {
    "agent",
    "agents",
    "ai",
    "api",
    "apis",
    "assistant",
    "builder",
    "builders",
    "claude",
    "computer",
    "developer",
    "developers",
    "feature",
    "features",
    "image",
    "images",
    "launch",
    "launched",
    "launches",
    "model",
    "models",
    "product",
    "products",
    "prompt",
    "prompts",
    "release",
    "released",
    "releases",
    "research",
    "runway",
    "search",
    "video",
    "videos",
    "voice",
    "workflow",
    "workflows",
    "workspace",
}

OFFICIAL_STRONG_ALLOW_KEYWORDS = {
    "agent",
    "agents",
    "api",
    "apis",
    "assistant",
    "claude",
    "computer",
    "feature",
    "features",
    "image",
    "images",
    "launch",
    "launched",
    "launches",
    "model",
    "models",
    "product",
    "products",
    "prompt",
    "prompts",
    "release",
    "released",
    "releases",
    "research",
    "runway",
    "video",
    "videos",
    "voice",
    "workflow",
    "workflows",
    "workspace",
}

OFFICIAL_BLOCK_PATTERNS = [
    r"\bstatement\b",
    r"\bcomments?\b",
    r"\bsecretary of\b",
    r"\bdepartment of war\b",
    r"\btestimony\b",
    r"\bsubmission\b",
    r"\bletter to\b",
    r"\bpublic policy\b",
]

TITLE_STOPWORDS = {
    "a",
    "an",
    "the",
    "for",
    "to",
    "of",
    "in",
    "on",
    "with",
    "and",
    "new",
    "introducing",
    "launch",
    "launches",
    "launched",
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return data


def classify_news_item(item: dict) -> list[str]:
    labels = list(item.get("topic_tags", []))
    title = (item.get("title") or "").lower()

    if any(token in title for token in ["launch", "release", "introducing", "new model"]):
        labels.append("product_launch" if "model" not in title else "model_release")
    if any(token in title for token in ["github", "repo", "open source"]):
        labels.append("repo_or_tool")
    if any(token in title for token in ["workflow", "prompt", "template"]):
        labels.append("workflow")
    if any(token in title for token in ["video", "film", "runway"]):
        labels.append("aigc_video")
    if any(token in title for token in ["research", "paper", "deepmind"]):
        labels.append("research")

    deduped: list[str] = []
    for label in labels:
        canonical = "repo_or_tool" if label == "open_source" else label
        if canonical not in deduped:
            deduped.append(canonical)
    return deduped[:3] or ["industry_signal"]


def choose_section(labels: list[str], config: dict) -> str:
    mapping = config["brief_integration"]["map_to_sections"]
    for label in labels:
        if label in mapping:
            return mapping[label]
    return "watch_next"


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


def news_relevant(item: dict) -> bool:
    combined = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    if item.get("kind") == "official":
        has_block = any(re.search(pattern, combined) for pattern in OFFICIAL_BLOCK_PATTERNS)
        if has_block:
            return any(keyword in combined for keyword in OFFICIAL_STRONG_ALLOW_KEYWORDS)
        return True
    for keyword in AI_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, combined):
            return True
    return False


def within_lookback(item: dict, hours: int) -> bool:
    timestamp = parse_timestamp(item.get("published_at"))
    if timestamp is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return timestamp >= cutoff


def category_score_adjustment(category: str, section: str) -> float:
    if section == "must_know_launches":
        if category == "official":
            return 1.4
        if category == "internal_watchlist":
            return 0.3
        if category == "platform":
            return -0.6
        if category == "media":
            return -0.75
    if category == "official":
        return 0.25
    if category == "media":
        return -0.1
    return 0.0


def score_item(item: dict, labels: list[str], section: str) -> float:
    priority = float(item.get("priority", 0.7))
    bonus = 0.35 * len(labels)
    title_score = math.log1p(len(item.get("title", "")))
    category_bonus = category_score_adjustment(item.get("kind", "news"), section)
    return round(priority * 5 + bonus + title_score * 0.4 + category_bonus, 2)


def summarize_why(item: dict, labels: list[str]) -> str:
    if any(label in {"model_release", "product_launch"} for label in labels):
        return "Primary launch signal worth validating and turning into creator-facing coverage."
    if "repo_or_tool" in labels:
        return "Useful builder signal with likely tool or workflow implications."
    if any(label in {"workflow", "aigc_video"} for label in labels):
        return "Potentially reusable creator workflow or trend signal."
    return (item.get("summary") or item.get("title") or "")[:120]


def choose_angle(labels: list[str]) -> str:
    if any(label in {"model_release", "product_launch"} for label in labels):
        return "What changed for creators or builders, and what is actually new?"
    if "repo_or_tool" in labels:
        return "Can this be reframed as a builder tool or workflow worth testing?"
    if any(label in {"workflow", "aigc_video"} for label in labels):
        return "Can followers reproduce this quickly and turn it into content?"
    return "Is this worth monitoring before it becomes a bigger trend?"


def normalize_title_key(value: str) -> str:
    lowered = value.lower().strip()
    collapsed = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", collapsed).strip()


def significant_title_tokens(value: str) -> set[str]:
    normalized = normalize_title_key(value)
    return {
        token
        for token in normalized.split()
        if len(token) >= 3 and token not in TITLE_STOPWORDS
    }


def near_duplicate_titles(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if normalize_title_key(left) == normalize_title_key(right):
        return True

    left_tokens = significant_title_tokens(left)
    right_tokens = significant_title_tokens(right)
    if not left_tokens or not right_tokens:
        return False

    overlap = left_tokens & right_tokens
    if len(overlap) < 2:
        return False

    union_size = len(left_tokens | right_tokens)
    smaller_size = min(len(left_tokens), len(right_tokens))
    jaccard = len(overlap) / union_size
    containment = len(overlap) / smaller_size
    return jaccard >= 0.75 or containment >= 1.0


def source_rank(category: str) -> int:
    order = {
        "official": 4,
        "internal_watchlist": 3,
        "platform": 2,
        "media": 1,
        "news": 1,
    }
    return order.get(category, 0)


def should_replace_duplicate(existing: dict, candidate: dict) -> bool:
    existing_rank = source_rank(existing.get("category", "news"))
    candidate_rank = source_rank(candidate.get("category", "news"))
    if candidate_rank != existing_rank:
        return candidate_rank > existing_rank
    return candidate["score"] > existing["score"]


def deduplicate_scored_items(items: list[dict]) -> list[dict]:
    best_by_key: dict[str, dict] = {}
    for item in items:
        title = item.get("title", "")
        title_key = normalize_title_key(title)
        url_key = item.get("source_url", "").strip().lower()
        dedupe_key = title_key or url_key
        if not dedupe_key:
            continue
        matched_key = None
        for existing_key, existing_item in best_by_key.items():
            if existing_key == dedupe_key:
                matched_key = existing_key
                break
            if near_duplicate_titles(title, existing_item.get("title", "")):
                matched_key = existing_key
                break

        existing = best_by_key.get(matched_key or dedupe_key)
        if existing is None or should_replace_duplicate(existing, item):
            best_by_key[matched_key or dedupe_key] = item
    return list(best_by_key.values())


def balance_section_items(items: list[dict], max_items: int) -> list[dict]:
    if len(items) <= 1:
        return items[:max_items]

    balanced: list[dict] = []
    seen_sources: set[str] = set()

    for item in items:
        source = item.get("source", "")
        if source in seen_sources:
            continue
        balanced.append(item)
        seen_sources.add(source)
        if len(balanced) >= max_items:
            return balanced

    for item in items:
        if len(balanced) >= max_items:
            break
        if item in balanced:
            continue
        balanced.append(item)

    return balanced


def build_payload(base: Path, source: str, mode: str = "daily_brief") -> dict:
    collect_mod = load_module(base / "scripts" / "collect_news.py", "collect_news")
    manifest_mod = load_module(base / "scripts" / "build_brief_manifest.py", "build_brief_manifest")
    news_cfg = load_yaml(base / "config" / "news-sources.yaml")
    manifest = manifest_mod.build_manifest(base, mode=mode)
    lookback_hours = manifest["runtime"]["lookback_hours"].get(mode, 24)

    if source == "news://default":
        items = collect_mod.collect_default_news(base)
    else:
        items = collect_mod.collect_news(Path(source))

    sections = {section: [] for section in manifest["brief"]["section_order"]}
    bucketed = {section: [] for section in manifest["brief"]["section_order"]}
    scored_items: list[dict] = []

    for item in items:
        if not news_relevant(item):
            continue
        if not within_lookback(item, lookback_hours):
            continue
        labels = classify_news_item(item)
        section = choose_section(labels, news_cfg)
        scored = {
            "title": item["title"],
            "source": item["source_name"],
            "category": item.get("kind", "news"),
            "labels": labels,
            "why_it_matters": summarize_why(item, labels),
            "suggested_angle": choose_angle(labels),
            "source_url": item["source_url"],
            "section": section,
            "score": score_item(item, labels, section),
        }
        scored_items.append(scored)

    for item in deduplicate_scored_items(scored_items):
        bucketed[item["section"]].append(item)

    for section, items_for_section in bucketed.items():
        items_for_section.sort(key=lambda item: item["score"], reverse=True)
        max_items = 3 if section != "must_know_launches" else 5
        balanced = balance_section_items(items_for_section, max_items)
        sections[section] = [
            {k: v for k, v in item.items() if k not in {"score", "section", "title"}}
            for item in balanced
        ]

    return {
        "meta": {
            "date": date.today().isoformat(),
            "mode": mode,
            "audience": "AI creator",
            "channels": manifest["delivery"]["channels"],
        },
        "sections": sections,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: build_news_brief.py <news.json|news://default> [mode]", file=sys.stderr)
        return 1
    base = Path(__file__).resolve().parents[1]
    mode = argv[2] if len(argv) > 2 else "daily_brief"
    payload = build_payload(base, argv[1], mode=mode)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
