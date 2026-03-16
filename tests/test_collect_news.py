import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CollectNewsTests(unittest.TestCase):
    def test_parse_rss_feed_extracts_items(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_news.py", "collect_news")

        xml_payload = """
        <rss version="2.0">
          <channel>
            <item>
              <title>OpenAI launches a new image model</title>
              <link>https://openai.com/news/item-1</link>
              <pubDate>Mon, 16 Mar 2026 10:00:00 +0000</pubDate>
              <description>New release for creators.</description>
            </item>
          </channel>
        </rss>
        """.strip()

        source = {
            "name": "OpenAI News",
            "priority": 1.0,
            "topic_tags": ["model_release", "product_launch"],
            "fetch": {"url": "https://openai.com/news/rss.xml", "format": "rss", "parser": "rss"},
        }

        items = module.parse_rss_feed(xml_payload.encode("utf-8"), source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_name"], "OpenAI News")
        self.assertEqual(items[0]["source_url"], "https://openai.com/news/item-1")
        self.assertIn("model_release", items[0]["topic_tags"])

    def test_parse_github_trending_extracts_repo_rows(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_news.py", "collect_news")

        html = """
        <article class="Box-row">
          <h2><a href="/mem0ai/mem0"> mem0ai / mem0 </a></h2>
          <p>Memory layer for AI agents.</p>
        </article>
        """.strip()

        source = {
            "name": "GitHub Trending",
            "priority": 0.9,
            "topic_tags": ["repo_or_tool", "open_source"],
            "fetch": {"url": "https://github.com/trending", "format": "html", "parser": "github_trending"},
        }

        items = module.parse_github_trending(html, source)

        self.assertEqual(len(items), 1)
        self.assertIn("mem0ai/mem0", items[0]["title"])
        self.assertEqual(items[0]["source_url"], "https://github.com/mem0ai/mem0")

    def test_parse_anthropic_news_extracts_unique_news_links(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_news.py", "collect_news")

        html = """
        <a href="/news/claude-sonnet-4-6">Introducing Sonnet 4.6</a>
        <a href="/news/claude-sonnet-4-6">Introducing Sonnet 4.6</a>
        <a href="/news/claude-is-a-space-to-think"><span>Claude is a space to think</span></a>
        <a href="/news">Newsroom</a>
        """.strip()

        source = {
            "name": "Anthropic News",
            "priority": 1.0,
            "topic_tags": ["model_release", "product_launch", "api"],
            "fetch": {"url": "https://www.anthropic.com/news", "format": "html", "parser": "anthropic_news"},
        }

        items = module.parse_anthropic_news(html, source)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source_url"], "https://www.anthropic.com/news/claude-sonnet-4-6")
        self.assertIn("Sonnet 4.6", items[0]["title"])

    def test_parse_runway_news_extracts_unique_news_links(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_news.py", "collect_news")

        html = """
        <a href="news/introducing-runway-characters">Introducing Runway Characters</a>
        <a href="news/introducing-runway-characters">Introducing Runway Characters</a>
        <a href="/news/introducing-the-runway-api">Introducing the Runway API</a>
        <a href="/research/introducing-runway-gwm-1">Research</a>
        """.strip()

        source = {
            "name": "Runway News",
            "priority": 0.93,
            "topic_tags": ["aigc_video", "product_launch"],
            "fetch": {"url": "https://runwayml.com/news/", "format": "html", "parser": "runway_news"},
        }

        items = module.parse_runway_news(html, source)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source_url"], "https://runwayml.com/news/introducing-runway-characters")
        self.assertIn("Runway Characters", items[0]["title"])

    def test_parse_elevenlabs_blog_extracts_unique_blog_posts(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_news.py", "collect_news")

        html = """
        <a href="/blog/introducing-elevenlabs-image-and-video">Introducing ElevenLabs image and video</a>
        <a href="/blog/introducing-elevenlabs-image-and-video">Introducing ElevenLabs image and video</a>
        <a href="/blog/introducing-scribe-v2">Introducing Scribe v2</a>
        <a href="/blog/category/product">Product</a>
        <a href="/blog/page/2">Next</a>
        <a href="/blog">Blog</a>
        """.strip()

        source = {
            "name": "ElevenLabs Blog",
            "priority": 0.9,
            "topic_tags": ["voice", "audio", "product_launch"],
            "fetch": {"url": "https://elevenlabs.io/blog", "format": "html", "parser": "elevenlabs_blog"},
        }

        items = module.parse_elevenlabs_blog(html, source)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source_url"], "https://elevenlabs.io/blog/introducing-elevenlabs-image-and-video")
        self.assertIn("ElevenLabs image and video", items[0]["title"])

    def test_parse_perplexity_blog_extracts_posts_from_search_index(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_news.py", "collect_news")

        html = """
        <meta name="framer-search-index" content="https://framerusercontent.com/sites/example/searchIndex-live.json">
        <meta name="framer-search-index-fallback" content="https://framerusercontent.com/sites/example/searchIndex-fallback.json">
        """.strip()

        search_index_payload = """
        {
          "/hub/blog/introducing-perplexity-computer": {
            "title": "Introducing Perplexity Computer",
            "description": "General-purpose digital worker for AI workflows.",
            "h1": ["Introducing Perplexity Computer"],
            "p": ["Written by", "Perplexity Team", "Published on", "Feb 25, 2026"],
            "url": "/hub/blog/introducing-perplexity-computer"
          },
          "/hub/blog/how-people-use-ai-agents": {
            "title": "How people use AI agents",
            "description": "Observed behavior across AI agent workflows.",
            "h1": [],
            "p": ["Published on", "Mar 11, 2026"],
            "url": "/hub/blog/how-people-use-ai-agents"
          },
          "/hub/use-cases/research-your-investments": {
            "title": "Research your investments",
            "description": "Use case entry",
            "h1": ["Research your investments"],
            "p": ["Published on", "Mar 01, 2026"],
            "url": "/hub/use-cases/research-your-investments"
          }
        }
        """.strip()

        fetched_urls: list[str] = []

        def fake_fetch(url: str, headers: dict | None = None) -> bytes:
            fetched_urls.append(url)
            if url.endswith("searchIndex-live.json"):
                return search_index_payload.encode("utf-8")
            raise AssertionError(f"Unexpected URL: {url}")

        source = {
            "name": "Perplexity Blog",
            "kind": "official",
            "priority": 0.94,
            "topic_tags": ["product_launch", "search_agent"],
            "fetch": {"url": "https://hub-prod.perplexity.ai/hub", "format": "html", "parser": "perplexity_blog"},
        }

        items = module.parse_perplexity_blog(html, source, fetcher=fake_fetch)

        self.assertEqual(fetched_urls, ["https://framerusercontent.com/sites/example/searchIndex-live.json"])
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source_url"], "https://www.perplexity.ai/hub/blog/introducing-perplexity-computer")
        self.assertEqual(items[0]["published_at"], "2026-02-25T00:00:00+00:00")
        self.assertIn("search_agent", items[0]["topic_tags"])
        self.assertEqual(items[1]["title"], "How people use AI agents")

    def test_collect_default_news_reads_enabled_sources(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_news.py", "collect_news")

        def fake_fetch(url: str, headers: dict | None = None) -> bytes:
            if "rss.xml" in url or "producthunt.com/feed" in url or "news.ycombinator.com/rss" in url or "google-deepmind/rss/" in url:
                return b"""
                <rss version='2.0'><channel><item>
                <title>AI model launch</title>
                <link>https://example.com/item</link>
                <pubDate>Mon, 16 Mar 2026 10:00:00 +0000</pubDate>
                <description>Signal</description>
                </item></channel></rss>
                """
            if "anthropic.com/news" in url:
                return b"""
                <a href='/news/claude-sonnet-4-6'>Introducing Sonnet 4.6</a>
                <a href='/news/claude-is-a-space-to-think'>Claude is a space to think</a>
                """
            if "hub-prod.perplexity.ai/hub" in url:
                return b"""
                <meta name='framer-search-index' content='https://framerusercontent.com/sites/example/searchIndex-live.json'>
                """
            if "framerusercontent.com/sites/example/searchIndex-live.json" in url:
                return b"""
                {
                  "/hub/blog/introducing-perplexity-computer": {
                    "title": "Introducing Perplexity Computer",
                    "description": "General-purpose digital worker for AI workflows.",
                    "h1": ["Introducing Perplexity Computer"],
                    "p": ["Published on", "Feb 25, 2026"],
                    "url": "/hub/blog/introducing-perplexity-computer"
                  }
                }
                """
            if "runwayml.com/news" in url:
                return b"""
                <a href='news/introducing-runway-characters'>Introducing Runway Characters</a>
                <a href='/news/introducing-the-runway-api'>Introducing the Runway API</a>
                """
            if "elevenlabs.io/blog" in url:
                return b"""
                <a href='/blog/introducing-elevenlabs-image-and-video'>Introducing ElevenLabs image and video</a>
                <a href='/blog/introducing-scribe-v2'>Introducing Scribe v2</a>
                <a href='/blog/category/product'>Product</a>
                """
            if "github.com/trending" in url:
                return b"""
                <article class='Box-row'>
                  <h2><a href='/org/repo'> org / repo </a></h2>
                  <p>AI repo</p>
                </article>
                """
            raise AssertionError(f"Unexpected URL: {url}")

        items = module.collect_default_news(base, fetcher=fake_fetch)

        self.assertGreaterEqual(len(items), 12)
        self.assertTrue(any(item["source_name"] == "OpenAI News" for item in items))
        self.assertTrue(any(item["source_name"] == "Anthropic News" for item in items))
        self.assertTrue(any(item["source_name"] == "Perplexity Blog" for item in items))
        self.assertTrue(any(item["source_name"] == "Runway News" for item in items))
        self.assertTrue(any(item["source_name"] == "ElevenLabs Blog" for item in items))
        self.assertTrue(any(item["source_name"] == "GitHub Trending" for item in items))

    def test_collect_news_reads_local_json_file(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_news.py", "collect_news")

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "news.json"
            target.write_text(
                """
                [
                  {
                    "title": "Runway launches new video feature",
                    "summary": "Creator update",
                    "source_name": "Runway News",
                    "source_url": "https://runwayml.com/news/1",
                    "published_at": "2026-03-16T10:00:00Z",
                    "topic_tags": ["product_launch", "aigc_video"],
                    "priority": 0.9
                  }
                ]
                """.strip(),
                encoding="utf-8",
            )

            items = module.collect_news(Path(target))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_name"], "Runway News")


if __name__ == "__main__":
    unittest.main()
