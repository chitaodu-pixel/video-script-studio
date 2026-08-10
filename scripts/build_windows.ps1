$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtual environment not found: $python"
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name VideoScriptStudio `
    --paths src `
    --collect-all faster_whisper `
    --collect-all ctranslate2 `
    --collect-all av `
    --collect-all numpy `
    --collect-all tokenizers `
    --collect-all tkinterdnd2 `
    --collect-all kokoro_onnx `
    --collect-all misaki `
    --collect-all soundfile `
    --collect-all jieba `
    --collect-all ordered_set `
    --collect-data language_tags `
    src/video_script_studio/portable_app.py

Write-Host "Build complete: $projectRoot\dist\VideoScriptStudio.exe"
