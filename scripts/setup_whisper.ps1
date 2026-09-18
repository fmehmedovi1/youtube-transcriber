#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Sets up local whisper.cpp on Windows: clone, build, download one free
    ggml model. No paid account, no API key, ever. Mirrors
    scripts/setup_whisper.sh for macOS/Linux.

.PARAMETER Model
    One of: tiny, base, small, medium. Defaults to small.
#>

param(
    [ValidateSet("tiny", "base", "small", "medium")]
    [string]$Model = "small"
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$ToolsDir = Join-Path $RootDir "tools"
$WhisperDir = Join-Path $ToolsDir "whisper.cpp"
$ModelsDir = Join-Path $RootDir "models\whisper"

Write-Host "==> Checking required tools"
foreach ($cmd in @("git", "cmake")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "Missing required tool: $cmd. Install it (e.g. winget install $cmd) and retry."
        exit 1
    }
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Error "ffmpeg not found. Install with: winget install ffmpeg (or download from ffmpeg.org and add it to PATH)."
    exit 1
}

New-Item -ItemType Directory -Force -Path $ToolsDir, $ModelsDir | Out-Null

if (Test-Path (Join-Path $WhisperDir ".git")) {
    Write-Host "==> whisper.cpp already cloned, pulling latest"
    git -C $WhisperDir pull --ff-only
} else {
    Write-Host "==> Cloning ggml-org/whisper.cpp"
    git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git $WhisperDir
}

Write-Host "==> Building whisper.cpp (uses your local CPU, no cloud build)"
cmake -S $WhisperDir -B "$WhisperDir\build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$WhisperDir\build" -j --config Release

$BuiltBin = Get-ChildItem -Path "$WhisperDir\build" -Recurse -Filter "whisper-cli.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $BuiltBin) {
    Write-Error "Build finished but whisper-cli.exe not found under $WhisperDir\build. Check the build output above."
    exit 1
}
Write-Host "==> Built: $($BuiltBin.FullName)"

$ModelFile = Join-Path $ModelsDir "ggml-$Model.bin"
if (Test-Path $ModelFile) {
    Write-Host "==> Model '$Model' already present at $ModelFile, skipping download"
} else {
    Write-Host "Downloading local Whisper model... ($Model, multilingual, free/open weights)"
    $ModelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$Model.bin"
    Invoke-WebRequest -Uri $ModelUrl -OutFile "$ModelFile.part"
    Move-Item "$ModelFile.part" $ModelFile
    Write-Host "==> Model saved to $ModelFile"
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "  whisper.cpp binary: $($BuiltBin.FullName)"
Write-Host "  model:              $ModelFile"
Write-Host ""
Write-Host "Set these env vars only if you move things from the defaults:"
Write-Host "  WHISPER_CPP_PATH=$($BuiltBin.FullName)"
Write-Host "  WHISPER_MODEL_PATH=$ModelsDir"
Write-Host "  DEFAULT_WHISPER_MODEL=$Model"
