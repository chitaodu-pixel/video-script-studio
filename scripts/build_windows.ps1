$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name VideoScriptStudio `
    --paths src `
    src/video_script_studio/app.py

Write-Host "Build complete: $projectRoot\dist\VideoScriptStudio"

