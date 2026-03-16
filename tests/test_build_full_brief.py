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


class BuildFullBriefTests(unittest.TestCase):
    def test_build_full_payload_merges_twitter_and_contests(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_full_brief.py", "build_full_brief")

        twitter_posts = [
            {
                "handle": "OpenAI",
                "text": "Introducing a major model release for developers.",
                "source_url": "https://x.com/OpenAI/status/1",
                "created_at": "2026-03-16T10:00:00Z",
                "engagement": {"likes": 1200, "retweets": 200, "replies": 50, "quotes": 10},
            }
        ]
        contests = [
            {
                "赛事名称": "AIGC 创作挑战赛",
                "主办方": "示例主办方",
                "截止时间": "2026年07月01日",
                "奖项": "一等奖 5 万元",
                "参赛要求": "提交原创作品",
                "报名链接": "https://example.cn/submit",
                "来源链接": "https://example.cn/list"
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            twitter_path = tmp / "twitter.json"
            contest_path = tmp / "contests.json"
            twitter_path.write_text(json.dumps(twitter_posts, ensure_ascii=False), encoding="utf-8")
            contest_path.write_text(json.dumps(contests, ensure_ascii=False), encoding="utf-8")

            payload = module.build_full_payload(
                base,
                mode="daily_brief",
                twitter_source=str(twitter_path),
                contest_source=str(contest_path),
            )

        self.assertEqual(payload["meta"]["mode"], "daily_brief")
        self.assertTrue(payload["sections"]["must_know_launches"])
        self.assertEqual(payload["sections"]["contest_opportunities"][0]["title"], "AIGC 创作挑战赛")

    def test_build_full_payload_merges_news_and_contests(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_full_brief.py", "build_full_brief")

        news_items = [
            {
                "title": "OpenAI launches a new creator model",
                "summary": "Official launch",
                "source_name": "OpenAI News",
                "source_url": "https://openai.com/news/1",
                "published_at": "2026-03-16T10:00:00Z",
                "topic_tags": ["model_release", "product_launch"],
                "priority": 1.0
            }
        ]
        contests = [
            {
                "赛事名称": "AIGC 创作挑战赛",
                "主办方": "示例主办方",
                "截止时间": "2026年07月01日",
                "奖项": "一等奖 5 万元",
                "参赛要求": "提交原创作品",
                "报名链接": "https://example.cn/submit",
                "来源链接": "https://example.cn/list"
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            news_path = tmp / "news.json"
            contest_path = tmp / "contests.json"
            news_path.write_text(json.dumps(news_items, ensure_ascii=False), encoding="utf-8")
            contest_path.write_text(json.dumps(contests, ensure_ascii=False), encoding="utf-8")

            payload = module.build_full_payload(
                base,
                mode="daily_brief",
                news_source=str(news_path),
                contest_source=str(contest_path),
            )

        self.assertTrue(payload["sections"]["must_know_launches"])
        self.assertEqual(payload["sections"]["contest_opportunities"][0]["title"], "AIGC 创作挑战赛")

    def test_render_full_payload_returns_markdown(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_full_brief.py", "build_full_brief")

        payload = {
            "meta": {
                "date": "2026-03-16",
                "mode": "daily_brief",
                "audience": "AI creator",
                "channels": ["feishu", "email"],
            },
            "sections": {
                "must_know_launches": [],
                "builder_moves": [],
                "creator_workflows": [],
                "viral_aigc": [],
                "watch_next": [],
                "contest_opportunities": [
                    {
                        "title": "Contest A",
                        "organizer": "Org A",
                        "deadline": "2026-04-01",
                        "prize": "$1000",
                        "requirements": "Req",
                        "official_url": "https://example.com/a",
                    }
                ],
            },
        }

        rendered = module.render_full_payload(base, payload)

        self.assertIn("# AI Creator Intel Brief", rendered)
        self.assertIn("## Contest Opportunities", rendered)
        self.assertIn("Contest A", rendered)


if __name__ == "__main__":
    unittest.main()
