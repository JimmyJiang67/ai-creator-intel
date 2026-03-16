import contextlib
import importlib.util
import io
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


class InitXBrowserProfileTests(unittest.TestCase):
    def test_resolve_profile_dir_prefers_cli_value(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "init_x_browser_profile.py", "init_x_browser_profile")

        profile = module.resolve_profile_dir(base, "/tmp/custom-x-profile")

        self.assertEqual(profile, Path("/tmp/custom-x-profile"))

    def test_resolve_profile_dir_uses_workspace_default_when_env_missing(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "init_x_browser_profile.py", "init_x_browser_profile")

        old = os.environ.pop("X_BROWSER_PROFILE_DIR", None)
        try:
            profile = module.resolve_profile_dir(base)
        finally:
            if old is not None:
                os.environ["X_BROWSER_PROFILE_DIR"] = old

        self.assertEqual(profile, base / "runtime" / "x-browser-profile")

    def test_main_prints_export_hint_after_bootstrap(self):
        base = Path(__file__).resolve().parents[1]
        module = load_module(base / "scripts" / "init_x_browser_profile.py", "init_x_browser_profile")

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "x-profile"
            calls = []

            def fake_bootstrap(profile_dir: Path, start_url: str, headless: bool):
                calls.append((profile_dir, start_url, headless))

            original = module.bootstrap_profile
            module.bootstrap_profile = fake_bootstrap
            stdout = io.StringIO()
            try:
                with contextlib.redirect_stdout(stdout):
                    exit_code = module.main(["init_x_browser_profile.py", "--profile-dir", str(target)])
            finally:
                module.bootstrap_profile = original

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0][0], target)
        self.assertEqual(calls[0][1], "https://x.com/home")
        self.assertFalse(calls[0][2])
        self.assertIn("X_BROWSER_PROFILE_DIR", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
