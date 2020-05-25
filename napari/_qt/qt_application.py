"""Defines our QtApplication.

Our QtApplication is either:
1) QApplication in the normal case.
2) PerfmonApplication if NAPARI_PERFMON environment variable is set.

PerfmonApplication defined below adds timing of every Qt Event.
"""
from qtpy.QtWidgets import QApplication

from ..utils import perf


def _get_timer_name(receiver, event) -> str:
    """Return a name for this event.

    Parameters
    ----------
    receiver : QWidget
        The receiver of the event.
    event : QEvent
        The event name.

    Returns
    -------
    timer_name : str

    Notes
    -----
    If no object we return <event_name>.
    If there's an object we return <event_name>:<object_name>.

    This our own made up format we can revise as needed.
    """
    # For an event.type() like "PySide2.QtCore.QEvent.Type.WindowIconChange"
    # we set event_str to just the final "WindowIconChange" part.
    event_str = str(event.type()).split(".")[-1]

    try:
        object_name = receiver.objectName()
    except AttributeError:
        # During shutdown the call to receiver.objectName() can fail with
        # "missing objectName attribute". Ignore and assume no object name.
        object_name = None

    if object_name:
        return f"{event_str}:{object_name}"

    # Many events have no object, only an event.
    return event_str


class TimedApplication(QApplication):
    """Extend QApplication to time Qt Events.

    There are 3 main parts to performance monitoring today:
    1) PerfmonApplication: times Qt Events.
    2) PerfTimers: stores timing data, optionally writes to chrome://tracing.
    3) QtPerformance: dockable widget which displays perf information.

    Notes
    -----
    Qt Event handling is nested. A call to notify() can trigger other calls to
    notify() prior to the first one finishing, even several levels deep. The
    hierarchy of timers is displayed correctly in the chrome://tracing GUI.

    Seeing the structure of the event handling hierarchy can be very informative
    even apart from the timing part.
    """

    def notify(self, receiver, event):
        """Time events while we handle them."""
        timer_name = _get_timer_name(receiver, event)

        # Time the event while we handle it.
        with perf.perf_timer(timer_name, "qt_event"):
            return QApplication.notify(self, receiver, event)


if perf.USE_PERFMON:
    # Use our performance monitoring version.
    QtApplication = TimedApplication
else:
    # Use the normal stock QApplication.
    QtApplication = QApplication
