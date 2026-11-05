#!/usr/bin/env bash
# Prepare an ubuntu-latest runner: ffmpeg + fonts, python deps, earshot (bank only, no torch/models),
# and the /workspace/work/yt symlink so the renderers' absolute paths work unchanged.
set -euo pipefail
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg fonts-dejavu-core >/dev/null
sudo mkdir -p /workspace/work
sudo ln -sfn "$GITHUB_WORKSPACE" /workspace/work/yt
sudo mkdir -p /workspace/work/pylib && sudo chmod 777 /workspace/work/pylib
pip install -q -r requirements.txt
pip install -q --no-deps "git+https://github.com/Leonxlnx/earshot@main" || echo "earshot install failed (optional)"
mkdir -p out dist clips qa
ffmpeg -version | head -1; python -c "import edge_tts, faster_whisper, cv2; print('deps ok')"
