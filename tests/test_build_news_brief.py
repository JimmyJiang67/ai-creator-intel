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


class BuildNewsBriefTests(unittest.TestCase):
    def test_build_payload_classifies_news_into_sections(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "OpenAI launches a new image model for creators",
                "summary": "Official launch signal",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/1",
                "published_at": "2026-03-16T10:00:00Z",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0,
            },
            {
                "title": "mem0 becomes popular on GitHub Trending",
                "summary": "Open-source memory layer for AI agents",
                "source_name": "GitHub Trending",
                "source_url": "https://github.com/mem0ai/mem0",
                "published_at": "2026-03-16T09:00:00Z",
                "topic_tags": ["repo_or_tool", "open_source"],
                "priority": 0.9,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        self.assertTrue(payload["sections"]["must_know_launches"])
        self.assertTrue(payload["sections"]["builder_moves"])
        self.assertEqual(payload["meta"]["mode"], "daily_brief")

    def test_build_payload_reads_default_news_source(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")
        real_manifest = load_module(base / "scripts" / "build_brief_manifest.py", "build_brief_manifest")

        class FakeCollectModule:
            @staticmethod
            def collect_default_news(base_path: Path):
                self = None
                return [
                    {
                        "title": "Product Hunt features a new AI video tool",
                        "summary": "Useful creator launch",
                        "source_name": "Product Hunt",
                        "source_url": "https://producthunt.com/posts/tool",
                        "published_at": "2026-03-16T10:00:00Z",
                        "topic_tags": ["product_launch", "tool_discovery"],
                        "priority": 0.86,
                    }
                ]

        def fake_loader(path: Path, name: str):
            if name == "collect_news":
                return FakeCollectModule
            if name == "build_brief_manifest":
                return real_manifest
            return load_module(path, name)

        original_loader = module.load_module
        module.load_module = fake_loader
        try:
            payload = module.build_payload(base, "news://default", mode="daily_brief")
        finally:
            module.load_module = original_loader

        self.assertTrue(payload["sections"]["must_know_launches"])

    def test_build_payload_filters_irrelevant_platform_news(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "OpenAI launches a new creator model",
                "summary": "Official launch",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/1",
                "published_at": "2026-03-16T10:00:00Z",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0,
                "kind": "official",
            },
            {
                "title": "Bus travel from Lima to Rio de Janeiro",
                "summary": "Unrelated article from Hacker News",
                "source_name": "Hacker News",
                "source_url": "https://example.com/bus",
                "published_at": "2026-03-16T09:00:00Z",
                "topic_tags": ["launch_discussion", "industry_signal"],
                "priority": 0.88,
                "kind": "platform",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        self.assertTrue(payload["sections"]["must_know_launches"])
        self.assertEqual(payload["sections"]["watch_next"], [])

    def test_build_payload_filters_news_outside_daily_window(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "OpenAI launches a new creator model",
                "summary": "Official launch",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/1",
                "published_at": "2026-03-16T10:00:00+00:00",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0,
                "kind": "official",
            },
            {
                "title": "Old OpenAI launch",
                "summary": "Too old for daily brief",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/old",
                "published_at": "2020-03-16T10:00:00+00:00",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0,
                "kind": "official",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        self.assertEqual(len(payload["sections"]["must_know_launches"]), 1)
        self.assertEqual(payload["sections"]["must_know_launches"][0]["source_url"], "https://openai.com/news/1")

    def test_build_payload_does_not_match_ai_inside_other_words(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "A new Bigfoot documentary helps explain our conspiracy-minded era",
                "summary": "Unrelated article from Hacker News",
                "source_name": "Hacker News",
                "source_url": "https://example.com/bigfoot",
                "published_at": "2026-03-16T09:00:00+00:00",
                "topic_tags": ["launch_discussion", "industry_signal"],
                "priority": 0.88,
                "kind": "platform",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        self.assertEqual(payload["sections"]["watch_next"], [])

    def test_build_payload_deduplicates_overlapping_items_by_normalized_title(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "Introducing Perplexity Computer",
                "summary": "Official launch",
                "source_name": "Perplexity Blog",
                "source_url": "https://www.perplexity.ai/hub/blog/introducing-perplexity-computer",
                "published_at": "2026-03-16T10:00:00+00:00",
                "topic_tags": ["product_launch", "search_agent"],
                "priority": 0.94,
                "kind": "official",
            },
            {
                "title": "Introducing Perplexity Computer ",
                "summary": "Same launch discussed on Product Hunt",
                "source_name": "Product Hunt",
                "source_url": "https://www.producthunt.com/posts/perplexity-computer",
                "published_at": "2026-03-16T11:00:00+00:00",
                "topic_tags": ["product_launch", "tool_discovery"],
                "priority": 0.86,
                "kind": "platform",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        launches = payload["sections"]["must_know_launches"]
        self.assertEqual(len(launches), 1)
        self.assertEqual(launches[0]["source"], "Perplexity Blog")

    def test_build_payload_balances_sources_before_filling_section(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "OpenAI launches model alpha",
                "summary": "Official launch",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/alpha",
                "published_at": "2026-03-16T10:00:00+00:00",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0,
                "kind": "official",
            },
            {
                "title": "OpenAI launches model beta",
                "summary": "Official launch",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/beta",
                "published_at": "2026-03-16T10:05:00+00:00",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0,
                "kind": "official",
            },
            {
                "title": "OpenAI launches model gamma",
                "summary": "Official launch",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/gamma",
                "published_at": "2026-03-16T10:10:00+00:00",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0,
                "kind": "official",
            },
            {
                "title": "Introducing Perplexity Computer",
                "summary": "Official launch",
                "source_name": "Perplexity Blog",
                "source_url": "https://www.perplexity.ai/hub/blog/introducing-perplexity-computer",
                "published_at": "2026-03-16T11:00:00+00:00",
                "topic_tags": ["product_launch", "search_agent"],
                "priority": 0.94,
                "kind": "official",
            },
            {
                "title": "Runway launches creator scenes",
                "summary": "Official launch",
                "source_name": "Runway News",
                "source_url": "https://runwayml.com/news/creator-scenes",
                "published_at": "2026-03-16T12:00:00+00:00",
                "topic_tags": ["product_launch", "aigc_video"],
                "priority": 0.93,
                "kind": "official",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        launches = payload["sections"]["must_know_launches"]
        self.assertEqual(len(launches), 5)
        self.assertEqual(launches[0]["source"], "OpenAI News")
        self.assertIn("Perplexity Blog", [item["source"] for item in launches[:3]])
        self.assertIn("Runway News", [item["source"] for item in launches[:3]])

    def test_build_payload_deduplicates_near_duplicate_launch_titles(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "Introducing Perplexity Computer",
                "summary": "Official launch",
                "source_name": "Perplexity Blog",
                "source_url": "https://www.perplexity.ai/hub/blog/introducing-perplexity-computer",
                "published_at": "2026-03-16T10:00:00+00:00",
                "topic_tags": ["product_launch", "search_agent"],
                "priority": 0.94,
                "kind": "official",
            },
            {
                "title": "Perplexity Computer launches for AI workflows",
                "summary": "Same launch reframed on Product Hunt",
                "source_name": "Product Hunt",
                "source_url": "https://www.producthunt.com/posts/perplexity-computer",
                "published_at": "2026-03-16T10:30:00+00:00",
                "topic_tags": ["product_launch", "tool_discovery"],
                "priority": 0.86,
                "kind": "platform",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        launches = payload["sections"]["must_know_launches"]
        self.assertEqual(len(launches), 1)
        self.assertEqual(launches[0]["source"], "Perplexity Blog")

    def test_build_payload_keeps_similar_but_distinct_launch_titles(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "OpenAI launches model alpha",
                "summary": "Official launch",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/alpha",
                "published_at": "2026-03-16T10:00:00+00:00",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0,
                "kind": "official",
            },
            {
                "title": "OpenAI launches model beta",
                "summary": "Separate official launch",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/beta",
                "published_at": "2026-03-16T11:00:00+00:00",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0,
                "kind": "official",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        launches = payload["sections"]["must_know_launches"]
        self.assertEqual(len(launches), 2)
        self.assertEqual({item["source_url"] for item in launches}, {"https://openai.com/news/alpha", "https://openai.com/news/beta"})

    def test_build_payload_filters_official_statement_style_news(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "Statement from Dario Amodei on our discussions with the Department of War",
                "summary": "Official statement on national security uses of AI.",
                "source_name": "Anthropic News",
                "source_url": "https://www.anthropic.com/news/statement-comments-secretary-war",
                "published_at": "2026-03-16T10:00:00+00:00",
                "topic_tags": ["model_release", "product_launch", "api"],
                "priority": 1.0,
                "kind": "official",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        self.assertEqual(payload["sections"]["must_know_launches"], [])
        self.assertEqual(payload["sections"]["watch_next"], [])

    def test_build_payload_keeps_official_research_and_product_news(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "Introducing Claude API workspace controls",
                "summary": "New admin and API features for enterprise builders.",
                "source_name": "Anthropic News",
                "source_url": "https://www.anthropic.com/news/claude-api-workspace-controls",
                "published_at": "2026-03-16T10:00:00+00:00",
                "topic_tags": ["product_launch", "api"],
                "priority": 1.0,
                "kind": "official",
            },
            {
                "title": "Research on safer agent planning",
                "summary": "New Anthropic research for safer agent workflows.",
                "source_name": "Anthropic News",
                "source_url": "https://www.anthropic.com/news/research-safer-agent-planning",
                "published_at": "2026-03-16T11:00:00+00:00",
                "topic_tags": ["research"],
                "priority": 1.0,
                "kind": "official",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        self.assertEqual(len(payload["sections"]["must_know_launches"]), 1)
        self.assertEqual(len(payload["sections"]["watch_next"]), 1)

    def test_build_payload_ranks_official_launches_ahead_of_platform_launches(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_news_brief.py", "build_news_brief")

        sample_items = [
            {
                "title": "Introducing Claude workspace controls",
                "summary": "Official admin launch for builders.",
                "source_name": "Anthropic News",
                "source_url": "https://www.anthropic.com/news/claude-workspace-controls",
                "published_at": "2026-03-16T10:00:00+00:00",
                "topic_tags": ["product_launch", "api"],
                "priority": 0.84,
                "kind": "official",
            },
            {
                "title": "AI website redesign with automated prompts, workflows, templates, and instant deployment",
                "summary": "Product Hunt launch with a broader discovery title.",
                "source_name": "Product Hunt",
                "source_url": "https://www.producthunt.com/products/ai-website-redesign",
                "published_at": "2026-03-16T10:30:00+00:00",
                "topic_tags": ["product_launch", "tool_discovery"],
                "priority": 0.95,
                "kind": "platform",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(target), mode="daily_brief")

        launches = payload["sections"]["must_know_launches"]
        self.assertEqual(len(launches), 2)
        self.assertEqual(launches[0]["source"], "Anthropic News")


if __name__ == "__main__":
    unittest.main()
