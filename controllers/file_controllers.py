"""
File loading controller for integrating Files widget with data manager.

This module handles the connection between file selection and data loading/display.
"""

import numpy as np
from typing import Optional, List, Dict, Any
from pyqtgraph.Qt import QtCore, QtWidgets

# Import local modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.file_model import datReader
from controllers.app_controller import data_manager
from utils.config import load_config, ensure_example_config


class FileLoadingController(QtCore.QObject):
    """
    Controller for handling file loading and data display integration.
    
    This class connects the Files widget to the data loading system and
    manages the flow from file selection to data display.
    """
    
    # Signals
    dataLoaded = QtCore.pyqtSignal(np.ndarray, list)  # data, state_names
    loadingError = QtCore.pyqtSignal(str)  # error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = None
        self.current_file_path = None
        # Load user configuration (non-fatal if missing)
        ensure_example_config()
        self._config = load_config()
        # Store resolved base parent directory from config for comparisons
        try:
            base_dir_cfg = self._config.get('default_data_base_dir', '')
            self._base_parent_dir = os.path.abspath(os.path.expanduser(base_dir_cfg)) if base_dir_cfg else ''
        except Exception:
            self._base_parent_dir = ''
        
    def load_file(self, file_path: str):
        """
        Load a .dat file and emit the processed data.
        
        Args:
            file_path: Path to the .dat file to load
        """
        try:
            print(f"[DEBUG][FileLoadingController] load_file called with: {file_path}")
            if not isinstance(file_path, str) or not file_path:
                raise ValueError("Invalid file path provided to load_file")
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File does not exist: {file_path}")

            # Use datReader to load the file
            reader = datReader(path=file_path, python_dict=True, verbose=False)
            
            # Get the images array
            images_array = reader.getDatImagesArray()
            print(f"[DEBUG][FileLoadingController] images_array length: {len(images_array) if images_array is not None else 'None'}")
            
            # Stack all images along the first axis (states axis)
            if not images_array:
                raise ValueError("Empty images array")
            
            raw_data_array = np.stack(images_array, axis=0)
            print(f"[DEBUG][FileLoadingController] raw_data_array shape: {raw_data_array.shape}")
            # Raw data is (states, spatial, spectral)
            
            # Extract state names from the raw data keys
            raw_data = reader.getDat()
            state_names = list(raw_data.keys()) if raw_data else None
            print(f"[DEBUG][FileLoadingController] raw_data keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else type(raw_data)}")
            # Store file info for later display
            try:
                self.current_info = reader.getDatInfo()
            except Exception:
                self.current_info = None
            
            # Filter out non-array keys (like 'info')
            if state_names:
                state_names = [name for name in state_names if isinstance(raw_data.get(name), np.ndarray) and raw_data[name].ndim >= 2]
            
            # Import here to avoid circular imports
            from .app_controller import data_manager
            from models.data_model import AxisType
            
            # Use data manager's rearrange functionality directly
            # The data comes as (states, spatial, spectral) 
            # The StokesSpectrumImageWindow expects (spectral, spatial) per state and transposes internally
            # So we need (states, spectral, spatial) format
            input_axes = [AxisType.STATES, AxisType.SPATIAL, AxisType.SPECTRAL]
            target_axes = [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL]
            
            processed_data = data_manager.rearranger.rearrange_data(
                raw_data_array,
                input_axes=input_axes,
                target_axes=target_axes
            )
            print(f"[DEBUG][FileLoadingController] processed_data shape: {processed_data.shape}")
            
            # Data successfully loaded and processed
            
            # Store current data
            self.current_data = processed_data
            self.current_file_path = file_path
            
            # Emit signal with loaded data
            print("[DEBUG][FileLoadingController] Emitting dataLoaded")
            self.dataLoaded.emit(processed_data, state_names)
                
        except Exception as e:
            import traceback
            error_msg = f"Error loading file {file_path}: {str(e)}\n{traceback.format_exc()}"
            print("[DEBUG][FileLoadingController] " + error_msg)
            self.loadingError.emit(error_msg)
    
    def _process_images_for_viewer(self, images_array: List[np.ndarray]) -> np.ndarray:
        """
        Process the images array from datReader into the format expected by the viewer.
        
        The viewer expects data in the format (N_states, N_spectral, N_spatial)
        where N_states is the number of different states/images.
        
        The data from .dat files comes in as (N_states, N_spatial, N_spectral)
        so we need to transpose to get the correct axis order.
        
        Args:
            images_array: List of image arrays from datReader
            
        Returns:
            Processed numpy array suitable for the viewer
        """
        if not images_array:
            raise ValueError("Empty images array")
        
        # Stack all images along the first axis (states axis)
        stacked_data = np.stack(images_array, axis=0)
        
        print(f"Raw stacked data shape: {stacked_data.shape}")
        print(f"Raw data axis order: (states, spatial, spectral)")
        
        # The viewer expects 3D data: (states, spectral, spatial)
        # But .dat files provide: (states, spatial, spectral)
        # So we need to transpose the last two dimensions
        if stacked_data.ndim == 3:
            # Transpose from (states, spatial, spectral) to (states, spectral, spatial)
            transposed_data = np.transpose(stacked_data, (0, 2, 1))
            print(f"Transposed data shape: {transposed_data.shape}")
            print(f"Final data axis order: (states, spectral, spatial)")
            return transposed_data
        elif stacked_data.ndim == 4:
            # Data is (N_states, dim1, dim2, dim3) - need to figure out which is which
            # For now, assume it's (states, spatial, spectral, extra_dim)
            if stacked_data.shape[3] == 1:
                # Remove singleton dimension and transpose
                squeezed_data = stacked_data.squeeze(axis=3)
                transposed_data = np.transpose(squeezed_data, (0, 2, 1))
                print(f"Squeezed and transposed data shape: {transposed_data.shape}")
                return transposed_data
            else:
                # For now, just take the first slice and transpose
                sliced_data = stacked_data[:, :, :, 0]
                transposed_data = np.transpose(sliced_data, (0, 2, 1))
                print(f"Sliced and transposed data shape: {transposed_data.shape}")
                return transposed_data
        else:
            raise ValueError(f"Unsupported data dimensionality: {stacked_data.ndim}")
    
    def display_data(self, data: np.ndarray, state_names: List[str]):
        """
        Display the loaded data using the data manager.
        
        Args:
            data: Processed data array
            state_names: Names for the states
        """
        try:
            # Determine the axis specification based on data shape
            if data.ndim == 3:
                # Assume (states, spectral, spatial)
                axes = ['states', 'spectral', 'spatial']
            elif data.ndim == 2:
                # Assume (spectral, spatial)
                axes = ['spectral', 'spatial']
            else:
                raise ValueError(f"Unsupported data dimensionality: {data.ndim}")
            
            # Extract filename for title
            filename = os.path.basename(self.current_file_path) if self.current_file_path else "Loaded Data"
            title = f"Spectator - {filename}"
            
            # Use the data manager to display the data
            viewer = data_manager.display_data(
                data, 
                *axes, 
                title=title, 
                state_names=state_names
            )
            
            return viewer
            
        except Exception as e:
            error_msg = f"Error displaying data: {str(e)}"
            self.loadingError.emit(error_msg)
        
        return None

    def get_current_info(self):
        """Return info section from last loaded file, if available."""
        return self.current_info


class FileListingController(QtWidgets.QWidget):
    """Widget for browsing and selecting .dat files from directories."""
    
    # Signal emitted when a file is selected for loading
    fileSelected = QtCore.pyqtSignal(str)  # file_path
    # Signal emitted when user requests an Info dock
    infoRequested = QtCore.pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize instance variables
        self.directory = ['']
        self.selected_directories = ['']
        self.file_paths = []  # Store full file paths
        self._dir_paths = []  # When listing directories, store abs paths
        self._listing_mode = 'files'  # 'files' or 'dirs'
        # Load config and precompute start directory
        ensure_example_config()
        self._config = load_config()
        # Load from config (with defaults applied by loader)
        self.must_be_in_directory = self._config.get("must_be_in_directory", "reduced")
        self.excluded_file_types = list(self._config.get("excluded_file_terms", ["cal", "dark", "ff"]))
        self._start_directory = self._compute_start_directory()
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        # Auto-populate listing if a valid start directory is configured
        try:
            if self._start_directory and os.path.isdir(self._start_directory):
                if self._config.get('auto_navigate_recent', False):
                    # Auto-list files directly
                    self._populate_from_paths([self._start_directory])
                    self.directory = [self._start_directory]
                else:
                    # List subdirectories for user to choose
                    self._populate_directories(self._start_directory)
                    self.directory = [self._start_directory]
        except Exception:
            pass
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Create widgets
        self.info_button = QtWidgets.QPushButton('List info')
        self.info_button.clicked.connect(self.infoRequested.emit)
        self.button = QtWidgets.QPushButton('Choose Directory')
        self.button.clicked.connect(self.handleChooseDirectories)
        self.refresh_button = QtWidgets.QPushButton('Refresh')
        self.refresh_button.clicked.connect(self.refresh_listing)
        self.listWidget = QtWidgets.QListWidget()
        self.directorylabel = QtWidgets.QLabel()
        self.fileinfolabel1 = QtWidgets.QLabel()
        self.fileinfolabel2 = QtWidgets.QLabel()
        
        # Set initial text
        initial_dir = self._start_directory or self.directory[0]
        self.directorylabel.setText('Current directory: ' + initial_dir)
        self.directorylabel.setWordWrap(True)
        self.fileinfolabel1.setText('Files sub-directory: ' + self.must_be_in_directory)
        
        file_type_string = " ".join(self.excluded_file_types)
        self.fileinfolabel2.setText('Excluded files: ' + file_type_string)
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.listWidget)
        # Place 'List info' button above the other buttons
        layout.addWidget(self.info_button)
        # Buttons row (Choose + Refresh)
        buttons_row = QtWidgets.QHBoxLayout()
        buttons_row.addWidget(self.button)
        buttons_row.addWidget(self.refresh_button)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)
        layout.addWidget(self.directorylabel)
        layout.addWidget(self.fileinfolabel1)
        layout.addWidget(self.fileinfolabel2)
    
    def _connect_signals(self):
        """Connect widget signals to handlers."""
        self.listWidget.itemClicked.connect(self.on_file_clicked)
    
    def on_file_clicked(self, item):
        """Handle file selection from the list."""
        try:
            # Extract the item number from the display text (e.g., "1. filename.dat")
            item_text = item.text()
            print(f"[DEBUG][FileListingController] item clicked: '{item_text}' mode={self._listing_mode}")
            
            # Skip if this is an info message (no files found)
            if not item_text or item_text.startswith("No .dat files") or item_text.startswith("Requirements") or item_text.startswith("•"):
                return
            
            item_number = int(item_text.split('.')[0]) - 1
            
            if self._listing_mode == 'files':
                if 0 <= item_number < len(self.file_paths):
                    file_path = self.file_paths[item_number]
                    print(f"[DEBUG][FileListingController] emitting fileSelected: {file_path}")
                    # Emit signal with the selected file path
                    self.fileSelected.emit(file_path)
            elif self._listing_mode == 'dirs':
                if 0 <= item_number < len(self._dir_paths):
                    chosen_dir = self._dir_paths[item_number]
                    # Populate files from this directory
                    self._populate_from_paths([chosen_dir])
                    self._listing_mode = 'files'
                    self.directory = [chosen_dir]
        
        except (ValueError, IndexError) as e:
            pass

    def handleChooseDirectories(self):
        """Handle directory selection and populate file list."""
        dialog = QtWidgets.QFileDialog(self)
        dialog.setWindowTitle('Choose a directory')
        dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        # Set starting directory from config
        if self._start_directory and os.path.isdir(self._start_directory):
            try:
                dialog.setDirectory(self._start_directory)
            except Exception:
                pass
        
        for view in dialog.findChildren((QtWidgets.QListView, QtWidgets.QTreeView)):
            if isinstance(view.model(), QtWidgets.QFileSystemModel):
                view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected = dialog.selectedFiles()
            # If user chose the base (parent) directory, do NOT list files; show its subdirectories
            base = selected[0] if selected else self.directory[0]
            if self._start_directory and os.path.abspath(base) == os.path.abspath(self._start_directory):
                self._populate_directories(base)
            else:
                # Otherwise, attempt to list files under the chosen directory; if none, show its subdirectories
                self._populate_from_paths(selected)
            self.directory = selected
        
        dialog.deleteLater()

    def _populate_from_paths(self, selected_paths: list[str]):
        """Populate the list widget and labels from selected directories (no dialog)."""
        try:
            self.listWidget.clear()
            self.file_paths.clear()
            self._listing_mode = 'files'

            # Never list files directly for the configured base (parent) directory; show its subdirectories instead
            try:
                if selected_paths and self._base_parent_dir and os.path.abspath(selected_paths[0]) == os.path.abspath(self._base_parent_dir):
                    self._populate_directories(selected_paths[0])
                    return
            except Exception:
                pass

            list_files, list_dirs = self.all_dat_files(
                selected_paths,
                excludes=self.excluded_file_types,
                in_dir=self.must_be_in_directory
            )

            if list_files:
                show_file_list = []
                for n, (file, directory) in enumerate(zip(list_files, list_dirs)):
                    full_path = os.path.join(directory, file)
                    self.file_paths.append(full_path)
                    show_file_list.append(str(n+1) + '. ' + file)
                self.listWidget.addItems(show_file_list)

                chosen_dir = selected_paths[0] if selected_paths else self.directory[0]
                self.directorylabel.setText(f'Current directory: {chosen_dir}')
            else:
                # No files found: show directories for user to drill down
                base = selected_paths[0] if selected_paths else self.directory[0]
                self._populate_directories(base)
                return

            # Track the directories used for listing
            self.selected_directories = list_dirs
        except Exception:
            pass

    def refresh_listing(self):
        """Refresh current listing according to current mode and directory."""
        try:
            current_base = self.directory[0] if self.directory else (self._start_directory or '')
            if self._listing_mode == 'files':
                # Re-list files for the current directory
                self._populate_from_paths([current_base])
            else:
                # Re-list subdirectories for the current base
                self._populate_directories(current_base)
        except Exception:
            pass

    def show_info(self):
        """Show a small dialog with listing rules and current context."""
        try:
            base = self.directory[0] if self.directory else (self._start_directory or '')
            mode = self._listing_mode
            must_dir = self.must_be_in_directory
            excludes = ', '.join(self.excluded_file_types)
            auto_recent = bool(self._config.get('auto_navigate_recent', False))
            msg = (
                f"Current directory: {base}\n"
                f"Mode: {mode}\n\n"
                f"Listing rules:\n"
                f"- Only .dat files under subfolders containing '{must_dir}' are shown.\n"
                f"- Excluded filename terms: {excludes or '(none)'}\n"
                f"- Auto-navigate recent: {'on' if auto_recent else 'off'}\n\n"
                f"Tips:\n"
                f"- Click a directory to drill down.\n"
                f"- Use Refresh to re-scan for newly created files.\n"
            )
            QtWidgets.QMessageBox.information(self, 'Files listing info', msg)
        except Exception:
            pass

    def _populate_directories(self, base_dir: str):
        """Populate the list with immediate subdirectories of base_dir (no filtering)."""
        try:
            self.listWidget.clear()
            self.file_paths.clear()
            self._dir_paths.clear()
            self._listing_mode = 'dirs'

            if not base_dir or not os.path.isdir(base_dir):
                self.listWidget.addItem("Base directory does not exist.")
                # Disable selection for info items
                for i in range(self.listWidget.count()):
                    item = self.listWidget.item(i)
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
                return

            # List immediate subdirectories
            entries = []
            try:
                for entry in sorted(os.listdir(base_dir)):
                    full = os.path.join(base_dir, entry)
                    if os.path.isdir(full):
                        entries.append((entry, full))
            except Exception:
                entries = []

            if entries:
                show_dirs = []
                for n, (name, full) in enumerate(entries):
                    self._dir_paths.append(full)
                    show_dirs.append(f"{n+1}. {name}")
                self.listWidget.addItems(show_dirs)
                self.directorylabel.setText(f"Current directory: {base_dir}")
            else:
                self.listWidget.addItem("No subdirectories found.")
                for i in range(self.listWidget.count()):
                    item = self.listWidget.item(i)
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
                self.directorylabel.setText(f"Current directory: {base_dir}")
        except Exception:
            # Non-fatal UI population errors should not crash the app
            pass

    def _compute_start_directory(self) -> str:
        """Compute the initial directory for the file chooser based on config.

        If auto_navigate_recent is True, return the most recent YYMMDD subdirectory
        within default_data_base_dir. Supports an optional 4-digit year layer:
        base_dir/YYYY/YYMMDD. Otherwise return default_data_base_dir.
        """
        import re
        base_dir = self._config.get('default_data_base_dir')
        if not base_dir:
            return ''
        base_dir = os.path.abspath(os.path.expanduser(base_dir))
        if not os.path.isdir(base_dir):
            return base_dir

        if not self._config.get('auto_navigate_recent', False):
            return base_dir

        # Find subdirectories containing a YYMMDD token (may have prefixes/suffixes)
        # at base level OR within optional 4-digit year folders (e.g., 2025/250822).
        # Pick the latest valid date.
        yymmdd_re = re.compile(r'(\d{6})')
        year_re = re.compile(r'^(19|20)\d{2}$')

        def extract_token(name: str) -> str | None:
            m = yymmdd_re.search(name)
            return m.group(1) if m else None

        def parse_yymmdd(token: str, fallback_year: int | None = None):
            yy = int(token[0:2])
            mm = int(token[2:4])
            dd = int(token[4:6])
            # Basic sanity checks on month/day
            if not (1 <= mm <= 12 and 1 <= dd <= 31):
                return None
            year = (2000 + yy) if fallback_year is None else fallback_year
            return year, mm, dd

        best_tuple = None  # (year, mm, dd, path)

        try:
            for entry in os.listdir(base_dir):
                full = os.path.join(base_dir, entry)
                if not os.path.isdir(full):
                    continue

                # Case 1: base_dir/... with a YYMMDD token in the name
                token = extract_token(entry)
                if token:
                    parsed = parse_yymmdd(token)
                    if parsed is not None:
                        y, m, d = parsed
                        tup = (y, m, d, full)
                        if best_tuple is None or tup[:3] > best_tuple[:3]:
                            best_tuple = tup
                        # Do not continue here; a dir can also be a YYYY year dir

                # Case 2: base_dir/YYYY/YYMMDD
                if year_re.match(entry):
                    year_val = int(entry)
                    try:
                        for sub in os.listdir(full):
                            sub_full = os.path.join(full, sub)
                            if os.path.isdir(sub_full):
                                sub_token = extract_token(sub)
                                if sub_token:
                                    parsed = parse_yymmdd(sub_token, fallback_year=year_val)
                                    if parsed is not None:
                                        y, m, d = parsed
                                        tup = (y, m, d, sub_full)
                                        if best_tuple is None or tup[:3] > best_tuple[:3]:
                                            best_tuple = tup
                    except Exception:
                        # ignore unreadable year dir
                        pass
        except Exception:
            # If listing base_dir fails, fall back
            return base_dir

        if best_tuple is None:
            return base_dir

        chosen = best_tuple[3]
        # If a specific subdirectory is required (e.g., 'reduced'), and it exists
        # inside the chosen date directory, auto-descend into it.
        try:
            must_dir = self._config.get('must_be_in_directory')
        except Exception:
            must_dir = None
        if must_dir:
            candidate = os.path.join(chosen, must_dir)
            if os.path.isdir(candidate):
                return candidate
        return chosen

        
    def all_dat_files(self, directories, excludes=None, in_dir=None):
        """Find all .dat files in the specified directories."""
        if excludes is None:
            excludes = []
        if in_dir is None:
            in_dir = self.must_be_in_directory
            
        # Quiet operation: no debug printing
        
        list_of_files = []
        list_of_directories = []
        total_sav_files = 0
        
        for root, dirs, files in os.walk(directories[0]):       
            dat_files_in_dir = [f for f in files if f.endswith('.dat')]
            if dat_files_in_dir:
                total_sav_files += len(dat_files_in_dir)
                
                for file in dat_files_in_dir:
                    # Check directory requirement
                    if in_dir in root:
                        
                        # Check exclusions
                        use = True
                        for exclude in excludes:
                            if exclude in file:
                                use = False
                                break
                        
                        if use:
                            list_of_files.append(file)
                            list_of_directories.append(root)
                        else:
                            pass
                    else:
                        pass
        # No summary prints
                
        return list_of_files, list_of_directories     
