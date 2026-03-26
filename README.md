# ComfyUI HF Model Downloader Popup

Adds a **sidebar button** (`HF Models`) to ComfyUI that opens a popup model downloader UI.

## Features

- Multi-owner Hugging Face indexing (default: Comfy-Org, Kijai, black-forest-labs, Tencent-Hunyuan, Qwen, lllyasviel)
- Category tabs + family grouping + search
- Multi-select + bulk download via aria2
- Direct install into ComfyUI `models/<category>/<family>/...`
- Backend routes exposed at:
  - `GET /hf-model-downloader/index`
  - `POST /hf-model-downloader/download`
  - `GET /hf-model-downloader/status`

## Token

Auth token resolution order:

1. `HF_TOKEN` env var
2. `HUGGINGFACE_TOKEN` env var
3. `./.hf_token` inside this custom node
4. `/workspace/mod/.hf_token`

## Activation

1. Restart ComfyUI server
2. Hard refresh browser (`Ctrl+Shift+R`)
3. Click `HF Models` in sidebar
