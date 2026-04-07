#!/usr/bin/env bash
# Run Spectator using uv
# Usage:
#   ./z3showred.sh
# Always runs: examples/z3showred_example.py
#
# Requires: uv (https://docs.astral.sh/uv/) installed

set -euo pipefail

# Resolve repo root as the directory containing this script
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_REL="examples/z3showred_example.py"
TARGET_ABS="${REPO_ROOT}/${TARGET_REL}"

if [[ ! -f "${TARGET_ABS}" ]]; then
  echo "Error: target script not found: ${TARGET_ABS}" >&2
  echo "Expected file at: ${TARGET_REL}" >&2
  exit 1
fi

# Environment adjustments for remote servers / headless / mismatched runtime dir
# 1) Ensure XDG_RUNTIME_DIR is owned by current UID and has 0700 perms
export XDG_RUNTIME_DIR="/tmp/xdg-runtime-$(id -u)"
mkdir -p "${XDG_RUNTIME_DIR}" 2>/dev/null || true
chmod 700 "${XDG_RUNTIME_DIR}" 2>/dev/null || true

# 2) Force software rendering to avoid GPU/GLX issues on servers
export LIBGL_ALWAYS_SOFTWARE=1
export QT_OPENGL=software
export QT_QUICK_BACKEND=software
export QT_QPA_PLATFORM=xcb
export QT_XCB_NO_XI2=1            # X servers without XInput2 support
export QT_XCB_GL_INTEGRATION=none # Avoid GLX initialization on headless/Xvfb without GLX
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe # Prefer CPU rasterization via llvmpipe

# Check if uv is available
if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv not found on PATH. Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

# If no X server is available, attempt to run under a virtual framebuffer
RUNNER_PREFIX=()
if [[ -z "${DISPLAY:-}" ]]; then
  if command -v xvfb-run >/dev/null 2>&1; then
    # Allow overriding virtual screen size via SPECTATOR_SCREEN, default to smaller geometry
    SCREEN_SPEC="${SPECTATOR_SCREEN:-1600x1200x24}"
    echo "[info] DISPLAY not set -> using xvfb-run with screen ${SCREEN_SPEC}" >&2
    RUNNER_PREFIX=(xvfb-run -a -s "-screen 0 ${SCREEN_SPEC}")
  else
    echo "[warn] DISPLAY not set and xvfb-run not found; continuing without X server (may fail)" >&2
  fi
fi

# Run with uv (uses .venv automatically)
exec "${RUNNER_PREFIX[@]}" uv run python -u "${TARGET_ABS}"