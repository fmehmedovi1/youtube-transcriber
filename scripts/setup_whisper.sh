#!/usr/bin/env bash
# Sets up local whisper.cpp: clone, build, download one free ggml model.
# No paid account, no API key, ever.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$ROOT_DIR/tools"
WHISPER_DIR="$TOOLS_DIR/whisper.cpp"
MODELS_DIR="$ROOT_DIR/models/whisper"
MODEL="${1:-small}"

case "$MODEL" in
  tiny|base|small|medium) ;;
  *)
    echo "Unknown model '$MODEL'. Choose one of: tiny base small medium" >&2
    exit 1
    ;;
esac

echo "==> Checking required tools"
for cmd in git cmake make; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required tool: $cmd" >&2
    if [[ "$(uname)" == "Darwin" ]]; then
      echo "Install with: brew install $cmd" >&2
    fi
    exit 1
  fi
done

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found. It's needed to convert downloaded audio for Whisper." >&2
  if [[ "$(uname)" == "Darwin" ]]; then
    echo "Install with: brew install ffmpeg" >&2
  fi
  exit 1
fi

mkdir -p "$TOOLS_DIR" "$MODELS_DIR"

if [[ -d "$WHISPER_DIR/.git" ]]; then
  echo "==> whisper.cpp already cloned, pulling latest"
  git -C "$WHISPER_DIR" pull --ff-only
else
  echo "==> Cloning ggml-org/whisper.cpp"
  git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$WHISPER_DIR"
fi

echo "==> Building whisper.cpp (this uses local CPU/GPU, no cloud build)"
cmake -S "$WHISPER_DIR" -B "$WHISPER_DIR/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$WHISPER_DIR/build" -j --config Release

BUILT_BIN="$WHISPER_DIR/build/bin/whisper-cli"
if [[ ! -f "$BUILT_BIN" ]]; then
  echo "Build finished but expected binary not found at $BUILT_BIN" >&2
  echo "Check the whisper.cpp build output above for the actual binary name/location." >&2
  exit 1
fi
echo "==> Built: $BUILT_BIN"

MODEL_FILE="$MODELS_DIR/ggml-$MODEL.bin"
if [[ -f "$MODEL_FILE" ]]; then
  echo "==> Model '$MODEL' already present at $MODEL_FILE, skipping download"
else
  echo "Downloading local Whisper model... ($MODEL, multilingual, free/open weights)"
  MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$MODEL.bin"
  curl -L --fail --progress-bar -o "$MODEL_FILE.part" "$MODEL_URL"
  mv "$MODEL_FILE.part" "$MODEL_FILE"
  echo "==> Model saved to $MODEL_FILE"
fi

echo ""
echo "Setup complete."
echo "  whisper.cpp binary: $BUILT_BIN"
echo "  model:              $MODEL_FILE"
echo ""
echo "Set these env vars only if you move things from the defaults:"
echo "  WHISPER_CPP_PATH=$BUILT_BIN"
echo "  WHISPER_MODEL_PATH=$MODELS_DIR"
echo "  DEFAULT_WHISPER_MODEL=$MODEL"
