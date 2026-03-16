#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import importlib.util

ALLOWED_HOSTS = {"www.aibetas.com.cn", "aibetas.com.cn"}


def load_normalizer(base: Path):
    path = base / "scripts" / "normalize_contests.py"
    spec = importlib.util.spec_from_file_location("normalize_contests", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SimpleHTMLEventParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[tuple[str, str, str | None]] = []
        self._capture_tag: str | None = None
        self._buffer: list[str] = []
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "p", "li", "a"}:
            self._capture_tag = tag
            self._buffer = []
            self._href = dict(attrs).get("href") if tag == "a" else None

    def handle_data(self, data: str) -> None:
        if self._capture_tag is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture_tag == tag:
            text = " ".join("".join(self._buffer).split())
            if text:
                self.events.append((tag, text, self._href))
            self._capture_tag = None
            self._buffer = []
            self._href = None


def validate_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    if parsed.netloc not in ALLOWED_HOSTS:
        raise ValueError(f"Host not allowed for contest scraping: {parsed.netloc}")


def fetch_url(url: str) -> str:
    validate_source_url(url)
    request = Request(url, headers={"User-Agent": "ai-creator-intel/0.1"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


def field_from_lines(lines: list[str], labels: list[str]) -> str | None:
    for line in lines:
        for label in labels:
            prefix = f"{label}:"
            if line.startswith(prefix):
                value = line[len(prefix) :].strip()
                return value or None
    return None


def clean_html_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(" ".join(text.split()))
    return text or None


def parse_aibetas_cards(html: str, page_url: str) -> list[dict]:
    items: list[dict] = []
    marker = 'class="competition-card'
    if marker not in html:
        return items

    positions = [match.start() for match in re.finditer(re.escape(marker), html)]
    positions.append(len(html))

    def search(block: str, pattern: str) -> str | None:
        match = re.search(pattern, block, re.S)
        if not match:
            return None
        return clean_html_text(match.group(1))

    for index in range(len(positions) - 1):
        block = html[positions[index] : positions[index + 1]]
        title = search(block, r'<h2 class="card-title">(.*?)</h2>')
        organizer = search(block, r'class="organizer-name">(.*?)</span>')
        deadline = search(block, r'class="deadline-date">(.*?)</span>')
        prize = search(block, r'class="prize-amount">(.*?)</span>')
        description = search(block, r'<p class="card-description">(.*?)</p>')
        format_value = search(block, r'class="tag"[^>]*>(.*?)</div>')
        register_match = re.search(r'register-btn" data-url="(.*?)"', block, re.S)
        details_match = re.search(r'details-btn" data-url="(.*?)"', block, re.S)
        register_url = urljoin(page_url, register_match.group(1)) if register_match else None
        details_url = urljoin(page_url, details_match.group(1)) if details_match else None
        if not title or not organizer or not deadline:
            continue
        items.append(
            {
                "title": title,
                "organizer": organizer,
                "deadline": deadline,
                "prize": prize,
                "requirements": description,
                "format": format_value,
                "official_url": details_url,
                "submission_url": register_url,
                "source_url": page_url,
                "is_valid": True,
            }
        )
    return items


def parse_aibetas_html(html: str, page_url: str) -> list[dict]:
    card_items = parse_aibetas_cards(html, page_url)
    if card_items:
        return card_items

    parser = SimpleHTMLEventParser()
    parser.feed(html)

    blocks: list[dict] = []
    current: dict | None = None

    for tag, text, href in parser.events:
        if tag in {"h2", "h3"}:
            if current:
                blocks.append(current)
            current = {"title": text, "lines": [], "links": []}
            continue
        if current is None:
            continue
        if tag in {"p", "li"}:
            current["lines"].append(text)
        elif tag == "a" and href:
            current["links"].append(urljoin(page_url, href))

    if current:
        blocks.append(current)

    items: list[dict] = []
    for block in blocks:
        lines = block["lines"]
        organizer = field_from_lines(lines, ["主办单位", "主办方", "组织方"])
        deadline = field_from_lines(lines, ["截止日期", "截止时间", "报名截止"])
        prize = field_from_lines(lines, ["奖金池", "奖金", "奖项"])

        if not organizer or not deadline:
            continue

        description = None
        format_value = None
        for line in lines:
            if ":" in line:
                continue
            if description is None and len(line) >= 10:
                description = line
                continue
            if format_value is None:
                format_value = line

        official_url = block["links"][0] if block["links"] else None
        items.append(
            {
                "title": block["title"],
                "organizer": organizer,
                "deadline": deadline,
                "prize": prize,
                "requirements": description,
                "format": format_value,
                "official_url": official_url,
                "submission_url": official_url,
                "source_url": page_url,
                "is_valid": True,
            }
        )

    return items


def collect_contests(sample_path: Path, base: Path | None = None) -> list[dict]:
    if base is None:
        base = Path(__file__).resolve().parents[1]
    normalizer = load_normalizer(base)
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Contest sample data must be a list")
    return [normalizer.normalize_contest(item) for item in payload]


def collect_aibetas_events(url: str, base: Path | None = None, html: str | None = None) -> list[dict]:
    if base is None:
        base = Path(__file__).resolve().parents[1]
    normalizer = load_normalizer(base)
    if html is None:
        html = fetch_url(url)
    raw_items = parse_aibetas_html(html, url)
    return [normalizer.normalize_contest(item) for item in raw_items]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: collect_contests.py <sample.json|aibetas_url>", file=sys.stderr)
        return 1
    base = Path(__file__).resolve().parents[1]
    target = argv[1]
    if target.startswith("http://") or target.startswith("https://"):
        contests = collect_aibetas_events(target, base=base)
    else:
        contests = collect_contests(Path(target), base=base)
    print(json.dumps(contests, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
