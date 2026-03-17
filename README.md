# Spectator - Spectropolarimetric Data Viewer

A Python-based visualization tool for multi-dimensional spectropolarimetric data, designed to replace IDL Z3showred.

![example](docs/viewer.png)


## Installation

### Requirements

- Python 3.14+
- PyQt6
- NumPy, PyQtGraph, QDarkStyle, SciPy

### Setup

```bash
# Create conda environment
conda create -n spectator python=3.14
conda activate spectator

# Install dependencies (pyqt has to be version 6 - do not mix with pyqt5!)
conda install -c conda-forge numpy pyqtgraph qdarkstyle scipy pyqt

# Clone and install
git clone https://github.com/fzeuner/spectator.git
cd spectator
pip install -e .
```

## Usage

### Programmatic Usage

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

### Examples

```bash
# 3D viewer (states, spectral, spatial)
python examples/viewer_example.py

# 4D scan viewer (states, spectral, spatial_y, spatial_x)
python examples/scan_viewer_example.py

# File browser (Z3showred-style)
python examples/z3showred_example.py
```

![File browser](docs/z3showred.png)

## Features

- **Flexible data handling**: numpy arrays with configurable dimension semantics
- **Synchronized views**: crosshairs, zoom, and averaging lines sync across all windows
- **Spectral/spatial averaging**: interactive line-based region selection
- **Per-state scaling**: automatic optimization for each Stokes parameter
- **ZIMPOL support**: direct `.dat` file loading

## Configuration (ZIMPOL file browser)

Edit `~/.config/spectator/file_config.json` (local user config, location is defined in `utils/config.py` as `USER_CONFIG_DIR`/`USER_CONFIG_PATH`) (or `config/file_config.json` in repo):

```json
{
  "default_data_base_dir": "/path/to/your/pdata",
  "auto_navigate_recent": true,
  "must_be_in_directory": "reduced",
  "excluded_file_terms": ["cal", "dark", "ff"]
}
```

- `default_data_base_dir`: Base data directory path
- `auto_navigate_recent`: Auto-open most recent `YYMMDD` subdirectory
- `must_be_in_directory`: Filter paths containing this substring
- `excluded_file_terms`: Exclude files containing these terms

## Architecture

Spectator follows a **Model-View-Controller (MVC)** architecture pattern for maintainable and scalable code

## License

Scientific research purposes. Contact maintainers for licensing.

## Acknowledgments

- **Franziska Zeuner**: Original concept, architecture, implementation
- **PyQtGraph team**: Plotting library
- **Claude Sonnet 4.5**: Development assistance
