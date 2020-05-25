"""PerfTraceFile class to write JSON files in the chrome://tracing format.
"""
from typing import Optional
import json
import os
import threading

from .perf_utils import perf_counter_ns
from .perf_event import PerfEvent


class PerfTraceFile:
    """Writes a chrome://tracing formatted JSON file.

    Attributes
    ----------
    zero_ns : int
        perf_counter_ns() time when we started the trace.
    trace_stop_ns : int, optional
        When we should stop the trace, if at all.
    pid : int
        Process ID.
    tid : int
        Thread ID.
    outf : file handle
        JSON file we are writing to.

    Notes
    -----
    There are two chrome://tracing formats:
    1) JSON Array Format
    2) JSON Object Format

    We are using the JSON Array Format right now, the file can be
    cut off at anytime. The other format allows for more options if
    we need them but must be closed properly.

    See the "trace_event format" Google Doc for details:
    https://chromium.googlesource.com/catapult/+/HEAD/tracing/README.md
    """

    def __init__(self, path: str, duration_seconds: Optional[int] = None):
        """Open the tracing file on disk.

        Parameters
        ----------
        path : str
            Write the trace file to this path.
        duration_seconds : int, optional
            If given trace send after this many seconds, otherwise never ends.
        """
        # So the events we write start at t=0.
        self.zero_ns = perf_counter_ns()

        if duration_seconds is not None:
            # Note when we should stop.
            self.trace_stop_ns = duration_seconds * 1e9
        else:
            # Never stop, user exits to stop.
            self.trace_stop_ns = None

        # PID and TID go in every event. We are assuming one process and
        # one thread for now, otherwise we'll have to add these to PerfEvent.
        self.pid = os.getpid()
        self.tid = threading.get_ident()

        # Start writing the file with an open bracket, per JSON Array format.
        self.outf = open(path, "w")
        self.outf.write("[\n")
        self.done = False

    def write_event(self, event: PerfEvent) -> None:
        """Write one perf event.
s
        Parameters
        ----------
        event : PerfEvent
            Event to write.
        """
        # Convert to a zero-based time.
        start_ns = event.start_ns - self.zero_ns

        # Event type "X" denotes a completed event. Meaning we already
        # know the duration. The format wants times in micro-seconds.
        data = {
            "pid": self.pid,
            "name": event.name,
            "cat": event.category,
            "ph": "X",
            "ts": event.start_us,
            "dur": event.duration_us,
        }
        json_str = json.dumps(data)

        # Write comma separated JSON objects.
        self.outf.write(f"{json_str},\n")

        if self.trace_stop_ns is not None:
            if start_ns > self.trace_stop_ns:
                self.outf.close()
                self.done = True
