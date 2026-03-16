import importlib.util
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildBriefManifestTests(unittest.TestCase):
    def test_build_manifest_combines_twitter_news_and_contests(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "build_brief_manifest.py", "build_brief_manifest")

        manifest = module.build_manifest(base, mode="daily_brief")

        self.assertEqual(manifest["mode"], "daily_brief")
        self.assertEqual(manifest["delivery"]["channels"], ["feishu", "email"])
        self.assertIn("must_know_launches", manifest["brief"]["section_order"])
        self.assertIn("contest_opportunities", manifest["brief"]["section_order"])
        self.assertGreater(manifest["twitter"]["account_count"], 0)
        self.assertGreater(manifest["news"]["source_count"], 0)
        self.assertGreater(manifest["contests"]["source_count"], 0)
        self.assertIn("AIBetas AIGC Events", manifest["contests"]["source_names"])


if __name__ == "__main__":
    unittest.main()
