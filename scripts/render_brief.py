#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


SECTION_TITLES = {
    "must_know_launches": "Must Know Launches",
    "builder_moves": "Builder Moves",
    "creator_workflows": "Creator Workflows",
    "viral_aigc": "Viral AIGC",
    "watch_next": "Watch Next",
    "contest_opportunities": "Contest Opportunities",
}


def render_standard_item(item: dict) -> list[str]:
    return [
        f"- Source: {item.get('source', '')}",
        f"  Why it matters: {item.get('why_it_matters', '')}",
        f"  Suggested angle: {item.get('suggested_angle', '')}",
        f"  Link: {item.get('source_url', '')}",
    ]


def render_contest_item(item: dict) -> list[str]:
    return [
        f"- Title: {item.get('title', '')}",
        f"  Organizer: {item.get('organizer', '')}",
        f"  Deadline: {item.get('deadline', '')}",
        f"  Prize: {item.get('prize', '')}",
        f"  Requirements: {item.get('requirements', '')}",
        f"  Official link: {item.get('official_url', '')}",
    ]


def render_brief(payload: dict) -> str:
    meta = payload["meta"]
    sections = payload["sections"]

    lines = [
        "# AI Creator Intel Brief",
        "",
        "## Topline",
        "",
        f"- Date: {meta.get('date', '')}",
        f"- Mode: {meta.get('mode', '')}",
        f"- Audience: {meta.get('audience', '')}",
        f"- Channels: {', '.join(meta.get('channels', []))}",
        "",
    ]

    for key, title in SECTION_TITLES.items():
        lines.append(f"## {title}")
        lines.append("")
        items = sections.get(key, [])
        if not items:
            lines.append("- None")
            lines.append("")
            continue
        for item in items:
            rendered = render_contest_item(item) if key == "contest_opportunities" else render_standard_item(item)
            lines.extend(rendered)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: render_brief.py <payload.json>", file=sys.stderr)
        return 1
    payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    print(render_brief(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
