# ComfyUI HF Model Downloader

Curated Hugging Face model browser + installer for ComfyUI.

This extension adds a popup UI with a persistent floating launcher in the ComfyUI shell, so you can browse official/popular models, filter them, select multiple files, and download directly into the correct Comfy model folders.

## What It Adds

- Persistent floating launcher: `Model Browser`
- Sidebar launch button: `HF Models`
- Curated multi-owner index (default owners include Comfy-Org, Kijai, black-forest-labs, Tencent-Hunyuan, Qwen, lllyasviel)
- Tabbed browsing by Comfy model category
- Search + filters (family/type, owner, strict filtering toggle)
- Bulk selection and queue-based download with `aria2c`
- Per-file live progress (each model has its own line/progress/speed in the Downloads view)
- Automatic install path placement:
  - `ComfyUI/models/<category>/<family>/<filename>`
- Token settings panel for gated Hugging Face repos

## Requirements

- ComfyUI running locally
- `aria2c` installed and available in `PATH`
- Python environment used by ComfyUI
- Python dependencies from [`requirements.txt`](requirements.txt)

## Install

1. Place this folder in:
   - `ComfyUI/custom_nodes/ComfyUI_HF_ModelDownloader`
2. Install Python requirements inside the same environment that runs ComfyUI:
   - `python -m pip install -r requirements.txt`
3. Restart ComfyUI.
4. Hard refresh browser (`Ctrl+Shift+R`).
5. Open `Model Browser` from the floating launcher or `HF Models` from the ComfyUI sidebar.

## Quick Start

1. Open `Model Browser`.
2. Click `Refresh Index` (optional, to pull latest curated list).
3. Pick a category tab (for example `diffusion_models`, `loras`, `vae`).
4. Filter by search / family / owner as needed.
5. Select models and click `Download Selected`.
6. Watch per-file progress in the `Downloads` view.

## Token for Gated Repos

Use the popup `Settings` button to save your Hugging Face token.

- `Save Token` validates token against HF before saving.
- `Clear` removes saved token file.
- UI shows masked token + source.

Token resolution order used by backend:

1. `./.hf_token` in this extension folder
2. `/workspace/mod/.hf_token`
3. `HF_TOKEN` / `HUGGINGFACE_TOKEN` environment variables

## Download + Progress Behavior

- Downloader uses `aria2c` in queue mode.
- Jobs support:
  - start
  - polling status
  - cancel
- Progress sources:
  - primary: aria2 JSON-RPC (per-file bytes/speed/progress)
  - fallback: local file-size snapshots when RPC data is unavailable

## Filtering Behavior

`Strict` mode is designed to reduce junk entries:

- excludes shard artifacts (`00001-of-00002` style files)
- excludes diffusers internals/components that are not direct model weights
- applies minimum size heuristics by category

Turn `Strict` off if you want wider/raw file visibility.

## API Routes

All routes are served by this extension:

- `GET /hf-model-downloader/index`
- `POST /hf-model-downloader/download`
- `GET /hf-model-downloader/status`
- `GET /hf-model-downloader/jobs`
- `POST /hf-model-downloader/cancel`
- `GET /hf-model-downloader/settings`
- `POST /hf-model-downloader/token`

## Development

- Backend runtime dependency: `aiohttp`
- ComfyUI-provided modules: `folder_paths`, `server.PromptServer`
- Indexing and download URLs use each model’s latest commit SHA from the Hugging Face API when available (falls back to `main`), so non-`main` default branches stay consistent.
- Frontend assets live in `./web`
- Syntax smoke test:
  - `python -m py_compile __init__.py server.py`
- Unit tests (no extra deps):
  - `python -m unittest discover -s tests -q`

## Repository Standards

- Issues: use the GitHub issue forms for bug reports and feature requests
- Pull requests: follow the checklist in [`.github/pull_request_template.md`](.github/pull_request_template.md)
- Contributions: see [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security reporting: see [`SECURITY.md`](SECURITY.md)
- Community expectations: see [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)

## Troubleshooting

- No sidebar button:
  - hard refresh browser
  - use the persistent floating `Model Browser` launcher
- Gated repo download fails with auth error:
  - open `Settings` and save a valid HF token
- Download fails immediately:
  - ensure `aria2c` is installed and in `PATH`
- Model appears already installed incorrectly:
  - installed detection uses filename + size heuristics; refresh index after manual file changes

## Notes

- This extension is UI/API focused and does not register graph node classes.
- Frontend assets are served from `./web`.
- Cached index data is stored in `./.cache` and is intentionally gitignored.
