#!/usr/bin/env bash
# Run Spectator in the 'spectator' conda environment
# Usage:
#   ./run_spectator.sh
# Always runs: examples/spectator.py

set -euo pipefail

# Resolve repo root as the directory containing this script
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_REL="examples/spectator.py"
TARGET_ABS="${REPO_ROOT}/${TARGET_REL}"

if [[ ! -f "${TARGET_ABS}" ]]; then
  echo "Error: target script not found: ${TARGET_ABS}" >&2
  echo "Expected file at: ${TARGET_REL}" >&2
  exit 1
fi

# Prefer 'conda run' for reliability across shells
if command -v conda >/dev/null 2>&1; then
  # Ensure environment exists
  if conda env list | awk '{print $1}' | grep -qx "spectator"; then
    exec conda run -n spectator --no-capture-output python -u "${TARGET_ABS}"
  else
    echo "Conda env 'spectator' not found. Create it or adjust the env name in this script." >&2
    exit 1
  fi
else
  echo "Conda command not found on PATH. Please install Miniconda/Anaconda and try again." >&2
  exit 1
fi
