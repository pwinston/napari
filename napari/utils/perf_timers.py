"""PerfTimers class for monitoring performance.
"""
import os
from typing import Optional

from .perf_utils import TimingEvent
from .simple_stat import SimpleStat
from .tracing import ChromeTracingFile

# For now all performance timing is 100% disabled unless the
# environment variable is set. Long term we will probably
# leave some timing on at all times.
USE_PERFMON = os.getenv("NAPARI_PERFMON", "0") != "0"


class PerfTimers:
    """Timers for performance monitoring.

    For each TimingEvent recorded we do two things:
    1) Update our self.timers dictionary (always).
    2) Write to a trace file (optional).

    Anyone can record a timing event, but these are 3 common ways:
    1) Our custom QtApplication times Qt Events.
    2) Our perf_timer context object times blocks of code.
    3) Our perf_func decorator can time functions.

    The QtPerformance Widget goes through our self.timers looking for long events
    and prints them to a log window. Then it clears the timers.

    Attributes
    ----------
    timers : dict
        Maps a timer name to a SimpleStat object.
    trace_file : ChromeTracingfile, optional
        The tracing file we are writing to if any.

    Notes
    -----
    Chrome deduces nesting based on the start and end times of each timer. The
    chrome://tracing GUI shows the nesting as stacks of colored rectangles.

    However our self.timers dictionary and thus our QtPerformance window do not
    currently understand nesting. So if they say two timers each took 1ms, you
    can't tell if they overlapped or not.

    Despites this limitation when the QtPerformance widget report slow timers it
    still gives you a good idea. And then you can use chrome://tracing GUI to
    see the full story.
    """

    def __init__(self):
        """Create PerfTimers.
        """
        # Maps a timer name to one SimleStat object.
        self.timers = {}

        # Menu item "Debug -> Record Trace File..." starts a trace.
        self.trace_file = None

    def record_trace_file(
        self, path: str, duration_seconds: Optional[int] = None
    ) -> None:
        """Record a trace file to disk.

        Parameters
        ----------
        path : str
            Write the trace to this path.
        duration_seconds: int, optional
            Record for this many seconds then stop.
        """
        self.trace_file = ChromeTracingFile(path, duration_seconds)

    def add_event(self, event: TimingEvent):
        """Add one timing event.

        Parameters
        ----------
        event : TimingEvent
            Add this event.
        """
        # Write if actively tracing.
        if self.trace_file is not None:
            self.trace_file.write_event(event)

            if self.trace_file.done:
                self.trace_file = None

        # Update self.timers (in milliseconds).
        name = event.name
        duration_ms = event.duration_ms
        if name in self.timers:
            self.timers[name].add(duration_ms)
        else:
            self.timers[name] = SimpleStat(duration_ms)

    def clear(self):
        """Clear all timers.
        """
        # After the GUI displays timing information it can clear the timers
        # so that we start accumulating fresh information.
        self.timers.clear()


if USE_PERFMON:
    # One global instance so far.
    TIMERS = PerfTimers()

    def add_event(event):
        TIMERS.add_event(event)


else:
    # Nothing should be using the class at all.
    del PerfTimers
