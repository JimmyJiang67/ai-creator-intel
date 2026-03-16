import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CollectTwitterTests(unittest.TestCase):
    def test_collect_twitter_reads_simple_sample_file(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_twitter.py", "collect_twitter")

        sample_items = [
            {
                "handle": "OpenAI",
                "text": "Introducing a new model release for creators and developers.",
                "url": "https://x.com/OpenAI/status/1",
                "likes": 1200,
                "retweets": 200,
                "created_at": "2026-03-16T10:00:00Z",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            sample_path = Path(tmpdir) / "twitter.json"
            sample_path.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            posts = module.collect_posts(sample_path, base)

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["handle"], "OpenAI")
        self.assertEqual(posts[0]["source_url"], "https://x.com/OpenAI/status/1")
        self.assertEqual(posts[0]["engagement"]["likes"], 1200)

    def test_collect_twitter_reads_twitterapiio_shape(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_twitter.py", "collect_twitter")

        payload = {
            "tweets": [
                {
                    "id": "2",
                    "text": "New prompt workflow for AI video generation.",
                    "createdAt": "2026-03-16T12:00:00Z",
                    "author": {"userName": "runwayml"},
                    "likeCount": 500,
                    "retweetCount": 80,
                    "replyCount": 10,
                    "quoteCount": 12,
                    "url": "https://x.com/runwayml/status/2",
                }
            ]
        }

        normalized = module.normalize_payload(payload)

        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]["handle"], "runwayml")
        self.assertEqual(normalized[0]["engagement"]["retweets"], 80)
        self.assertEqual(normalized[0]["source_url"], "https://x.com/runwayml/status/2")

    def test_collect_watchlist_posts_requires_api_key(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_twitter.py", "collect_twitter")

        old = os.environ.pop("TWITTERAPI_IO_KEY", None)
        try:
            with self.assertRaises(ValueError):
                module.collect_watchlist_posts(base)
        finally:
            if old is not None:
                os.environ["TWITTERAPI_IO_KEY"] = old

    def test_collect_watchlist_posts_uses_core_accounts_and_normalizes(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_twitter.py", "collect_twitter")

        old = os.environ.get("TWITTERAPI_IO_KEY")
        os.environ["TWITTERAPI_IO_KEY"] = "test-key"

        calls = []

        def fake_fetch(api_key: str, user_name: str, include_replies: bool):
            calls.append((api_key, user_name, include_replies))
            return {
                "tweets": [
                    {
                        "id": f"{user_name}-1",
                        "text": f"{user_name} released a new AI workflow.",
                        "createdAt": "2026-03-16T12:00:00Z",
                        "author": {"userName": user_name},
                        "likeCount": 100,
                        "retweetCount": 20,
                        "replyCount": 5,
                        "quoteCount": 1,
                        "url": f"https://x.com/{user_name}/status/1",
                    }
                ]
            }

        try:
            posts = module.collect_watchlist_posts(base, fetcher=fake_fetch, account_limit=2)
        finally:
            if old is None:
                del os.environ["TWITTERAPI_IO_KEY"]
            else:
                os.environ["TWITTERAPI_IO_KEY"] = old

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "test-key")
        self.assertFalse(calls[0][2])
        self.assertEqual(len(posts), 2)
        self.assertIn("handle", posts[0])
        self.assertIn("source_url", posts[0])

    def test_collect_browser_watchlist_posts_uses_core_and_candidate_accounts(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_twitter.py", "collect_twitter")

        calls = []

        def fake_scraper(profile_dir: Path, handle: str, window_hours: int, include_replies: bool):
            calls.append((profile_dir, handle, window_hours, include_replies))
            return [
                {
                    "handle": handle,
                    "text": f"{handle} posted a new workflow.",
                    "source_url": f"https://x.com/{handle}/status/1",
                    "created_at": "2026-03-16T12:00:00Z",
                    "content_type": "quote",
                    "engagement": {"likes": 10, "retweets": 2, "replies": 1, "quotes": 0},
                }
            ]

        posts = module.collect_browser_watchlist_posts(
            base,
            scraper=fake_scraper,
            profile_dir=Path("/tmp/x-profile"),
            window_hours=24,
            include_replies=False,
        )

        self.assertEqual(len(calls), 24)
        self.assertEqual(calls[0][0], Path("/tmp/x-profile"))
        self.assertEqual(calls[0][2], 24)
        self.assertFalse(calls[0][3])
        self.assertEqual(len(posts), 24)
        self.assertEqual(posts[0]["content_type"], "quote")
        self.assertTrue(any(call[1] == "AI_Jasonyu" for call in calls))
        self.assertTrue(any(call[1] == "aakashgupta" for call in calls))
        self.assertFalse(any(call[1] == "zarazhangrui" for call in calls))

    def test_normalize_browser_payload_preserves_content_type(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_twitter.py", "collect_twitter")

        payload = [
            {
                "handle": "OpenAI",
                "text": "Introducing a new model release.",
                "source_url": "https://x.com/OpenAI/status/1",
                "created_at": "2026-03-16T10:00:00Z",
                "content_type": "repost",
                "engagement": {"likes": 1200, "retweets": 200, "replies": 50, "quotes": 10},
            }
        ]

        normalized = module.normalize_payload(payload)

        self.assertEqual(normalized[0]["content_type"], "repost")


if __name__ == "__main__":
    unittest.main()
