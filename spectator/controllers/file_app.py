from __future__ import annotations

import sys
import os
from typing import List

import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui
import qdarkstyle
from pyqtgraph.dockarea import DockArea, Dock
from .file_controllers import FileListingController, FileLoadingController
from ..utils.info_formatter import format_info_to_html
from ..utils.colors import getWidgetColors
from ..utils.fixed_dock_label import FixedDockLabel
from ..config.viewer_config import DEFAULT_AXIS_ORDERS


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
        self.files_dock = Dock(
            "Files",
            closable=False,
            size=(1, 1),
            label=FixedDockLabel("Files"),
        )  # relative size
        files_container = QtWidgets.QWidget()
        files_layout = QtWidgets.QVBoxLayout(files_container)
        files_layout.setContentsMargins(8, 8, 8, 8)
        files_layout.addWidget(self.file_lister)
        # Make files dock relatively narrow
        files_container.setMinimumWidth(220)
        files_container.setMaximumWidth(420)
        self.files_dock.addWidget(files_container)

        # Info dock (wide)
        self.info_dock = Dock(
            "Info",
            closable=False,
            size=(3, 1),
            label=FixedDockLabel("Info"),
        )  # wider than Files
        info_container = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(info_container)
        info_layout.setContentsMargins(8, 8, 8, 8)
        self.info_view = QtWidgets.QTextBrowser()
        self.info_view.setOpenExternalLinks(True)
        self.info_view.setReadOnly(True)
        # Make info dock significantly wider
        info_container.setMinimumWidth(600)
        info_layout.addWidget(self.info_view)
        self.info_dock.addWidget(info_container)

        # Observer log dock (stacked with Info using pyqtgraph Dock tabs)
        self.observer_log_dock = Dock(
            "Observer log",
            closable=False,
            size=(3, 1),
            label=FixedDockLabel("Observer log"),
        )
        observer_container = QtWidgets.QWidget()
        observer_layout = QtWidgets.QVBoxLayout(observer_container)
        observer_layout.setContentsMargins(8, 8, 8, 8)
        self.observer_dir_edit = QtWidgets.QLineEdit()
        # Simple search UI for observer log
        self.observer_search_edit = QtWidgets.QLineEdit()
        self.observer_search_button = QtWidgets.QPushButton("Find next")
        search_row = QtWidgets.QHBoxLayout()
        search_row.addWidget(self.observer_search_edit)
        search_row.addWidget(self.observer_search_button)
        self.observer_log_view = QtWidgets.QTextBrowser()
        self.observer_log_view.setReadOnly(True)
        observer_container.setMinimumWidth(600)
        observer_layout.addWidget(self.observer_dir_edit)
        observer_layout.addLayout(search_row)
        observer_layout.addWidget(self.observer_log_view)
        self.observer_log_dock.addWidget(observer_container)

        # Apply theme-based stylesheet from utils/colors.py
        self._apply_info_dock_style()

        # Add docks to area: Info on the right, Files on the left
        self.dock_area.addDock(self.files_dock)
        self.dock_area.addDock(self.info_dock, 'right', self.files_dock)
        # Stack observer log dock with Info using pyqtgraph's Dock tabs/stacking
        self.dock_area.addDock(self.observer_log_dock, 'above', self.info_dock)
        # Ensure Info is the initially visible/raised dock in this stack
        try:
            self.info_dock.raiseDock()
        except Exception:
            pass

        # Initialize observer log directory based on the same start directory
        # logic as the file browser, but without descending into the
        # must_be_in_directory subfolder (e.g. 'reduced').
        try:
            start_dir = getattr(self.file_lister, '_start_directory', '') or ''
            must_dir = getattr(self.file_lister, 'must_be_in_directory', None)
            if start_dir:
                start_dir = os.path.abspath(os.path.expanduser(start_dir))
                # If the file browser start directory is exactly the special
                # subdirectory (e.g. '.../reduced'), move one level up so the
                # observer log uses the parent directory.
                if must_dir:
                    base, leaf = os.path.split(start_dir.rstrip(os.sep))
                    if leaf == must_dir and base:
                        start_dir = base
                if os.path.isdir(start_dir):
                    self.observer_dir_edit.setText(start_dir)
                    self._load_observer_log_from_dir(start_dir)
        except Exception:
            pass

        # Wire signals
        self._connect_signals()

    def _connect_signals(self):
        # Clicking a file in the list triggers loading
        self.file_lister.fileSelected.connect(self._on_file_selected)
        # 'Display' toggle replaced 'List info' button; info is refreshed automatically on load
        # Loader results
        self.file_loader.dataLoaded.connect(self._on_data_loaded)
        self.file_loader.loadingError.connect(self._on_loading_error)
        # Observer log directory editing
        try:
            self.observer_dir_edit.returnPressed.connect(self._on_observer_dir_entered)
        except Exception:
            pass
        # Observer log text search
        try:
            self.observer_search_button.clicked.connect(self._on_observer_search_clicked)
        except Exception:
            pass

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
        self._refresh_observer_log()
        # Condensed terminal output: only dims line
        try:
            shape = getattr(data, 'shape', None)
            if isinstance(shape, tuple):
                ndim = len(shape)
                try:
                    labels = list(DEFAULT_AXIS_ORDERS[ndim])
                except KeyError:
                    labels = [f"dim{i}" for i in range(ndim)]
                dims_str = ", ".join(f"{label}={shape[i]}" for i, label in enumerate(labels))
                print(f"Loaded array dims: {dims_str}")
        except Exception:
            pass
        # Display via main viewer only if 'Display' toggle is enabled
        try:
            display_enabled = True
            try:
                display_enabled = bool(self.file_lister.display_button.isChecked())
            except Exception:
                display_enabled = True
            if display_enabled:
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

    def _refresh_observer_log(self):
        """Refresh observer log based on current data file and directory field.

        Default behavior:
        - If observer_dir_edit has a valid directory, use it as base.
        - Otherwise, infer base from the data file path by going one level
          above an 'automatic' directory, and update observer_dir_edit.
        """
        # If user has entered a directory, prefer that
        base_dir = None
        try:
            candidate = self.observer_dir_edit.text().strip()
        except Exception:
            candidate = ""
        if candidate:
            if os.path.isdir(candidate):
                base_dir = candidate
        if base_dir is None:
            # Derive from current data file path
            path = None
            try:
                path = self.file_loader.current_file_path
            except Exception:
                path = None
            if not path:
                self.observer_log_view.setHtml("<i>No observer log available.</i>")
                return

            norm_path = os.path.normpath(path)
            parts = norm_path.split(os.sep)
            if "automatic" in parts:
                idx = parts.index("automatic")
                base_dir = os.sep.join(parts[:idx]) or os.sep
            else:
                # Fallback: use directory of the current file
                base_dir = os.path.dirname(norm_path) or os.sep

            if not base_dir or not os.path.isdir(base_dir):
                self.observer_log_view.setHtml("<i>No observer log found (base directory missing).</i>")
                return

            # Update the directory field to show the inferred base
            try:
                self.observer_dir_edit.setText(base_dir)
            except Exception:
                pass

        # At this point base_dir is a valid directory; load log from it
        self._load_observer_log_from_dir(base_dir)

    def _load_observer_log_from_dir(self, base_dir: str):
        try:
            candidates = []
            for name in sorted(os.listdir(base_dir)):
                if name.startswith("csi_"):
                    full = os.path.join(base_dir, name)
                    if os.path.isfile(full):
                        candidates.append(full)

            if not candidates:
                self.observer_log_view.setHtml("<i>No observer log found (no 'csi_' file).")
                return

            log_path = candidates[0]
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except Exception:
                self.observer_log_view.setHtml("<i>Failed to read observer log file.</i>")
                return

            self.observer_log_view.setPlainText(text)
        except Exception:
            self.observer_log_view.setHtml("<i>Failed to load observer log.</i>")

    def _on_observer_dir_entered(self):
        """Handle manual edits of the observer log directory path."""
        try:
            path = self.observer_dir_edit.text().strip()
        except Exception:
            path = ""
        if not path:
            return
        if not os.path.isdir(path):
            self.observer_log_view.setHtml("<i>Observer directory does not exist.</i>")
            return
        self._load_observer_log_from_dir(path)

    def _on_observer_search_clicked(self):
        """Find next occurrence of the search text in the observer log, wrapping."""
        try:
            text = self.observer_search_edit.text()
        except Exception:
            text = ""
        if not text:
            return

        # Try to find next occurrence from current cursor position
        found = self.observer_log_view.find(text)
        if not found:
            # Wrap: move cursor to start and search again
            cursor = self.observer_log_view.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            self.observer_log_view.setTextCursor(cursor)
            self.observer_log_view.find(text)

    def _apply_info_dock_style(self):
        """Apply stylesheet to the Info dock and viewer based on theme colors."""
        colors = getWidgetColors('dark')  # default to dark theme for now
        bg = colors.get('background', '#19232D')
        fg = colors.get('foreground', '#FFFFFF')
        accent = colors.get('accent', '#375A7F')

        # Info view keeps the accent color for selections
        info_qss = (
            f"QTextBrowser {{ background: {bg}; color: {fg}; selection-background-color: {accent}; }}"
            f"QTextBrowser QWidget {{ background: {bg}; color: {fg}; }}"
            f"a, QTextBrowser::link {{ color: {accent}; }}"
        )
        self.info_view.setStyleSheet(info_qss)

        # Observer log view uses red selection background so search matches
        # are clearly visible.
        observer_qss = (
            f"QTextBrowser {{ background: {bg}; color: {fg}; selection-background-color: red; }}"
            f"QTextBrowser QWidget {{ background: {bg}; color: {fg}; }}"
            f"a, QTextBrowser::link {{ color: {accent}; }}"
        )
        try:
            self.observer_log_view.setStyleSheet(observer_qss)
        except Exception:
            pass

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
    return app.exec()
