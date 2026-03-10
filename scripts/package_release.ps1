Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path "dist\\AutoClickerMVP\\AutoClickerMVP.exe")) {
  throw "EXE not found. Run scripts\\build_exe.ps1 first."
}

$archive = "AutoClickerMVP-win64.zip"
if (Test-Path $archive) {
  Remove-Item $archive -Force
}

Compress-Archive -Path "dist\\AutoClickerMVP\\*" -DestinationPath $archive -Force
Write-Host "Created $archive"
