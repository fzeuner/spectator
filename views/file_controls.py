"""
File control widgets for data loading.

This module contains control panels for selecting and loading data files.
"""

import os
from pyqtgraph.Qt import QtCore, QtWidgets
from scipy.io import readsav


class FilesControlWidget(QtWidgets.QWidget):
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
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Create widgets
        self.button = QtWidgets.QPushButton('Choose Directory')
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
        
        # Add widgets to layout
        self.main_layout.addWidget(self.listWidget)
        self.main_layout.addWidget(self.button)
        self.main_layout.addWidget(self.directorylabel)
        self.main_layout.addWidget(self.fileinfolabel1)
        self.main_layout.addWidget(self.fileinfolabel2)
    
    def _connect_signals(self):
        """Connect widget signals to handlers."""
        self.button.clicked.connect(self.handleChooseDirectories)
        self.listWidget.itemClicked.connect(self.on_file_clicked)

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
            
            list_files, list_dirs = self.all_sav_files(
                dialog.selectedFiles(),
                excludes=self.excluded_file_types,
                in_dir=self.must_be_in_directory
            )
            
            # Store full file paths for later use
            for i, (file, directory) in enumerate(zip(list_files, list_dirs)):
                full_path = os.path.join(directory, file)
                self.file_paths.append(full_path)
                
                # Create display name with number
                display_name = f"{i+1}. {file}"
                self.listWidget.addItem(display_name)
            
            self.directory = dialog.selectedFiles()
            self.directorylabel.setText('Current directory: ' + self.directory[0])
            self.selected_directories = list_dirs
        
        dialog.deleteLater()

        
    def all_sav_files(self, directories, excludes=None, in_dir=None):
        """Find all .sav files in the specified directories."""
        if excludes is None:
            excludes = []
        if in_dir is None:
            in_dir = self.must_be_in_directory
            
        list_of_files = []
        list_of_directories = []
        
        for root, dirs, files in os.walk(directories[0]):       
            for file in files:
                if in_dir in root and file.endswith('.sav'):
                    use = True
                    for exclude in excludes:
                        if exclude in file:
                            use = False
                            break
                    if use:
                        list_of_files.append(file)
                        list_of_directories.append(root)
                 
        return list_of_files, list_of_directories
    
    def on_file_clicked(self, item):
        """Handle file selection from the list."""
        try:
            # Extract the item number from the display text (e.g., "1. filename.sav")
            item_text = item.text()
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
