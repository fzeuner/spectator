#!/usr/bin/env python3
from __future__ import annotations

import sys
import os

# Ensure repository root is on sys.path when running as a script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pyqtgraph.Qt import QtWidgets

try:
    from controllers.file_app import run as run_file_app
    IMPORTS_OK = True
except Exception as e:
    print(f"Error importing file app: {e}")
    IMPORTS_OK = False


def main():
    if not IMPORTS_OK:
        print("Cannot run file browser example due to import errors.")
        sys.exit(1)
    # Launch the standalone file browser app
    exit_code = run_file_app()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
