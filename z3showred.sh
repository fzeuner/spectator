#!/usr/bin/env bash
# Run Spectator in the 'spectator' conda environment
# Usage:
#   ./run_spectator.sh
# Always runs: examples/z3showred_example.py

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

# Prefer 'conda run' for reliability across shells
if command -v conda >/dev/null 2>&1; then
  # Ensure environment exists
  if conda env list | awk '{print $1}' | grep -qx "spectator"; then
    # If no X server is available, attempt to run under a virtual framebuffer
    RUNNER_PREFIX=()
    if [[ -z "${DISPLAY:-}" ]]; then
      if command -v xvfb-run >/dev/null 2>&1; then
        echo "[info] DISPLAY not set -> using xvfb-run" >&2
        RUNNER_PREFIX=(xvfb-run -a -s "-screen 0 1920x1080x24")
      else
        echo "[warn] DISPLAY not set and xvfb-run not found; continuing without X server (may fail)" >&2
      fi
    fi

    exec "${RUNNER_PREFIX[@]}" conda run -n spectator --no-capture-output python -u "${TARGET_ABS}"
  else
    echo "Conda env 'spectator' not found. Create it or adjust the env name in this script." >&2
    exit 1
  fi
else
  echo "Conda command not found on PATH. Please install Miniconda/Anaconda and try again." >&2
  exit 1
fi
