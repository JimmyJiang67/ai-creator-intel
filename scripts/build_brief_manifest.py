#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return data


def flatten_source_names(source_groups: dict) -> list[str]:
    names: list[str] = []
    for group in source_groups.values():
        for source in group.get("sources", []):
            names.append(source["name"])
    return names


def build_manifest(base: Path, mode: str = "daily_brief") -> dict:
    config_dir = base / "config"
    watchlist = load_yaml(config_dir / "twitter-watchlist.yaml")
    twitter_cfg = load_yaml(config_dir / "twitter-fetch-config.yaml")
    news_cfg = load_yaml(config_dir / "news-sources.yaml")
    contest_cfg = load_yaml(config_dir / "contest-sources.yaml")

    accounts = watchlist["accounts"]
    tier_counts = Counter(account["tier"] for account in accounts)
    news_source_names = flatten_source_names(news_cfg["source_groups"])
    contest_source_names = flatten_source_names(contest_cfg["source_groups"])

    section_order = list(twitter_cfg["brief_generation"]["section_order"])
    if "contest_opportunities" not in section_order:
        section_order.append("contest_opportunities")

    return {
        "mode": mode,
        "runtime": twitter_cfg["runtime"],
        "delivery": {
            "channels": twitter_cfg["delivery_hints"]["default_channels"],
            "subject_template": twitter_cfg["delivery_hints"]["subject_templates"].get(mode),
        },
        "twitter": {
            "account_count": len(accounts),
            "tier_counts": dict(tier_counts),
            "provider_order": twitter_cfg["sources"]["provider_order"],
        },
        "news": {
            "source_count": len(news_source_names),
            "source_names": news_source_names,
            "priority_order": news_cfg["strategy"]["priority_order"],
        },
        "contests": {
            "source_count": len(contest_source_names),
            "source_names": contest_source_names,
            "required_fields": contest_cfg["required_fields"],
        },
        "brief": {
            "section_order": section_order,
            "item_output_fields": twitter_cfg["brief_generation"]["item_output_fields"],
        },
    }


def main(argv: list[str]) -> int:
    base = Path(__file__).resolve().parents[1]
    mode = argv[1] if len(argv) > 1 else "daily_brief"
    manifest = build_manifest(base, mode=mode)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
