# Spectator

A Python-based interactive visualization tool for multi-dimensional 
spectropolarimetric data - designed to replace IDL Z3showred.

![viewer](docs/viewer.png)

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [End users](#end-users)
  - [z3showred — modern systems](#z3showred--modern-systems)
  - [z3showred — old OS / instrument PCs](#z3showred--old-os--instrument-pcs)
  - [Developers](#developers)
- [Usage](#usage)
- [Configuration](#configuration)
- [Acknowledgments](#acknowledgments)

---

## Installation

### End users

If you only want to use Spectator programmatically in your own Python project, install it via pip:

```bash
pip install git+https://github.com/fzeuner/spectator.git
```

Requires Python 3.14+.

### z3showred — modern systems

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.14+.

```bash
git clone https://github.com/fzeuner/spectator.git ~/spectator
cd ~/spectator
uv sync
```

**Configure data path:**

```bash
mkdir -p ~/.config/spectator
cp ~/spectator/config/file_config.json ~/.config/spectator/file_config.json
# Edit the file and set "default_data_base_dir" to your data root
```

**Add shell alias:**

```bash
echo "alias z3showred='cd ~/spectator && ./z3showred.sh'" >> ~/.bashrc
source ~/.bashrc
```

Then simply run `z3showred`.

![File browser](docs/z3showred.png)

### z3showred — old OS / instrument PCs

For OS systems where PyQt6 cannot be installed (e.g. saturn, old instrument PCs), use the `os-old` branch which is based on PyQt5. Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/fzeuner/spectator.git ~/spectator
cd ~/spectator
git checkout os-old
uv sync
```

See the `os-old` branch README for the additional symlink setup steps.

### Developers

```bash
git clone https://github.com/fzeuner/spectator.git
cd spectator
uv sync
uv run python examples/viewer_example.py  # verify
```

Useful commands:

```bash

uv run python examples/scan_viewer_example.py
uv add <package>                           # add dependency
uv lock                                    # update lock file
```

---

## Usage

### Programmatic

```python
from spectator.controllers.app_controller import display_data
import numpy as np

data = np.load('your_data.npy')  # shape: (states, spectral, spatial_x)

viewer = display_data(
    data,
    order=['states', 'spectral', 'spatial_x'],
    title='My Data',
    state_names=['I', 'Q', 'U', 'V'],
)
```

**Note:** The actual data array order does not matter, because the order you specify will be used to rearrange the data to match the expected layout for the viewer.

### Available viewers

| Viewer | Dimensions | Description |
|--------|------------|-------------|
| `spectator_viewer` | 3D (states, spectral, spatial_x) | Standard spectropolarimetric viewer with synchronized spectrum, and spatial windows |
| `scan_viewer` | 4D (states, spectral, spatial_y, spatial_x) | Extended viewer for raster scan data with additional spatial Y dimension |

More viewers for 2D and 5D data are planned.

### Example scripts

```bash
uv run python examples/viewer_example.py        # 3D: states × spectral × spatial
uv run python examples/scan_viewer_example.py   # 4D: + spatial_y
uv run python examples/z3showred_example.py     # ZIMPOL file browser
```

---

## Configuration

The file browser reads `~/.config/spectator/file_config.json` (user-local, takes priority) or `config/file_config.json` in the repo.

```json
{
  "default_data_base_dir": "/path/to/your/pdata",
  "auto_navigate_recent": true,
  "must_be_in_directory": "reduced",
  "excluded_file_terms": ["cal", "dark", "ff"]
}
```

| Key | Description |
|-----|-------------|
| `default_data_base_dir` | Base directory for data files |
| `auto_navigate_recent` | Auto-open most recent `YYMMDD` subdirectory |
| `must_be_in_directory` | Preferred subdirectory (e.g., 'reduced'). If present, files there are shown; if not, parent directory files are used |
| `excluded_file_terms` | Skip files whose name contains any of these terms |

---

## Acknowledgments

- **Franziska Zeuner** — concept, architecture, implementation
- **PyQtGraph team** — plotting library
- **Claude Sonnet** — development assistance
