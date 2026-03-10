Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Building AutoClickerMVP.exe ..."

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name AutoClickerMVP `
  --icon assets/branding/app_icon.ico `
  main.py

Write-Host "Build complete: dist\\AutoClickerMVP\\AutoClickerMVP.exe"
