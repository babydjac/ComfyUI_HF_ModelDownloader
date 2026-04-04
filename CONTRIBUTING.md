# Contributing

Thanks for helping improve ComfyUI HF Model Downloader.

## Development setup

1. Clone or copy the repository into your ComfyUI `custom_nodes` directory.
2. Activate the same Python environment used to run ComfyUI.
3. Install Python dependencies:
   - `python -m pip install -r requirements.txt`
4. Ensure `aria2c` is installed and available in `PATH`.
5. Restart ComfyUI after backend or frontend changes.

## Project layout

- `server.py`: backend routes, index building, token management, and downloads
- `__init__.py`: ComfyUI extension entrypoint
- `web/`: browser-side UI assets
- `docs/`: screenshots and documentation assets

## Contribution guidelines

- Keep changes focused and well-scoped.
- Preserve compatibility with ComfyUI's custom node loading model.
- Do not commit `.hf_token`, `.env`, caches, or machine-specific artifacts.
- Update screenshots or README sections when the UI or install flow changes.
- Prefer small pull requests with a clear user-facing reason for the change.

## Before opening a pull request

1. Run a quick syntax check:
   - `python -m py_compile __init__.py server.py`
2. Smoke test the extension inside ComfyUI.
3. Include any relevant screenshots for visible UI changes.
4. Summarize what changed and how you tested it.

## Reporting issues

- Use the GitHub issue templates for bugs and feature requests.
- For security-sensitive reports, follow the process in [`SECURITY.md`](SECURITY.md).
