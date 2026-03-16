#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a JSON object")
    return data


def build_full_payload(
    base: Path,
    mode: str = "daily_brief",
    standard_sections_path: str | None = None,
    news_source: str | None = None,
    twitter_source: str | None = None,
    contest_source: str | None = None,
) -> dict:
    scripts_dir = base / "scripts"
    manifest_mod = load_module(scripts_dir / "build_brief_manifest.py", "build_brief_manifest")
    news_mod = load_module(scripts_dir / "build_news_brief.py", "build_news_brief")
    contest_mod = load_module(scripts_dir / "build_contest_brief.py", "build_contest_brief")
    twitter_mod = load_module(scripts_dir / "build_twitter_brief.py", "build_twitter_brief")

    manifest = manifest_mod.build_manifest(base, mode=mode)
    section_order = manifest["brief"]["section_order"]
    sections = {section: [] for section in section_order}

    if standard_sections_path:
        standard_sections = load_json(Path(standard_sections_path))
        for section, items in standard_sections.items():
            if section in sections:
                sections[section] = items

    if news_source:
        news_payload = news_mod.build_payload(base, news_source, mode=mode)
        for section, items in news_payload["sections"].items():
            if section in sections and items:
                sections[section].extend(items)

    if twitter_source:
        twitter_payload = twitter_mod.build_payload(base, twitter_source, mode=mode)
        for section, items in twitter_payload["sections"].items():
            if section in sections and items:
                sections[section].extend(items)

    if contest_source:
        contest_payload = contest_mod.build_payload(base, contest_source, mode=mode)
        sections["contest_opportunities"] = contest_payload["sections"]["contest_opportunities"]

    return {
        "meta": {
            "date": date.today().isoformat(),
            "mode": mode,
            "audience": "AI creator",
            "channels": manifest["delivery"]["channels"],
        },
        "sections": sections,
    }


def render_full_payload(base: Path, payload: dict) -> str:
    render_mod = load_module(base / "scripts" / "render_brief.py", "render_brief")
    return render_mod.render_brief(payload)


def main(argv: list[str]) -> int:
    base = Path(__file__).resolve().parents[1]
    mode = "daily_brief"
    standard_sections_path: str | None = None
    news_source: str | None = None
    twitter_source: str | None = None
    contest_source: str | None = None
    render = False

    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg == "--mode":
            mode = argv[index + 1]
            index += 2
        elif arg == "--standard-sections":
            standard_sections_path = argv[index + 1]
            index += 2
        elif arg == "--news-source":
            news_source = argv[index + 1]
            index += 2
        elif arg == "--twitter-source":
            twitter_source = argv[index + 1]
            index += 2
        elif arg == "--contest-source":
            contest_source = argv[index + 1]
            index += 2
        elif arg == "--render":
            render = True
            index += 1
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            return 1

    payload = build_full_payload(
        base,
        mode=mode,
        standard_sections_path=standard_sections_path,
        news_source=news_source,
        twitter_source=twitter_source,
        contest_source=contest_source,
    )

    if render:
        print(render_full_payload(base, payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
