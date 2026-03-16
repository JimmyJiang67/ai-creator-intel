#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import math
import sys
from datetime import date
from pathlib import Path

import yaml


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


def watchlist_index(base: Path) -> dict[str, dict]:
    watchlist = load_yaml(base / "config" / "twitter-watchlist.yaml")
    return {entry["handle"].lower(): entry for entry in watchlist["accounts"]}


def classify_post(text: str) -> list[str]:
    lowered = text.lower()
    labels: list[str] = []
    if any(token in lowered for token in ["model", "release", "launch", "introducing", "feature", "api"]):
        labels.append("model_release" if "model" in lowered else "product_launch")
    if any(token in lowered for token in ["prompt", "workflow", "template"]):
        labels.append("prompt" if "prompt" in lowered else "builder_workflow")
    if any(token in lowered for token in ["repo", "github", "tool"]):
        labels.append("repo_or_tool")
    if any(token in lowered for token in ["video", "film", "runway", "viral"]):
        labels.append("viral_video")
    if not labels:
        labels.append("industry_narrative")
    return labels[:3]


def post_relevant(text: str, account: dict | None, config: dict) -> bool:
    lowered = text.lower()
    if account and account.get("category") in {"official", "founder"}:
        return True
    keywords = config["ai_relevance"]["required_keywords_any"]
    return any(keyword in lowered for keyword in keywords)


def score_post(post: dict, account: dict | None, config: dict) -> float:
    category = account.get("category", "creator") if account else "creator"
    category_priority = config["account_category_policy"].get(category, {}).get("default_priority", 0.6)
    engagement = post["engagement"]
    engagement_score = math.log1p(
        engagement.get("likes", 0) + 2 * engagement.get("retweets", 0) + engagement.get("quotes", 0)
    )
    label_bonus = len(post["labels"]) * 0.4
    content_type = post.get("content_type", "original")
    content_type_multiplier = {"original": 1.0, "quote": 0.95, "repost": 0.7}.get(content_type, 1.0)
    return round((category_priority * 5 + engagement_score * 0.6 + label_bonus) * content_type_multiplier, 2)


def choose_section(labels: list[str], config: dict) -> str:
    if any(label in {"viral_video", "viral_image"} for label in labels):
        return "viral_aigc"
    if any(label in {"model_release", "product_launch", "feature_update", "funding_or_company_move"} for label in labels):
        return "must_know_launches"
    if "prompt" in labels:
        return "creator_workflows"
    if any(label in {"builder_workflow", "repo_or_tool"} for label in labels):
        return "builder_moves"
    if any(label in {"research_signal", "industry_narrative"} for label in labels):
        return "watch_next"
    for section, rule in config["brief_generation"]["section_rules"].items():
        if any(label in rule["include_labels"] for label in labels):
            return section
    return "watch_next"


def choose_angle(labels: list[str], config: dict) -> str:
    prioritized = config["creator_angles"]["prioritize_angles_for_labels"]
    for label in labels:
        if label in prioritized:
            return prioritized[label][0]
    return config["creator_angles"]["default_angles"][0]


def summarize_why(text: str, labels: list[str], account: dict | None) -> str:
    label = labels[0]
    if label in {"model_release", "product_launch"}:
        return "First-hand launch signal worth turning into a creator-facing update."
    if label in {"prompt", "builder_workflow"}:
        return "Reusable workflow signal with direct creator utility."
    if label == "viral_video":
        return "Potential viral AIGC example worth reverse engineering."
    if account and account.get("category") == "builder":
        return "Builder-side signal with practical product or workflow implications."
    return text[:120]


def build_payload(base: Path, source: str, mode: str = "daily_brief") -> dict:
    collect_mod = load_module(base / "scripts" / "collect_twitter.py", "collect_twitter")
    config = load_yaml(base / "config" / "twitter-fetch-config.yaml")
    manifest_mod = load_module(base / "scripts" / "build_brief_manifest.py", "build_brief_manifest")
    manifest = manifest_mod.build_manifest(base, mode=mode)
    indexed_accounts = watchlist_index(base)
    if source == "twitterapiio://watchlist":
        posts = collect_mod.collect_watchlist_posts(base)
    elif source == "xbrowser://watchlist":
        posts = collect_mod.collect_browser_watchlist_posts(base)
    else:
        posts = collect_mod.collect_posts(Path(source), base)

    sections = {section: [] for section in manifest["brief"]["section_order"]}
    bucketed: dict[str, list[dict]] = {section: [] for section in manifest["brief"]["section_order"]}

    for post in posts:
        account = indexed_accounts.get((post.get("handle") or "").lower())
        if not post_relevant(post["text"], account, config):
            continue
        labels = classify_post(post["text"])
        post["labels"] = labels
        post["score"] = score_post(post, account, config)
        section = choose_section(labels, config)
        bucketed[section].append(
            {
                "source": f"@{post['handle']}",
                "category": account.get("category", "creator") if account else "creator",
                "content_type": post.get("content_type", "original"),
                "labels": labels,
                "why_it_matters": summarize_why(post["text"], labels, account),
                "suggested_angle": choose_angle(labels, config),
                "source_url": post["source_url"],
                "score": post["score"],
            }
        )

    for section, items in bucketed.items():
        items.sort(key=lambda item: item["score"], reverse=True)
        max_items = config["brief_generation"]["section_rules"].get(section, {}).get("max_items", 3)
        sections[section] = [{k: v for k, v in item.items() if k != "score"} for item in items[:max_items]]

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
        print("Usage: build_twitter_brief.py <posts.json|twitterapiio://watchlist|xbrowser://watchlist> [mode]", file=sys.stderr)
        return 1
    base = Path(__file__).resolve().parents[1]
    mode = argv[2] if len(argv) > 2 else "daily_brief"
    payload = build_payload(base, argv[1], mode=mode)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
