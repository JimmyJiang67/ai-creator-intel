import importlib.util
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NormalizeContestTests(unittest.TestCase):
    def test_normalize_contest_maps_english_fields(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "normalize_contests.py", "normalize_contests")

        normalized = module.normalize_contest(
            {
                "title": "Global AI Film Challenge",
                "organizer": "Example Studio",
                "deadline": "2026-05-01",
                "prize": "$10,000",
                "requirements": "AI-generated short film",
                "official_url": "https://example.com/official",
                "source_url": "https://example.com/listing",
            }
        )

        self.assertEqual(normalized["title"], "Global AI Film Challenge")
        self.assertEqual(normalized["organizer"], "Example Studio")
        self.assertEqual(normalized["deadline"], "2026-05-01")
        self.assertEqual(normalized["official_url"], "https://example.com/official")
        self.assertEqual(normalized["source_url"], "https://example.com/listing")
        self.assertTrue(normalized["is_valid"])

    def test_normalize_contest_maps_chinese_aliases_and_fallbacks(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "normalize_contests.py", "normalize_contests")

        normalized = module.normalize_contest(
            {
                "赛事名称": "AIGC 视频大赛",
                "主办方": "某平台",
                "截止时间": "2026-06-30",
                "奖项": "一等奖 5 万元",
                "参赛要求": "原创 AIGC 视频",
                "报名链接": "https://example.cn/signup",
                "来源链接": "https://example.cn/aggregate",
            }
        )

        self.assertEqual(normalized["title"], "AIGC 视频大赛")
        self.assertEqual(normalized["organizer"], "某平台")
        self.assertEqual(normalized["deadline"], "2026-06-30")
        self.assertEqual(normalized["submission_url"], "https://example.cn/signup")
        self.assertEqual(normalized["source_url"], "https://example.cn/aggregate")
        self.assertEqual(normalized["official_url"], "https://example.cn/signup")
        self.assertTrue(normalized["is_valid"])


if __name__ == "__main__":
    unittest.main()
