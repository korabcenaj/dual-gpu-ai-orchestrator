#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y \
  docker.io docker-compose-v2 \
  mesa-opencl-icd intel-opencl-icd clinfo \
  vulkan-tools ffmpeg curl make python3-pip

sudo usermod -aG docker,video,render "$USER"

echo
echo "Host setup complete. Start a new login shell before running GPU tools without sudo."
echo "Until then, use: sg render -c 'clinfo --list'"
