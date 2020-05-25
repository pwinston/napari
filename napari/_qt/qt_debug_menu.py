"""Debug menu.

The debug menu is for developer-focused functionality that we want to be
easy-to-use and discoverable, but which is not for the average user.

Right now perfmon's "Record Trace File..." is the only item but we should
have non-perf related items soon.
"""
from qtpy.QtWidgets import QAction, QFileDialog

from ..utils import perf


def _ensure_extension(filename: str, extension: str):
    """Add the extension if needed."""
    if filename.endswith(extension):
        return filename
    return filename + extension


class DebugMenu:
    def __init__(self, main_window):
        """Create the debug menu.

        Parameters
        ----------
        main_menu : qtpy.QtWidgets.QMainWindow.menuBar
            We add ourselves to this menu.
        """
        self._main_window = main_window
        self.debug_menu = self._main_window.main_menu.addMenu('&Debug')
        self._add_perf_actions()

    def _add_perf_actions(self):
        """Add performance related debug menu items.
        """
        window = self._main_window._qt_window

        record = QAction('Record Trace File...', window)
        record.setShortcut('Alt+T')
        record.setStatusTip('Record performance trace file.')
        record.triggered.connect(self._record_trace_dialog)
        self.debug_menu.addAction(record)

    def _record_trace_dialog(self):
        """Record a performance trace file."""
        viewer = self._main_window.qt_viewer

        filename, _ = QFileDialog.getSaveFileName(
            parent=viewer,
            caption='Record performance trace file',
            directory=viewer._last_visited_dir,
            filter="Trace Files (*.json)",
        )
        if filename:
            file_with_extension = _ensure_extension(filename, '.json')
            perf.record_trace_file(file_with_extension)
