import importlib.util
import json
import signal
import tempfile
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CollectContestsTests(unittest.TestCase):
    def test_collect_contests_reads_and_normalizes_sample_file(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_contests.py", "collect_contests")

        sample_items = [
            {
                "赛事名称": "AIGC 创作挑战赛",
                "主办方": "示例主办方",
                "截止时间": "2026-07-01",
                "参赛要求": "提交原创作品",
                "报名链接": "https://example.cn/submit",
                "来源链接": "https://example.cn/list",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            sample_path = Path(tmpdir) / "contests.json"
            sample_path.write_text(json.dumps(sample_items, ensure_ascii=False), encoding="utf-8")

            collected = module.collect_contests(sample_path)

        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["title"], "AIGC 创作挑战赛")
        self.assertEqual(collected[0]["organizer"], "示例主办方")
        self.assertTrue(collected[0]["is_valid"])

    def test_parse_aibetas_html_extracts_structured_items(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_contests.py", "collect_contests")

        html = (base / "sample-data" / "aibetas-events-sample.html").read_text(encoding="utf-8")
        items = module.parse_aibetas_html(html, "https://www.aibetas.com.cn/aigc-events")

        self.assertGreaterEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "阿里云米兰冬奥会AIGC全球大赛")
        self.assertEqual(items[0]["organizer"], "阿里云")
        self.assertEqual(items[0]["deadline"], "2026年1月26日")
        self.assertEqual(items[0]["prize"], "米兰冬奥会门票")
        self.assertEqual(items[0]["source_url"], "https://www.aibetas.com.cn/aigc-events")
        self.assertTrue(items[0]["is_valid"])

    def test_parse_aibetas_html_handles_large_noisy_pages(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "collect_contests.py", "collect_contests")

        html = (base / "sample-data" / "aibetas-events-sample.html").read_text(encoding="utf-8")
        noisy_html = ("<style>" + ("x" * 500000) + "</style>") + html

        def timeout_handler(signum, frame):
            raise TimeoutError("parser timed out on noisy HTML")

        previous = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(2)
        try:
            items = module.parse_aibetas_html(noisy_html, "https://www.aibetas.com.cn/aigc-events")
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)

        self.assertGreaterEqual(len(items), 2)


if __name__ == "__main__":
    unittest.main()
