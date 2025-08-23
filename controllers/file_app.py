from __future__ import annotations

import sys
from typing import List

import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets
import qdarkstyle
from pyqtgraph.dockarea import DockArea, Dock
from .file_controllers import FileListingController, FileLoadingController
from utils.info_formatter import format_info_to_html
from utils.colors import getWidgetColors


class FileBrowserApp(QtWidgets.QMainWindow):
    """
    A lightweight app that exposes only the file browser and info display.
    When a file is loaded, it calls display_data to open the full Spectator viewer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spectator – Files")
        self.resize(900, 600)

        # Controllers
        self.file_loader = FileLoadingController(self)
        self.file_lister = FileListingController(self)

        # Central DockArea with two docks: Files (narrow) and Info (wide)
        self.dock_area = DockArea()
        self.setCentralWidget(self.dock_area)

        # Files dock (narrow)
        self.files_dock = Dock("Files", closable=False, size=(1, 1))  # relative size
        files_container = QtWidgets.QWidget()
        files_layout = QtWidgets.QVBoxLayout(files_container)
        files_layout.setContentsMargins(8, 8, 8, 8)
        files_layout.addWidget(self.file_lister)
        # Make files dock relatively narrow
        files_container.setMinimumWidth(220)
        files_container.setMaximumWidth(420)
        self.files_dock.addWidget(files_container)

        # Info dock (wide)
        self.info_dock = Dock("Info", closable=False, size=(3, 1))  # wider than Files
        info_container = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(info_container)
        info_layout.setContentsMargins(8, 8, 8, 8)
        self.info_view = QtWidgets.QTextBrowser()
        self.info_view.setOpenExternalLinks(True)
        self.info_view.setReadOnly(True)
        # Make info dock significantly wider
        info_container.setMinimumWidth(600)
        # Apply theme-based stylesheet from utils/colors.py
        self._apply_info_dock_style()
        info_layout.addWidget(self.info_view)
        self.info_dock.addWidget(info_container)

        # Add docks to area: Info on the right, Files on the left
        self.dock_area.addDock(self.files_dock)
        self.dock_area.addDock(self.info_dock, 'right', self.files_dock)

        # Wire signals
        self._connect_signals()

    def _connect_signals(self):
        # Clicking a file in the list triggers loading
        self.file_lister.fileSelected.connect(self._on_file_selected)
        # Ask to show info
        self.file_lister.infoRequested.connect(self._on_info_requested)
        # Loader results
        self.file_loader.dataLoaded.connect(self._on_data_loaded)
        self.file_loader.loadingError.connect(self._on_loading_error)

    # Slots
    @QtCore.pyqtSlot(str)
    def _on_file_selected(self, file_path: str):
        # Delegate to loader
        self.statusBar().showMessage(f"Loading: {file_path}")
        self.file_loader.load_file(file_path)

    @QtCore.pyqtSlot(np.ndarray, list)
    def _on_data_loaded(self, data: np.ndarray, state_names: List[str]):
        self.statusBar().clearMessage()
        # Update info dock contents (keep info visible)
        self._refresh_info_dock()
        # Briefly print loaded data info to terminal
        try:
            shape = getattr(data, 'shape', None)
            print(f"Loaded array shape: {shape}")
        except Exception:
            pass
        if state_names:
            print("State names:", ", ".join(state_names))
        # Display via main viewer
        try:
            self.file_loader.display_data(data, state_names)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Display Error", str(e))

    @QtCore.pyqtSlot()
    def _on_info_requested(self):
        # Populate info; dock is always visible
        self._refresh_info_dock()

    @QtCore.pyqtSlot(str)
    def _on_loading_error(self, msg: str):
        self.statusBar().clearMessage()
        QtWidgets.QMessageBox.critical(self, "Loading Error", msg)

    # Helpers
    def _refresh_info_dock(self):
        info = None
        try:
            info = self.file_loader.get_current_info()
        except Exception:
            info = None
        if info is None:
            self.info_view.setHtml("<i>No info available.</i>")
        else:
            try:
                html = format_info_to_html(info)
            except Exception:
                html = "<i>Failed to format info.</i>"
            self.info_view.setHtml(html)

    def _apply_info_dock_style(self):
        """Apply stylesheet to the Info dock and viewer based on theme colors."""
        colors = getWidgetColors('dark')  # default to dark theme for now
        bg = colors.get('background', '#19232D')
        fg = colors.get('foreground', '#FFFFFF')
        accent = colors.get('accent', '#375A7F')

        view_qss = (
            f"QTextBrowser {{ background: {bg}; color: {fg}; selection-background-color: {accent}; }}"
            f"QTextBrowser QWidget {{ background: {bg}; color: {fg}; }}"
            f"a, QTextBrowser::link {{ color: {accent}; }}"
        )
        self.info_view.setStyleSheet(view_qss)

        # Also style the Dock container background to match
        try:
            self.info_dock.widgets[0].setStyleSheet(f"background: {bg}; color: {fg};")
        except Exception:
            pass


def run():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    try:
        # Use environment variable or default to dark style
        dark_stylesheet = qdarkstyle.load_stylesheet_from_environment(is_pyqtgraph=True)
        app.setStyleSheet(dark_stylesheet)
    except ImportError:
        print("qdarkstyle not found. Using default Qt style.")
    except Exception as e:
        print(f"Could not apply qdarkstyle: {e}")
    w = FileBrowserApp()
    w.show()
    return app.exec_()
