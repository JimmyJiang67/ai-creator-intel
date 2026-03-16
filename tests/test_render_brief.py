import importlib.util
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RenderBriefTests(unittest.TestCase):
    def test_render_brief_includes_all_sections_and_contests(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "render_brief.py", "render_brief")

        payload = {
            "meta": {
                "date": "2026-03-16",
                "mode": "daily_brief",
                "audience": "AI creator",
                "channels": ["feishu", "email"],
            },
            "sections": {
                "must_know_launches": [
                    {
                        "source": "@OpenAI",
                        "why_it_matters": "New release affects creator workflows.",
                        "suggested_angle": "Explain what actually changed.",
                        "source_url": "https://x.com/OpenAI",
                    }
                ],
                "builder_moves": [],
                "creator_workflows": [],
                "viral_aigc": [],
                "watch_next": [],
                "contest_opportunities": [
                    {
                        "title": "AIGC 视频大赛",
                        "organizer": "某平台",
                        "deadline": "2026-06-30",
                        "prize": "一等奖 5 万元",
                        "requirements": "原创 AIGC 视频",
                        "official_url": "https://example.cn/official",
                    }
                ],
            },
        }

        rendered = module.render_brief(payload)

        self.assertIn("# AI Creator Intel Brief", rendered)
        self.assertIn("## Must Know Launches", rendered)
        self.assertIn("## Contest Opportunities", rendered)
        self.assertIn("AIGC 视频大赛", rendered)
        self.assertIn("@OpenAI", rendered)


if __name__ == "__main__":
    unittest.main()
