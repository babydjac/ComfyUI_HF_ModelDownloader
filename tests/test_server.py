"""Unit tests for server helpers (ComfyUI deps stubbed)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

EXTENSION_ROOT = Path(__file__).resolve().parent.parent


def _load_hfmd_server():
    """Load extension ``server.py`` as *hfmd_server* with ComfyUI shims."""
    fp = types.ModuleType("folder_paths")
    fp.models_dir = str(EXTENSION_ROOT / "_test_models")
    sys.modules["folder_paths"] = fp

    class _Routes:
        def get(self, _path):
            def _decorator(handler):
                return handler

            return _decorator

        def post(self, _path):
            def _decorator(handler):
                return handler

            return _decorator

    class _PromptServer:
        class _Instance:
            routes = _Routes()

        instance = _Instance()

    comfy_server = types.ModuleType("server")
    comfy_server.PromptServer = _PromptServer
    sys.modules["server"] = comfy_server

    spec = importlib.util.spec_from_file_location("hfmd_server", EXTENSION_ROOT / "server.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load extension server.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["hfmd_server"] = module
    spec.loader.exec_module(module)
    return module


hfmd = _load_hfmd_server()


class TestParseAndNormalize(unittest.TestCase):
    def test_parse_int_clamps(self) -> None:
        self.assertEqual(hfmd.parse_int("5", default=10, min_value=1, max_value=10), 5)
        self.assertEqual(hfmd.parse_int("99", default=10, min_value=1, max_value=10), 10)
        self.assertEqual(hfmd.parse_int("nope", default=3, min_value=1, max_value=10), 3)

    def test_parse_bool(self) -> None:
        self.assertFalse(hfmd.parse_bool(None))
        self.assertTrue(hfmd.parse_bool("true"))
        self.assertTrue(hfmd.parse_bool("1"))
        self.assertFalse(hfmd.parse_bool("false"))

    def test_normalize_owner_aliases(self) -> None:
        self.assertEqual(hfmd.normalize_owner("comfy_org"), "Comfy-Org")
        self.assertEqual(hfmd.normalize_owner("  kijai "), "Kijai")

    def test_normalize_owner_list_dedupes(self) -> None:
        self.assertEqual(
            hfmd.normalize_owner_list(["Kijai", "kijai", " Comfy-Org "]),
            ["Kijai", "Comfy-Org"],
        )


class TestRepoRevisionAndDownloadUrl(unittest.TestCase):
    def test_repo_tree_revision_prefers_sha(self) -> None:
        self.assertEqual(
            hfmd._repo_tree_revision({"sha": "59d8c015ac70bea0efa4a4619157085012fc2690"}),
            "59d8c015ac70bea0efa4a4619157085012fc2690",
        )

    def test_repo_tree_revision_falls_back_main(self) -> None:
        self.assertEqual(hfmd._repo_tree_revision({}), "main")
        self.assertEqual(hfmd._repo_tree_revision({"sha": ""}), "main")
        self.assertEqual(hfmd._repo_tree_revision({"sha": "short"}), "main")

    def test_download_url_uses_revision(self) -> None:
        item = {
            "repo_id": "org/model",
            "path": "weights/x.safetensors",
            "repo_revision": "59d8c015ac70bea0efa4a4619157085012fc2690",
        }
        url = hfmd.download_url(item)
        self.assertIn("/resolve/59d8c015ac70bea0efa4a4619157085012fc2690/", url)
        self.assertIn("weights/x.safetensors", url)

    def test_download_url_defaults_main(self) -> None:
        item = {"repo_id": "org/model", "path": "a/b.ckpt"}
        url = hfmd.download_url(item)
        self.assertIn("/resolve/main/", url)


class TestSanitizeAndCategorize(unittest.TestCase):
    def test_sanitize_filename(self) -> None:
        self.assertEqual(hfmd.sanitize_filename('foo<>:"|?*.bin'), "foo_.bin")

    def test_categorize_file_lora_in_path(self) -> None:
        repo: dict = {"id": "o/r", "tags": []}
        self.assertEqual(hfmd.categorize_file(repo, "pytorch_lora_weights.safetensors"), "loras")


class TestVerifyDownloadFile(unittest.TestCase):
    def test_verify_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ok, err = hfmd._verify_download_file({"size": 10}, str(Path(tmp) / "nope.bin"))
        self.assertFalse(ok)
        self.assertIn("missing", (err or "").lower())

    def test_verify_size_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ok.bin"
            path.write_bytes(b"12345")
            ok, err = hfmd._verify_download_file({"size": 5}, str(path))
        self.assertTrue(ok)
        self.assertIsNone(err)


if __name__ == "__main__":
    unittest.main()
