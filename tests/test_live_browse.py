"""Tests for live-browse item normalization and repo-row shaping.

These avoid importing ComfyUI: the modules under test pull in `folder_paths`,
`aiohttp` and `server`, so the pieces that matter are exercised through small stubs.
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _install_stubs() -> None:
    if "folder_paths" not in sys.modules:
        fp = types.ModuleType("folder_paths")
        fp.models_dir = "/tmp/hfmd-test-models"
        fp.folder_names_and_paths = {}
        sys.modules["folder_paths"] = fp

    if "server" not in sys.modules:
        srv = types.ModuleType("server")

        class _Routes:
            def get(self, *_a, **_k):
                return lambda fn: fn

            def post(self, *_a, **_k):
                return lambda fn: fn

        class _Instance:
            routes = _Routes()

        class PromptServer:
            instance = _Instance()

        srv.PromptServer = PromptServer
        sys.modules["server"] = srv


def _load_package() -> tuple:
    """Load server.py and live_browse.py as a synthetic package.

    They cannot simply be imported: `server.py` does `from server import PromptServer`,
    meaning ComfyUI's server module, so the local file must not occupy that name.
    """
    import importlib.util

    pkg_name = "hfmd_pkg"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(ROOT)]
    sys.modules[pkg_name] = pkg

    loaded = {}
    for mod_name in ("server", "live_browse"):
        full = f"{pkg_name}.{mod_name}"
        spec = importlib.util.spec_from_file_location(full, ROOT / f"{mod_name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[full] = module
        spec.loader.exec_module(module)
        setattr(pkg, mod_name, module)
        loaded[mod_name] = module
    return loaded["server"], loaded["live_browse"]


_install_stubs()

try:
    core, live_browse = _load_package()
except Exception as exc:  # pragma: no cover
    raise unittest.SkipTest(f"cannot load package modules: {exc}") from exc


class NormalizeLiveItemsTests(unittest.TestCase):
    def good(self, **over):
        row = {
            "repo_id": "Comfy-Org/Krea-2",
            "path": "diffusion_models/krea2_turbo_bf16.safetensors",
            "size": 26283332608,
            "category": "diffusion_models",
            "family": "KREA",
            "title": "Krea2 Turbo",
        }
        row.update(over)
        return row

    def test_keeps_a_valid_row(self):
        out = core.normalize_live_items([self.good()])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["repo_id"], "Comfy-Org/Krea-2")
        self.assertEqual(out[0]["filename"], "krea2_turbo_bf16.safetensors")
        self.assertEqual(out[0]["repo_name"], "Krea-2")
        self.assertEqual(out[0]["repo_revision"], "main")

    def test_rejects_non_model_extensions(self):
        self.assertEqual(core.normalize_live_items([self.good(path="README.md")]), [])
        self.assertEqual(core.normalize_live_items([self.good(path="config.json")]), [])

    def test_accepts_every_known_model_extension(self):
        for ext in (".safetensors", ".ckpt", ".pt", ".pth", ".gguf"):
            with self.subTest(ext=ext):
                out = core.normalize_live_items([self.good(path=f"weights{ext}")])
                self.assertEqual(len(out), 1, ext)

    def test_rejects_path_traversal(self):
        for bad in ("../secret.safetensors", "a/../../b.safetensors"):
            with self.subTest(path=bad):
                self.assertEqual(core.normalize_live_items([self.good(path=bad)]), [])

    def test_strips_leading_slash(self):
        out = core.normalize_live_items([self.good(path="/vae/x.safetensors")])
        self.assertEqual(out[0]["path"], "vae/x.safetensors")

    def test_rejects_malformed_repo_ids(self):
        for bad in ("", "noslash", "too/many/slashes", "/", "owner/"):
            with self.subTest(repo=bad):
                self.assertEqual(core.normalize_live_items([self.good(repo_id=bad)]), [])

    def test_unknown_category_falls_back_to_checkpoints(self):
        out = core.normalize_live_items([self.good(category="../../etc")])
        self.assertEqual(out[0]["category"], "checkpoints")
        out = core.normalize_live_items([self.good(category="not_a_real_dir")])
        self.assertEqual(out[0]["category"], "checkpoints")

    def test_known_categories_survive(self):
        for category in ("loras", "vae", "text_encoders", "controlnet"):
            with self.subTest(category=category):
                out = core.normalize_live_items([self.good(category=category)])
                self.assertEqual(out[0]["category"], category)

    def test_dedupes_same_repo_and_path(self):
        out = core.normalize_live_items([self.good(), self.good(), self.good(path="vae/a.safetensors")])
        self.assertEqual(len(out), 2)

    def test_bad_size_becomes_zero(self):
        self.assertEqual(core.normalize_live_items([self.good(size="huge")])[0]["size"], 0)
        self.assertEqual(core.normalize_live_items([self.good(size=None)])[0]["size"], 0)

    def test_ignores_non_dict_rows(self):
        self.assertEqual(core.normalize_live_items(["nope", None, 42]), [])

    def test_missing_family_defaults(self):
        row = self.good()
        row.pop("family")
        self.assertEqual(core.normalize_live_items([row])[0]["family"], "MISC")

    def test_download_url_is_built_from_normalized_row(self):
        row = core.normalize_live_items([self.good(repo_revision="refs/pr/1")])[0]
        url = core.download_url(row)
        self.assertIn("Comfy-Org/Krea-2/resolve/", url)
        self.assertIn("krea2_turbo_bf16.safetensors", url)


class LiveBrowseModuleTests(unittest.TestCase):
    def setUp(self):
        self.lb = live_browse

    def test_repo_row_shape(self):
        row = self.lb._repo_row(
            {
                "id": "Comfy-Org/Krea-2",
                "downloads": 1234,
                "likes": 56,
                "tags": ["comfyui", "safetensors"],
                "pipeline_tag": "text-to-image",
            }
        )
        self.assertEqual(row["owner"], "Comfy-Org")
        self.assertEqual(row["name"], "Krea-2")
        self.assertEqual(row["downloads"], 1234)
        self.assertEqual(row["pipeline"], "text-to-image")
        self.assertTrue(row["url"].endswith("/Comfy-Org/Krea-2"))

    def test_model_file_skips_non_weights(self):
        repo = {"id": "a/b", "tags": []}
        self.assertIsNone(self.lb._model_file(repo, {"path": "README.md"}))
        self.assertIsNone(self.lb._model_file(repo, {"path": ""}))

    def test_model_file_reads_lfs_size(self):
        repo = {"id": "a/b", "tags": []}
        row = self.lb._model_file(repo, {"path": "vae/x.safetensors", "lfs": {"size": 99}})
        self.assertEqual(row["size"], 99)
        self.assertEqual(row["repo_id"], "a/b")

    def test_sort_fields_are_known_hub_keys(self):
        self.assertEqual(self.lb.SORT_FIELDS["downloads"], "downloads")
        self.assertEqual(self.lb.SORT_FIELDS["trending"], "trendingScore")

    def test_cache_helpers_expire(self):
        cache = {}
        self.lb._store(cache, "k", "v")
        self.assertEqual(self.lb._cached(cache, "k", 60), "v")
        self.assertIsNone(self.lb._cached(cache, "k", 0))
        self.assertIsNone(self.lb._cached(cache, "missing", 60))

    def test_aria2_state_reports_a_bool(self):
        self.assertIsInstance(self.lb.aria2_state()["installed"], bool)


class InstalledDetectionTests(unittest.TestCase):
    """Weights fetched by hand land in models/<category>/, not <category>/<family>/."""

    def setUp(self):
        import shutil
        import tempfile

        self.lb = live_browse
        self.tmp = Path(tempfile.mkdtemp(prefix="hfmd-models-"))
        self._real_root = core.models_root
        core.models_root = lambda: self.tmp
        self.addCleanup(setattr, core, "models_root", self._real_root)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def row(self, **over):
        base = {"filename": "krea2_turbo_bf16.safetensors", "category": "diffusion_models", "size": 11}
        base.update(over)
        return base

    def write(self, rel: str, data: bytes = b"x" * 11) -> Path:
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_finds_file_in_category_root(self):
        target = self.write("diffusion_models/krea2_turbo_bf16.safetensors")
        self.assertEqual(self.lb._installed_in_category_root(self.row()), str(target))

    def test_finds_file_one_level_deeper(self):
        target = self.write("diffusion_models/KREA/krea2_turbo_bf16.safetensors")
        self.assertEqual(self.lb._installed_in_category_root(self.row()), str(target))

    def test_size_mismatch_is_not_a_match(self):
        self.write("diffusion_models/krea2_turbo_bf16.safetensors", b"short")
        self.assertIsNone(self.lb._installed_in_category_root(self.row()))

    def test_unknown_size_still_matches_by_name(self):
        target = self.write("diffusion_models/krea2_turbo_bf16.safetensors")
        self.assertEqual(self.lb._installed_in_category_root(self.row(size=0)), str(target))

    def test_missing_category_dir(self):
        self.assertIsNone(self.lb._installed_in_category_root(self.row(category="loras")))

    def test_missing_filename(self):
        self.assertIsNone(self.lb._installed_in_category_root(self.row(filename="")))

    def test_wrong_category_does_not_match(self):
        self.write("diffusion_models/krea2_turbo_bf16.safetensors")
        self.assertIsNone(self.lb._installed_in_category_root(self.row(category="vae")))


class UpscalerDiscoveryTests(unittest.TestCase):
    """Real repo metadata: ESRGAN publishers report 0 downloads and no ComfyUI tags."""

    KIM = {
        "id": "Kim2091/UltraSharp",
        "downloads": 0,
        "likes": 66,
        "tags": ["onnx", "pytorch", "super-resolution", "image-to-image", "region:us"],
    }
    GEMASAI = {"id": "gemasai/4x_NMKD-Siax_200k", "downloads": 0, "likes": 86, "tags": ["region:us"]}
    UWG = {"id": "uwg/upscaler", "downloads": 0, "likes": 729, "tags": ["onnx", "Upscalers", "en"]}
    UNPOPULAR = {"id": "someone/4xRandom", "downloads": 0, "likes": 1, "tags": []}

    def test_owners_include_the_upscaler_publishers(self):
        for owner in ("uwg", "Kim2091", "gemasai", "Phips"):
            self.assertIn(owner, core.DEFAULT_OWNERS, owner)

    def test_super_resolution_tag_is_recognised(self):
        self.assertTrue(core.looks_like_upscaler(self.KIM))
        self.assertTrue(core.looks_like_upscaler(self.UWG))

    def test_model_name_alone_is_enough(self):
        self.assertTrue(core.looks_like_upscaler(self.GEMASAI))
        self.assertTrue(core.looks_like_upscaler({"id": "a/b"}, "ESRGAN/4x-UltraSharp.pth"))
        self.assertTrue(core.looks_like_upscaler({"id": "a/b"}, "4x_foolhardy_Remacri.pth"))

    def test_these_repos_now_survive_the_index_filter(self):
        for repo in (self.KIM, self.GEMASAI, self.UWG):
            self.assertTrue(core.should_keep_repo(repo), repo["id"])

    def test_popularity_floor_still_applies(self):
        self.assertFalse(core.should_keep_repo(self.UNPOPULAR))

    def test_upscalers_are_categorised_into_upscale_models(self):
        cases = [
            (self.KIM, "4x-UltraSharp.pth"),
            (self.GEMASAI, "4x_NMKD-Siax_200k.pth"),
            (self.UWG, "ESRGAN/1x-ITF-SkinDiffDetail-Lite-v1.pth"),
            ({"id": "a/b", "tags": []}, "4x_foolhardy_Remacri.pth"),
            ({"id": "a/b", "tags": []}, "models/SwinIR-L.pth"),
        ]
        for repo, path in cases:
            with self.subTest(path=path):
                self.assertEqual(core.categorize_file(repo, path), "upscale_models")

    def test_ordinary_weights_are_not_swept_into_upscale_models(self):
        repo = {"id": "Comfy-Org/Krea-2", "tags": ["comfyui"]}
        for path, expected in (
            ("vae/qwen_image_vae.safetensors", "vae"),
            ("text_encoders/qwen3vl_4b_bf16.safetensors", "text_encoders"),
            ("loras/krea2_darkbrush.safetensors", "loras"),
        ):
            with self.subTest(path=path):
                self.assertEqual(core.categorize_file(repo, path), expected)

    def test_upscaler_size_floor_admits_a_67mb_esrgan(self):
        self.assertFalse(core.is_size_too_small("upscale_models", 67_000_000))
        self.assertFalse(core.is_size_too_small("upscale_models", 20_000_000))


class FrontendRegressionTests(unittest.TestCase):
    """The live browser broke because a cached overlay was reused blindly."""

    def setUp(self):
        import re

        self.re = re
        self.js = (ROOT / "web" / "hf_model_downloader.js").read_text()

    def test_overlay_is_version_stamped_and_checked(self):
        self.assertIn("overlay.dataset.hfmdLayout = LAYOUT_VERSION", self.js)
        self.assertIn("existing.dataset.hfmdLayout === LAYOUT_VERSION", self.js)

    def test_rehydrate_branch_restores_every_live_reference(self):
        """state.ui is built twice: fresh, and rehydrated from a reused overlay.

        The fresh branch uses shorthand (`livePanel,`) while the rehydrate branch
        queries the DOM (`livePanel: existing.querySelector(...)`). A name missing
        from either means setView("live") dereferences undefined, which is exactly
        how the live browser broke.
        """
        head = self.js.split("function setStatus")[0]
        for name in (
            "liveButton",
            "livePanel",
            "liveSearch",
            "liveSort",
            "livePipeline",
            "liveRepos",
            "liveFiles",
            "liveAria2",
            "liveAria2Text",
            "liveAria2Button",
        ):
            self.assertIn(f"{name}: existing.querySelector", head, f"{name} not rehydrated")
            self.assertTrue(
                self.re.search(rf"^\s+{name},\s*$", head, self.re.M),
                f"{name} not in the freshly built state.ui",
            )

    def test_curated_search_is_debounced(self):
        self.assertIn("state.searchDebounce", self.js)
        self.assertIn("searchDebounce: null", self.js)

    def test_job_polling_backs_off_when_idle(self):
        self.assertIn("function hasLiveJobs()", self.js)
        self.assertIn("jobsIdleTicks", self.js)

    def test_dom_observer_is_not_bound_to_document_body(self):
        self.assertNotIn("observe(document.body", self.js)

    def test_no_dead_css_selectors(self):
        """A styled class that the JS never creates silently does nothing.

        An earlier scroll fix targeted .hfmd-jobs and .hfmd-job-list, neither of
        which exists, so the downloads panel never scrolled.
        """
        css = (ROOT / "web" / "hf_model_downloader.css").read_text()
        dynamic = ("hfmd-job-status-", "hfmd-job-file-status-", "hfmd-status-")
        dead = [
            cls
            for cls in sorted(set(self.re.findall(r"\.(hfmd-[a-z0-9-]+)", css)))
            if cls not in self.js and not any(cls.startswith(d) for d in dynamic)
        ]
        self.assertEqual(dead, [], f"styled but never created: {dead}")

    def test_downloads_panel_is_a_flex_column_that_clips(self):
        """A block panel lets the job list grow past it instead of scrolling."""
        css = (ROOT / "web" / "hf_model_downloader.css").read_text()
        block = css.split(".hfmd-downloads-panel {")[-1].split("}")[0]
        for rule in ("display: flex", "flex-direction: column", "min-height: 0", "overflow: hidden"):
            self.assertIn(rule, block, f"downloads panel missing {rule}")

    def test_downloads_list_is_the_scrollable_child(self):
        css = (ROOT / "web" / "hf_model_downloader.css").read_text()
        block = css.split(".hfmd-downloads-panel .hfmd-downloads-list {")[-1].split("}")[0]
        for rule in ("flex: 1 1 auto", "min-height: 0", "overflow-y: auto"):
            self.assertIn(rule, block, f"downloads list missing {rule}")

    def test_setview_shows_the_panel_as_flex_not_block(self):
        self.assertIn('downloadsPanel.style.display = downloads ? "flex" : "none"', self.js)
        self.assertNotIn('downloadsPanel.style.display = downloads ? "block"', self.js)

    def test_compact_toggle_is_wired_and_persisted(self):
        self.assertIn("hfmd-density-toggle", self.js)
        self.assertIn("function setCompact(", self.js)
        self.assertIn("function applyCompact(", self.js)
        self.assertIn("DENSITY_KEY", self.js)
        # Applied on open so a rehydrated overlay keeps the saved density.
        self.assertGreaterEqual(self.js.count("applyCompact()"), 2)

    def test_compact_button_survives_overlay_rehydration(self):
        head = self.js.split("function setStatus")[0]
        self.assertIn("compactButton: existing.querySelector", head)
        self.assertTrue(self.re.search(r"^\s+compactButton,\s*$", head, self.re.M))

    def test_upscaler_quick_search_chips_exist(self):
        self.assertIn('["Upscalers", "upscaler"]', self.js)
        self.assertIn('["ESRGAN", "esrgan"]', self.js)

    def test_every_quick_search_is_a_single_token(self):
        """The Hub ANDs search terms, so a multi-word chip returns near-empty junk."""
        block = self.js.split("const QUICK_SEARCHES = [")[1].split("];")[0]
        queries = self.re.findall(r'\[\s*"[^"]+"\s*,\s*"([^"]+)"\s*\]', block)
        self.assertGreaterEqual(len(queries), 6)
        for query in queries:
            self.assertNotIn(" ", query, f"quick search {query!r} must be one token")


class CoreCallCompatibilityTests(unittest.TestCase):
    """live_browse reuses server.py helpers, so their signatures must line up.

    A mismatch here only shows up as a runtime error on a real network call, which
    no offline test would otherwise reach.
    """

    def test_request_json_has_no_headers_parameter(self):
        import inspect

        params = inspect.signature(core.request_json).parameters
        self.assertNotIn(
            "headers",
            params,
            "request_json applies HF auth itself; do not pass headers to it",
        )
        self.assertEqual(list(params)[:2], ["session", "url"])
        self.assertIn("timeout", params)

    def test_fetch_repo_tree_takes_a_repo_id_string(self):
        import inspect

        params = list(inspect.signature(core.fetch_repo_tree).parameters)
        self.assertEqual(params[:3], ["session", "repo_id", "revision"])

    def test_live_browse_never_passes_headers_to_request_json(self):
        source = (ROOT / "live_browse.py").read_text()
        for chunk in source.split("request_json(")[1:]:
            call = chunk.split(")")[0]
            self.assertNotIn("headers", call, f"headers passed to request_json: {call!r}")

    def test_helpers_live_browse_depends_on_all_exist(self):
        for name in (
            "request_json",
            "fetch_repo_tree",
            "_repo_tree_revision",
            "categorize_file",
            "title_from_path",
            "detect_family",
            "is_shard_file",
            "build_installed_lookup",
            "installed_path_for_item",
            "preview_destination",
            "parse_int",
            "MODEL_EXTENSIONS",
            "HF_API",
            "HF_WEB",
        ):
            self.assertTrue(hasattr(core, name), f"server.py is missing {name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
