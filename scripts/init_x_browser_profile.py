#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from pathlib import Path


DEFAULT_START_URL = "https://x.com/home"


def resolve_profile_dir(base: Path, cli_value: str | None = None) -> Path:
    if cli_value:
        return Path(cli_value).expanduser()
    env_value = os.getenv("X_BROWSER_PROFILE_DIR", "").strip()
    if env_value:
        return Path(env_value).expanduser()
    return base / "runtime" / "x-browser-profile"


def export_hint(profile_dir: Path) -> str:
    return f'export X_BROWSER_PROFILE_DIR="{profile_dir}"'


def bootstrap_profile(profile_dir: Path, start_url: str = DEFAULT_START_URL, headless: bool = False) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required to initialize the X browser profile") from exc

    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(str(profile_dir), headless=headless)
        try:
            page = context.new_page()
            page.goto(start_url, wait_until="domcontentloaded", timeout=30000)
            print(f"Opened X in a persistent browser profile at: {profile_dir}")
            print("Log into your X account in the opened browser window.")
            print("When login is complete and the home timeline is visible, return here and press Enter.")
            input()
        finally:
            context.close()


def main(argv: list[str]) -> int:
    base = Path(__file__).resolve().parents[1]
    profile_arg: str | None = None
    start_url = DEFAULT_START_URL
    headless = False

    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg == "--profile-dir":
            profile_arg = argv[index + 1]
            index += 2
        elif arg == "--start-url":
            start_url = argv[index + 1]
            index += 2
        elif arg == "--headless":
            headless = True
            index += 1
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            return 1

    profile_dir = resolve_profile_dir(base, profile_arg)
    bootstrap_profile(profile_dir, start_url=start_url, headless=headless)
    print("")
    print("Profile initialization finished.")
    print("Use this environment variable before running the browser collector:")
    print(export_hint(profile_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
