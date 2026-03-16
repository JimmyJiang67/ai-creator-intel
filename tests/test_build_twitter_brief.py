import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildTwitterBriefTests(unittest.TestCase):
    def test_build_payload_classifies_posts_into_sections(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_twitter_brief.py", "build_twitter_brief")

        sample_posts = [
            {
                "handle": "OpenAI",
                "text": "Introducing a major model release for developers.",
                "source_url": "https://x.com/OpenAI/status/1",
                "created_at": "2026-03-16T10:00:00Z",
                "engagement": {"likes": 1200, "retweets": 200, "replies": 50, "quotes": 10},
            },
            {
                "handle": "AI_Jasonyu",
                "text": "Here is a reusable prompt workflow for creators using Claude.",
                "source_url": "https://x.com/AI_Jasonyu/status/2",
                "created_at": "2026-03-16T11:00:00Z",
                "engagement": {"likes": 400, "retweets": 80, "replies": 10, "quotes": 2},
            },
            {
                "handle": "runwayml",
                "text": "Viral AI video workflow with a new generation pipeline.",
                "source_url": "https://x.com/runwayml/status/3",
                "created_at": "2026-03-16T12:00:00Z",
                "engagement": {"likes": 900, "retweets": 150, "replies": 30, "quotes": 20},
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            sample_path = Path(tmpdir) / "posts.json"
            sample_path.write_text(json.dumps(sample_posts, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(sample_path), mode="daily_brief")

        self.assertEqual(payload["meta"]["mode"], "daily_brief")
        self.assertTrue(payload["sections"]["must_know_launches"])
        self.assertTrue(payload["sections"]["creator_workflows"])
        self.assertTrue(payload["sections"]["viral_aigc"])

    def test_build_payload_reads_browser_watchlist_source(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_twitter_brief.py", "build_twitter_brief")
        real_manifest = load_module(base / "scripts" / "build_brief_manifest.py", "build_brief_manifest")

        class FakeCollectModule:
            @staticmethod
            def collect_browser_watchlist_posts(base_path: Path):
                self = None
                return [
                    {
                        "handle": "runwayml",
                        "text": "Viral AI video workflow for creators.",
                        "source_url": "https://x.com/runwayml/status/3",
                        "created_at": "2026-03-16T12:00:00Z",
                        "content_type": "quote",
                        "engagement": {"likes": 900, "retweets": 150, "replies": 30, "quotes": 20},
                    }
                ]

        def fake_loader(path: Path, name: str):
            if name == "collect_twitter":
                return FakeCollectModule
            if name == "build_brief_manifest":
                return real_manifest
            return load_module(path, name)

        original_loader = module.load_module
        module.load_module = fake_loader
        try:
            payload = module.build_payload(base, "xbrowser://watchlist", mode="daily_brief")
        finally:
            module.load_module = original_loader

        self.assertEqual(payload["meta"]["mode"], "daily_brief")
        self.assertTrue(payload["sections"]["viral_aigc"])


if __name__ == "__main__":
    unittest.main()
