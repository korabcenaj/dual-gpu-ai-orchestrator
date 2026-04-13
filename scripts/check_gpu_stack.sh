#!/usr/bin/env bash
set -euo pipefail

echo "=== User groups ==="
id

echo
echo "=== Render devices ==="
ls -l /dev/dri || true

echo
echo "=== OpenCL ==="
if command -v clinfo >/dev/null 2>&1; then
  sg render -c 'clinfo --list || clinfo | head -n 60' || true
else
  echo "clinfo not installed"
fi

echo
echo "=== Vulkan ==="
if command -v vulkaninfo >/dev/null 2>&1; then
  sg render -c 'vulkaninfo --summary | head -n 60' || true
else
  echo "vulkaninfo not installed"
fi
