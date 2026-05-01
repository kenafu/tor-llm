# Tor LLM Support Tool

Standalone desktop support tool that captures a selected screen region, runs OCR, and sends the image/text/context to a local LM Studio backend.

RapidOCR is installed by default. Optional OCR dependencies:

```powershell
..\.venv\Scripts\python.exe -m pip install -e ".[paddle-ocr]"
..\.venv\Scripts\python.exe -m pip install -e ".[tesseract]"
```
