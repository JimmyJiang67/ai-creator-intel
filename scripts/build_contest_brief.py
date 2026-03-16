#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, datetime
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


def parse_deadline(value: str | None) -> tuple[int, object]:
    if not value:
        return (1, value or "")
    for fmt in ("%Y-%m-%d", "%Y年%m月%d日", "%Y年%-m月%-d日"):
        try:
            return (0, datetime.strptime(value, fmt).date())
        except ValueError:
            continue
    try:
        parts = (
            value.replace("年", "-")
            .replace("月", "-")
            .replace("日", "")
            .replace("/", "-")
            .split("-")
        )
        parts = [part for part in parts if part]
        if len(parts) == 3:
            year, month, day = map(int, parts)
            return (0, date(year, month, day))
    except ValueError:
        pass
    return (1, value)


def prize_score(value: str | None) -> int:
    if not value or value == "/":
        return 0
    score = 1
    if any(token in value for token in ["万元", "$", "现金", "奖金", "门票", "资助", "support"]):
        score += 1
    return score


def select_contests(contests: list[dict], max_items: int) -> list[dict]:
    valid = [contest for contest in contests if contest.get("is_valid")]
    ranked = sorted(
        valid,
        key=lambda item: (
            parse_deadline(item.get("deadline")),
            -prize_score(item.get("prize")),
            item.get("title", ""),
        ),
    )
    return ranked[:max_items]


def build_payload(base: Path, source: str, mode: str = "daily_brief") -> dict:
    scripts_dir = base / "scripts"
    collect_mod = load_module(scripts_dir / "collect_contests.py", "collect_contests")
    manifest_mod = load_module(scripts_dir / "build_brief_manifest.py", "build_brief_manifest")

    contest_cfg = load_yaml(base / "config" / "contest-sources.yaml")
    max_items = contest_cfg["brief_integration"]["max_items"].get(mode, 3)

    if source.startswith("http://") or source.startswith("https://"):
        contests = collect_mod.collect_aibetas_events(source, base=base)
    else:
        contests = collect_mod.collect_contests(Path(source), base=base)

    selected = select_contests(contests, max_items=max_items)
    manifest = manifest_mod.build_manifest(base, mode=mode)

    sections = {section: [] for section in manifest["brief"]["section_order"]}
    sections["contest_opportunities"] = selected

    return {
        "meta": {
            "date": date.today().isoformat(),
            "mode": mode,
            "audience": "AI creator",
            "channels": manifest["delivery"]["channels"],
        },
        "sections": sections,
    }


def render_payload(base: Path, payload: dict) -> str:
    render_mod = load_module(base / "scripts" / "render_brief.py", "render_brief")
    return render_mod.render_brief(payload)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: build_contest_brief.py <source.json|aibetas_url> [mode] [--render]", file=sys.stderr)
        return 1

    base = Path(__file__).resolve().parents[1]
    source = argv[1]
    mode = argv[2] if len(argv) >= 3 and not argv[2].startswith("--") else "daily_brief"
    render = "--render" in argv[2:]

    payload = build_payload(base, source, mode=mode)
    if render:
        print(render_payload(base, payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
