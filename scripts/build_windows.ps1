#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Builds the Windows YouTubeTranscriber.exe distribution.

.DESCRIPTION
    Must be run on Windows — PyInstaller does not cross-compile. Creates/
    reuses a venv, installs build dependencies, cleans previous build
    output, runs PyInstaller against YouTubeTranscriber.spec, and zips the
    result. No arguments to remember: just run it.
#>

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "==> Setting up virtual environment"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
$Python = ".\.venv\Scripts\python.exe"
$Pip = ".\.venv\Scripts\pip.exe"

& $Pip install --upgrade pip | Out-Null
& $Pip install -e ".[dev,build]"

Write-Host "==> Running tests"
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "Tests failed — aborting build."
    exit 1
}

Write-Host "==> Cleaning previous build output"
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist

Write-Host "==> Running PyInstaller"
& ".\.venv\Scripts\pyinstaller.exe" YouTubeTranscriber.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
    exit 1
}

$DistDir = "dist\YouTubeTranscriber"
$ExePath = Join-Path $DistDir "YouTubeTranscriber.exe"
if (-not (Test-Path $ExePath)) {
    Write-Error "Expected executable not found: $ExePath"
    exit 1
}

Write-Host "==> Adding README.txt to the distribution"
@"
YouTubeTranscriber - Windows

Double-click YouTubeTranscriber.exe to start. Your browser opens
automatically at http://127.0.0.1:8501 once the app is ready.

Local Whisper (only needed for videos with no YouTube captions):
run scripts\setup_whisper.ps1 from a source checkout, or use the
"Download model" button in the app once ffmpeg/whisper.cpp are set up.

Troubleshooting: see README.md in the project repository, including the
note on Windows SmartScreen warnings for unsigned executables.
"@ | Out-File -Encoding utf8 (Join-Path $DistDir "README.txt")

$ZipPath = "dist\YouTubeTranscriber-Windows-x64.zip"
Write-Host "==> Creating $ZipPath"
Remove-Item -Force -ErrorAction SilentlyContinue $ZipPath
Compress-Archive -Path $DistDir -DestinationPath $ZipPath

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $((Get-Item $ExePath).FullName)"
Write-Host "  $((Get-Item $ZipPath).FullName)"
