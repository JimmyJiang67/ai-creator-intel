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


class BuildContestBriefTests(unittest.TestCase):
    def test_select_contests_prefers_earlier_deadlines_and_limits_daily_brief(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_contest_brief.py", "build_contest_brief")

        contests = [
            {
                "title": "Contest C",
                "organizer": "Org C",
                "deadline": "2026年08月01日",
                "prize": "$500",
                "requirements": "Req",
                "official_url": "https://example.com/c",
                "source_url": "https://example.com/c-list",
                "is_valid": True,
            },
            {
                "title": "Contest A",
                "organizer": "Org A",
                "deadline": "2026年04月01日",
                "prize": "$1000",
                "requirements": "Req",
                "official_url": "https://example.com/a",
                "source_url": "https://example.com/a-list",
                "is_valid": True,
            },
            {
                "title": "Contest B",
                "organizer": "Org B",
                "deadline": "2026年05月01日",
                "prize": "$800",
                "requirements": "Req",
                "official_url": "https://example.com/b",
                "source_url": "https://example.com/b-list",
                "is_valid": True,
            },
            {
                "title": "Contest Invalid",
                "organizer": "Org X",
                "deadline": None,
                "prize": "$100",
                "requirements": "Req",
                "official_url": "https://example.com/x",
                "source_url": "https://example.com/x-list",
                "is_valid": False,
            },
        ]

        selected = module.select_contests(contests, max_items=2)

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["title"], "Contest A")
        self.assertEqual(selected[1]["title"], "Contest B")

    def test_build_payload_from_contest_file_includes_contest_section(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_contest_brief.py", "build_contest_brief")

        raw_items = [
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
            sample_path = Path(tmpdir) / "contests.json"
            sample_path.write_text(json.dumps(raw_items, ensure_ascii=False), encoding="utf-8")
            payload = module.build_payload(base, str(sample_path), mode="daily_brief")

        self.assertEqual(payload["meta"]["mode"], "daily_brief")
        self.assertEqual(payload["meta"]["channels"], ["feishu", "email"])
        self.assertIn("contest_opportunities", payload["sections"])
        self.assertEqual(payload["sections"]["contest_opportunities"][0]["title"], "AIGC 创作挑战赛")


if __name__ == "__main__":
    unittest.main()
