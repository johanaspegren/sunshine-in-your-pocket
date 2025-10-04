#!/bin/bash
# Sync the patched st7036 driver into the personal-assistant venv
# Usage: ./sync_hat_patch.sh /path/to/patched/st7036.py

set -e

PATCH_SRC="${1:-./st7036.py}"
VENV_PATH="/home/antipater/dev/personal-assistant/.venv"
TARGET="$VENV_PATH/lib/python3.11/site-packages/st7036.py"

if [ ! -f "$PATCH_SRC" ]; then
  echo "❌ No patch source found at $PATCH_SRC"
  exit 1
fi

if [ ! -d "$VENV_PATH" ]; then
  echo "❌ Virtualenv not found at $VENV_PATH"
  exit 1
fi

echo "🧩 Copying patched st7036.py to venv..."
sudo cp "$PATCH_SRC" "$TARGET"

echo "🧹 Removing old .pyc cache..."
sudo find "$(dirname "$TARGET")" -name "st7036*.pyc" -delete

echo "✅ Done! Patched driver is now active in:"
echo "   $TARGET"
