"""Defines our QtApplication.

Our QtApplication is either:
1) QApplication in the normal case.
2) PerfmonApplication if NAPARI_PERFMON environment variable is set.

PerfmonApplication defined below adds timing of every Qt Event.
"""
import os

from qtpy.QtWidgets import QApplication

from ..utils.perf_utils import perf_timer


def _get_timer_name(event: str, receiver: str) -> str:
    """Return a name for this event.

    Parameters
    ----------
    event : str
        The event name.
    receiver : str
        The receiver of the event.

    Returns
    -------
    timer name : str

    Notes
    -----
    If there is no object we return just <event_name>.
    If there is an object we do <event_name>:<object_name>.

    This our own made up format we can revise as needed.
    """
    # For an event.type() like "PySide2.QtCore.QEvent.Type.WindowIconChange"
    # we set event_str to just the final "WindowIconChange" part.
    event_str = str(event.type()).split(".")[-1]

    try:
        object_name = receiver.objectName()
    except AttributeError:
        # During shutdown the call to receiver.objectName() can fail with
        # "missing objectName attribute". Ingore and assume no object name.
        object_name = None

    if object_name:
        return f"{event_str}:{object_name}"

    # Many events have no object.
    return event_str


class PerfmonApplication(QApplication):
    """Extend QApplication to time Qt Events.

    Performance monitoring is a WIP. There are 3 main parts to performance
    monitoring today:
    1) PerfmonApplication: times events, sends times to PerfTimers.
    2) PerfTimers: stores timing data, optionally writes to chrome://tracing.
    3) QtPerformance: dockable widget which displays some PerfTime data.

    Nesting: Note that Qt Event handling is nested. A call to notify() can
    trigger other calls to notify() prior to the first one finishing, and so one
    several levels deep. This hierarchy of timers is visible in
    chrome://tracing.
    """

    def notify(self, receiver, event):
        """Time events while we handle them."""
        print("RECEIVER", type(receiver))
        print("EVENT", type(event))
        # Must access event/receiver before calling notify().
        timer_name = _get_timer_name(receiver, event)

        # Time the event while we handle it.
        with perf_timer(timer_name, "qt_event"):
            return QApplication.notify(self, receiver, event)


USE_PERFMON = os.getenv("NAPARI_PERFMON", "0") != "0"

if USE_PERFMON:
    # Use our performance monitoring version.
    QtApplication = PerfmonApplication
else:
    # Use the normal stock QApplication
    QtApplication = QApplication
