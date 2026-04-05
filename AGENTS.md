# AGENTS.md

## Cursor Cloud specific instructions

This is a **ComfyUI extension** (not a standalone app). It requires ComfyUI as a host.

### Project overview

- `server.py` — Python backend (~1,680 lines): API routes, HF index builder, aria2c download manager
- `__init__.py` — ComfyUI extension entrypoint
- `web/` — Frontend JS/CSS assets served by ComfyUI

### Running the extension

1. ComfyUI must be installed at `/home/ubuntu/ComfyUI` and the extension is symlinked at `custom_nodes/ComfyUI_HF_ModelDownloader → /workspace`.
2. Start ComfyUI with: `cd /home/ubuntu/ComfyUI && python3 main.py --cpu --listen 0.0.0.0 --port 8188`
3. The extension registers API routes under `/hf-model-downloader/*` and frontend assets from `./web`.

### Lint / syntax check

`python3 -m py_compile __init__.py server.py` (from `/workspace`). This is the only CI check (see `.github/workflows/ci.yml`).

### Testing

No automated test suite exists. CI only runs `py_compile`. Manual smoke testing is done by starting ComfyUI and exercising the UI/API.

### Key API endpoints for smoke testing

- `GET /hf-model-downloader/settings` — token status
- `GET /hf-model-downloader/index?strict_filter=true` — fetches curated model index from HF
- `GET /hf-model-downloader/jobs` — download job status
- `POST /hf-model-downloader/download` — start a download job

### System dependency

`aria2c` must be installed (`sudo apt-get install -y aria2`). The extension uses it for model downloads via JSON-RPC.

### Gotchas

- The extension imports `folder_paths` and `server.PromptServer` from ComfyUI — these are only available when running inside the ComfyUI process.
- Running `python3 server.py` standalone will fail due to missing ComfyUI modules.
- The index is cached locally at `.cache/index.json` (gitignored) with a 6-hour TTL.
