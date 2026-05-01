# Tor LLM Support Tool

Tor Browser に拡張を入れず、画面上の指定範囲をスクリーンショット取得して OCR と local LLM で翻訳・解説・質問応答を行う独立支援ツールです。

## Current MVP

- Windows desktop app
- Screen region selector
- Screenshot preview
- OCR provider abstraction
- Active app / process / window title capture
- URL candidate extraction from OCR text
- LM Studio OpenAI-compatible provider
- Settings dialog
- Translate / explain / ask / clean OCR tasks

## Setup

```powershell
.\scripts\setup-dev.ps1
```

RapidOCR is installed by default. Optional OCR engines can be installed separately:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".\app[paddle-ocr]"
.\.venv\Scripts\python.exe -m pip install -e ".\app[tesseract]"
```

PaddleOCR is optional because it is heavier and can be more sensitive to the local Windows/Paddle runtime.

## Run

```powershell
.\scripts\run-dev.ps1
```

or:

```powershell
.\.venv\Scripts\python.exe -m tor_llm_tool
```

## LM Studio

1. Open LM Studio.
2. Start the Local Server.
3. Load a model.
4. In the app settings, set:
   - Base URL: `http://127.0.0.1:1234/v1`
   - Model: the loaded LM Studio model identifier
   - Vision model: optional, for image input

If LM Studio authentication is enabled, set the API key in the app settings.
