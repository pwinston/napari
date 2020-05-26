"""Debug menu.

The debug menu is for developer-focused functionality that we want to be
easy-to-use and discoverable, but which is not for the average user.

Current Items
-------------
Start Trace File...
Stop Trace File
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

        record = QAction('Start Trace File...', window)
        record.setShortcut('Alt+T')
        record.setStatusTip('Start recording a performance trace file')
        record.triggered.connect(self._start_trace_dialog)
        self.debug_menu.addAction(record)

        record = QAction('Stop Trace File', window)
        record.setShortcut('Shift+Alt+T')
        record.setStatusTip('Stop recording a performance trace file')
        record.triggered.connect(perf.timers.stop_trace_file)
        self.debug_menu.addAction(record)

    def _start_trace_dialog(self):
        """Show save file dialog and start recording."""
        viewer = self._main_window.qt_viewer

        filename, _ = QFileDialog.getSaveFileName(
            parent=viewer,
            caption='Record performance trace file',
            directory=viewer._last_visited_dir,
            filter="Trace Files (*.json)",
        )
        if filename:
            filename = _ensure_extension(filename, '.json')
            perf.timers.start_trace_file(filename)
