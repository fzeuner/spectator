# Spectator

Python replacement for IDL Z3showred — spectropolarimetric data viewer. This version is specifically tailored for old OS versions where pyqt6 cannot be installed.

![z3showred](docs/z3showred.png)
![viewer](docs/viewer.png)

## Installation

### 1. Install uv

Follow the official guide: https://docs.astral.sh/uv/getting-started/installation/

### 2. Clone and set up

```bash
git clone https://github.com/fzeuner/spectator.git ~/spectator
cd ~/spectator
git checkout os-old
uv sync
```

### 3. Symlink pyqtgraph overrides

Two files in `utils/` replace pyqtgraph internals. Create symlinks into the `.venv`:

```bash
SITE=~/spectator/.venv/lib/python3.10/site-packages

ln -sf ~/spectator/utils/Dock.py         $SITE/pyqtgraph/dockarea/Dock.py
ln -sf ~/spectator/utils/VerticalLabel.py $SITE/pyqtgraph/widgets/VerticalLabel.py
```

### 4. Configure data path

Copy the example config and point it to your data folder:

```bash
mkdir -p ~/.config/spectator
cp ~/spectator/config/file_config.json ~/.config/spectator/file_config.json
```

Then edit `~/.config/spectator/file_config.json` and set `default_data_base_dir` to your data root:

```json
{
  "default_data_base_dir": "/path/to/your/data"
}
```

### 5. Add alias

```bash
echo "alias z3showred='cd ~/spectator && ./z3showred.sh'" >> ~/.bashrc
source ~/.bashrc
```

Then simply run:

```bash
z3showred
```
