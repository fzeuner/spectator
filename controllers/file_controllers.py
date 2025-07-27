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
        
    def load_file(self, file_path: str):
        """
        Load a .dat file and emit the processed data.
        
        Args:
            file_path: Path to the .dat file to load
        """
        try:
            print(f"Loading file: {file_path}")
            
            # Use datReader to load the file
            reader = datReader(path=file_path, python_dict=True, verbose=True)
            
            # Get the images array
            images_array = reader.getDatImagesArray()
            
            # Stack all images along the first axis (states axis)
            if not images_array:
                raise ValueError("Empty images array")
            
            raw_data_array = np.stack(images_array, axis=0)
            print(f"Raw data shape: {raw_data_array.shape}")
            print(f"Raw data axis order: (states, spatial, spectral)")
            
            # Extract state names from the raw data keys
            raw_data = reader.getDat()
            state_names = list(raw_data.keys()) if raw_data else None
            
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
            
            print(f"Successfully loaded and processed data with shape: {processed_data.shape}")
            
            # Store current data
            self.current_data = processed_data
            self.current_file_path = file_path
            
            # Emit signal with loaded data
            self.dataLoaded.emit(processed_data, state_names)
                
        except Exception as e:
            error_msg = f"Error loading file {file_path}: {str(e)}"
            print(error_msg)
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
            
            print(f"Data displayed successfully with title: {title}")
            return viewer
            
        except Exception as e:
            error_msg = f"Error displaying data: {str(e)}"
            print(error_msg)
            self.loadingError.emit(error_msg)
            return None


class FileListingController(QtWidgets.QWidget):
    """Widget for browsing and selecting .dat files from directories."""
    
    # Signal emitted when a file is selected for loading
    fileSelected = QtCore.pyqtSignal(str)  # file_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize instance variables
        self.directory = ['']
        self.selected_directories = ['']
        self.must_be_in_directory = "reduced"
        self.excluded_file_types = ["cal", "dark", "ff"]
        self.file_paths = []  # Store full file paths
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Create widgets
        self.button = QtWidgets.QPushButton('Choose Directory')
        self.button.clicked.connect(self.handleChooseDirectories)
        self.listWidget = QtWidgets.QListWidget()
        self.directorylabel = QtWidgets.QLabel()
        self.fileinfolabel1 = QtWidgets.QLabel()
        self.fileinfolabel2 = QtWidgets.QLabel()
        
        # Set initial text
        self.directorylabel.setText('Current directory: ' + self.directory[0])
        self.directorylabel.setWordWrap(True)
        self.fileinfolabel1.setText('Files sub-directory: ' + self.must_be_in_directory)
        
        file_type_string = " ".join(self.excluded_file_types)
        self.fileinfolabel2.setText('Excluded files: ' + file_type_string)
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.listWidget)
        layout.addWidget(self.button)
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
            
            # Skip if this is an info message (no files found)
            if not item_text or item_text.startswith("No .dat files") or item_text.startswith("Requirements") or item_text.startswith("•"):
                return
            
            item_number = int(item_text.split('.')[0]) - 1
            
            if 0 <= item_number < len(self.file_paths):
                file_path = self.file_paths[item_number]
                print(f"Selected file: {file_path}")
                # Emit signal with the selected file path
                self.fileSelected.emit(file_path)
            else:
                print(f"Invalid file selection: index {item_number} out of range")
                
        except (ValueError, IndexError) as e:
            print(f"Error processing file selection: {e}")

    def handleChooseDirectories(self):
        """Handle directory selection and populate file list."""
        dialog = QtWidgets.QFileDialog(self)
        dialog.setWindowTitle('Choose a directory')
        dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        
        for view in dialog.findChildren((QtWidgets.QListView, QtWidgets.QTreeView)):
            if isinstance(view.model(), QtWidgets.QFileSystemModel):
                view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.listWidget.clear()
            self.file_paths.clear()
            
            list_files, list_dirs = self.all_dat_files(
                dialog.selectedFiles(),
                excludes=self.excluded_file_types,
                in_dir=self.must_be_in_directory
            )
            
            if list_files:
                # Files found - display them and store full paths
                show_file_list = []
                for n, (file, directory) in enumerate(zip(list_files, list_dirs)):
                    # Store full file path
                    full_path = os.path.join(directory, file)
                    self.file_paths.append(full_path)
                    
                    # Create display name with number
                    show_file_list.append(str(n+1) + '. ' + file)
                
                self.listWidget.addItems(show_file_list)
                
                # Update status
                self.directorylabel.setText(f'Current directory: {self.directory[0]} ({len(list_files)} files found)')
            else:
                # No files found - provide feedback
                self.listWidget.addItem("No .dat files found in 'reduced' subdirectories")
                self.listWidget.addItem("")
                self.listWidget.addItem("Requirements:")
                self.listWidget.addItem("• Files must be in subdirectories containing 'reduced'")
                self.listWidget.addItem("• Files must have .dat extension")
                self.listWidget.addItem(f"• Files must not contain: {', '.join(self.excluded_file_types)}")
                
                # Disable selection for info items
                for i in range(self.listWidget.count()):
                    item = self.listWidget.item(i)
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
                
                self.directorylabel.setText(f'Current directory: {self.directory[0]} (no files found)')
            
            self.directory = dialog.selectedFiles()
            self.selected_directories = list_dirs
        
        dialog.deleteLater()

        
    def all_dat_files(self, directories, excludes=None, in_dir=None):
        """Find all .dat files in the specified directories."""
        if excludes is None:
            excludes = []
        if in_dir is None:
            in_dir = self.must_be_in_directory
            
        print(f"\n=== DEBUG: Searching for files ===")
        print(f"Base directory: {directories[0]}")
        print(f"Must be in directory containing: '{in_dir}'")
        print(f"Excluded file types: {excludes}")
        
        list_of_files = []
        list_of_directories = []
        total_sav_files = 0
        
        for root, dirs, files in os.walk(directories[0]):       
            dat_files_in_dir = [f for f in files if f.endswith('.dat')]
            if dat_files_in_dir:
                print(f"\nDirectory: {root}")
                print(f"  .dat files found: {len(dat_files_in_dir)}")
                total_sav_files += len(dat_files_in_dir)
                
                for file in dat_files_in_dir:
                    print(f"    Checking: {file}")
                    
                    # Check directory requirement
                    if in_dir in root:
                        print(f"      ✓ Directory contains '{in_dir}'")
                        
                        # Check exclusions
                        use = True
                        for exclude in excludes:
                            if exclude in file:
                                print(f"      ✗ File contains excluded term '{exclude}'")
                                use = False
                                break
                        
                        if use:
                            print(f"      ✓ File passes all filters")
                            list_of_files.append(file)
                            list_of_directories.append(root)
                        else:
                            print(f"      ✗ File excluded")
                    else:
                        print(f"      ✗ Directory does not contain '{in_dir}'")
        
        print(f"\n=== SEARCH SUMMARY ===")
        print(f"Total .dat files found: {total_sav_files}")
        print(f"Files passing filters: {len(list_of_files)}")
        if list_of_files:
            print("Filtered files:")
            for i, (file, dir_path) in enumerate(zip(list_of_files, list_of_directories)):
                print(f"  {i+1}. {file} (in {dir_path})")
        print("=" * 50)
                 
        return list_of_files, list_of_directories     
