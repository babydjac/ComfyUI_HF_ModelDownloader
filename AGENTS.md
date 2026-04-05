# AGENTS.md

This is a **ComfyUI extension** (not a standalone app). It requires ComfyUI as a host.

## Project overview

- `server.py` — Python backend (~1,700 lines): API routes, HF index builder, aria2c download manager
- `__init__.py` — ComfyUI extension entrypoint
- `web/` — Frontend JS/CSS assets served by ComfyUI
- `tests/test_server.py` — Unit tests with ComfyUI shims (no GPU or ComfyUI process needed)

## Prerequisites

- **Python 3.10+** (CI tests 3.10, 3.11, 3.12)
- **ComfyUI** installed, with this extension placed or symlinked at `ComfyUI/custom_nodes/ComfyUI_HF_ModelDownloader`
- **aria2c** — download engine used via JSON-RPC
  - macOS: `brew install aria2`
  - Linux: `sudo apt-get install -y aria2`
  - Windows: download from https://aria2.github.io/ and add to PATH
- **aiohttp** — `pip install -r requirements.txt` (inside the same venv as ComfyUI)

## Running the extension

1. Ensure this folder is at `ComfyUI/custom_nodes/ComfyUI_HF_ModelDownloader` (clone, copy, or symlink).
2. Install Python deps: `pip install -r requirements.txt`
3. Start ComfyUI from its root: `python main.py --listen` (add `--cpu` if no GPU).
4. The extension registers API routes under `/hf-model-downloader/*` and serves frontend assets from `./web`.

## Lint / syntax check

```
python -m py_compile __init__.py server.py
```

Run from this extension's directory. This is the baseline CI check (see `.github/workflows/ci.yml`).

## Testing

Unit tests stub ComfyUI modules so they run without a ComfyUI process:

```
python -m unittest discover -s tests -q
```

CI runs both the syntax check and unit tests on Python 3.10, 3.11, and 3.12.

## Key API endpoints for smoke testing

- `GET /hf-model-downloader/settings` — token status
- `GET /hf-model-downloader/index?strict_filter=true` — fetches curated model index from HF
- `GET /hf-model-downloader/jobs` — download job status
- `POST /hf-model-downloader/download` — start a download job

## Gotchas

- The extension imports `folder_paths` and `server.PromptServer` from ComfyUI — these are only available when running inside the ComfyUI process. Running `python server.py` standalone will fail.
- The index is cached locally at `.cache/index.json` (gitignored) with a 6-hour TTL.
- Downloads use SHA-based revision pinning from the HF API; if a repo has no usable SHA the extension falls back to `main`.
