#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return data


def require_keys(data: dict, path: Path, keys: list[str]) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise ValueError(f"{path} missing keys: {', '.join(missing)}")


def main() -> int:
    base = Path(__file__).resolve().parents[1]
    files = {
        "watchlist": base / "config" / "twitter-watchlist.yaml",
        "twitter_fetch": base / "config" / "twitter-fetch-config.yaml",
        "news_sources": base / "config" / "news-sources.yaml",
        "contest_sources": base / "config" / "contest-sources.yaml",
        "openai_meta": base / "agents" / "openai.yaml",
    }

    parsed = {name: load_yaml(path) for name, path in files.items()}

    require_keys(parsed["watchlist"], files["watchlist"], ["version", "accounts"])
    require_keys(parsed["twitter_fetch"], files["twitter_fetch"], ["version", "runtime", "brief_generation"])
    require_keys(parsed["news_sources"], files["news_sources"], ["version", "source_groups"])
    require_keys(parsed["contest_sources"], files["contest_sources"], ["version", "source_groups", "required_fields"])
    require_keys(parsed["openai_meta"], files["openai_meta"], ["interface", "policy"])

    accounts = parsed["watchlist"]["accounts"]
    if not isinstance(accounts, list) or not accounts:
        raise ValueError("twitter-watchlist.yaml must contain a non-empty accounts list")

    handles = [item.get("handle") for item in accounts]
    if len(handles) != len(set(handles)):
        raise ValueError("twitter-watchlist.yaml contains duplicate handles")

    contest_required = parsed["contest_sources"]["required_fields"]
    if "deadline" not in contest_required or "organizer" not in contest_required:
        raise ValueError("contest-sources.yaml must require at least deadline and organizer")

    print("Config validation passed")
    print(f"Accounts: {len(accounts)}")
    print(f"News source groups: {len(parsed['news_sources']['source_groups'])}")
    print(f"Contest source groups: {len(parsed['contest_sources']['source_groups'])}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
