$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $repoRoot "app"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Virtual environment not found. Run scripts\setup-dev.ps1 first."
}

Push-Location $appDir
try {
    & $pythonExe -m tor_llm_tool
}
finally {
    Pop-Location
}
