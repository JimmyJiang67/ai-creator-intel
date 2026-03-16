#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


FIELD_ALIASES = {
    "title": ["title", "name", "赛事名称", "比赛名称", "活动名称"],
    "organizer": ["organizer", "host", "主办方", "主办单位", "组织方"],
    "deadline": ["deadline", "due_date", "截止时间", "报名截止", "征集截止"],
    "format": ["format", "type", "形式", "赛道", "作品形式"],
    "requirements": ["requirements", "rules", "参赛要求", "规则", "要求"],
    "prize": ["prize", "award", "奖金", "奖项"],
    "source_url": ["source_url", "url", "来源链接", "列表链接"],
    "official_url": ["official_url", "official", "官网链接", "官方链接", "活动链接"],
    "submission_url": ["submission_url", "apply_url", "报名链接", "提交链接", "参赛链接"],
    "region": ["region", "地区"],
    "target_audience": ["target_audience", "对象", "参赛对象"],
}


def first_value(raw: dict, keys: list[str]) -> str | None:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
        if value:
            return value
    return None


def normalize_contest(raw: dict) -> dict:
    normalized = {field: first_value(raw, aliases) for field, aliases in FIELD_ALIASES.items()}

    if not normalized["official_url"] and normalized["submission_url"]:
        normalized["official_url"] = normalized["submission_url"]

    normalized["is_valid"] = bool(
        normalized["title"] and normalized["organizer"] and normalized["deadline"] and normalized["source_url"]
    )
    return normalized


def normalize_file(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Input JSON must be a list of contest objects")
    return [normalize_contest(item) for item in payload]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: normalize_contests.py <input.json>", file=sys.stderr)
        return 1
    items = normalize_file(Path(argv[1]))
    print(json.dumps(items, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
