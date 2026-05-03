$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  throw "venv not found. Run .\scripts\setup-dev.ps1 first."
}

& $python -m pip install -e "$root\app[build]"
& $python -m PyInstaller `
  --name tor-llm-tool `
  --windowed `
  --noconfirm `
  --clean `
  --paths "$root\app" `
  "$root\app\tor_llm_tool\__main__.py"

Write-Host "Build output: $root\dist\tor-llm-tool"
