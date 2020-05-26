"""Debug menu.

The debug menu is for developer-focused functionality that we want to be
easy-to-use and discoverable, but which is not for the average user.

Current Items
-------------
Start Trace File...
Stop Trace File
"""
from qtpy.QtCore import QTimer
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
        self.start_trace = self._add_start_trace()
        self.stop_trace = self._add_stop_trace()
        self._set_recording(False)

    @property
    def window(self):
        return self._main_window._qt_window

    def _set_recording(self, recording: bool):
        """Enable/disable menu items.

        Parameters
        ----------
        record : bool
            Are we currently recording a trace file.
        """
        self.start_trace.setEnabled(not recording)
        self.stop_trace.setEnabled(recording)

    def _add_start_trace(self):
        """Add "start trace" menu item.
        """
        start = QAction('Start Trace File...', self.window)
        start.setShortcut('Alt+T')
        start.setStatusTip('Start recording a performance trace file')
        start.triggered.connect(self._start_trace)
        self.debug_menu.addAction(start)
        return start

    def _add_stop_trace(self):
        """Add "stop trace" menu item.
        """
        stop = QAction('Stop Trace File', self.window)
        stop.setShortcut('Shift+Alt+T')
        stop.setStatusTip('Stop recording a performance trace file')
        stop.triggered.connect(self._stop_trace)
        self.debug_menu.addAction(stop)
        return stop

    def _start_trace(self):
        """Start recording a trace file."""
        viewer = self._main_window.qt_viewer

        filename, _ = QFileDialog.getSaveFileName(
            parent=viewer,
            caption='Record performance trace file',
            directory=viewer._last_visited_dir,
            filter="Trace Files (*.json)",
        )
        if filename:
            filename = _ensure_extension(filename, '.json')

            def start_trace():
                perf.timers.start_trace_file(filename)
                self._set_recording(True)

            # If we don't start with a timer the first event in the trace will
            # be a super long "MetaCall" event for the file dialog.
            QTimer.singleShot(0, start_trace)

    def _stop_trace(self):
        """Stop recording a trace file.
        """
        perf.timers.stop_trace_file()
        self._set_recording(False)
