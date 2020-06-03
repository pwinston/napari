"""Defines QApplicationWithEventTiming for perf mon.

If the environment variable NAPARI_PERFMON is set we monkey patch in the
notify_with_event_timing() method below to replace the stock
QApplication.notify() method.

Our notify method times every Qt Event which powers the debug menu's "Start
Tracing" feature as well as the dockable QtPerformance widget.
"""
from types import MethodType
from qtpy.QtWidgets import QApplication

from ..utils import perf

MONKEY_PATCHED = False


def monkey_patch_event_timing(app: QApplication):
    """
    Replace the application's notify method with one that times event handling.

    Parameters
    ----------
    app : QApplication
        We replace the notify method of this application.

    Notes
    -----
    Qt Event handling is nested. A call to notify() can trigger other calls to
    notify() prior to the first one finishing, even several levels deep.

    The hierarchy of timers is displayed correctly in the chrome://tracing GUI.
    Just seeing the structure of the event handling hierarchy can be very
    informative even apart from the timing numbers.
    """
    original_notify = app.notify

    def notify_with_timing(self, receiver, event):
        """Time the Qt Events as we handle them."""
        print("MONKEY_PATCHED VERSION***********")
        timer_name = _get_timer_name(receiver, event)

        # Time the event while we handle it.
        with perf.perf_timer(timer_name, "qt_event"):
            return original_notify(receiver, event)

    bound_notify = MethodType(notify_with_timing, app)

    # Check if we are already patched first.
    if not hasattr(app, '_napari_event_timing'):
        # Patch and record that we did so we never double patch which would be
        # very confusing and would degrade performance.
        print(
            "Napari: Monkey Patching the QAppliction instance for performance monitoring."
        )
        app.notify = bound_notify
        app._napari_event_timing = True


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
