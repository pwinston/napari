"""Utilities to support performance monitoring:

The perf_timer context manager to time blocks of code.
The perf_func decorator to time functions.
Our perf_counter_ns() function.
"""
import contextlib
import functools
import os
import sys
import time
from typing import Optional

from .perf_timers import add_event
from .perf_event import PerfEvent


PYTHON_3_7 = sys.version_info[:2] >= (3, 7)
USE_PERFMON = os.getenv("NAPARI_PERFMON", "0") != "0"


if USE_PERFMON:

    @contextlib.contextmanager
    def perf_timer(name: str, category: Optional[str] = None):
        """Time a block of code.

        Attributes
        ----------
        name : str
            The name of this timer.

        Example
        -------
        with perf_timer("draw"):
            draw_stuff()
        """
        start_ns = perf_counter_ns()
        yield
        end_ns = perf_counter_ns()
        event = PerfEvent(category, name, start_ns, end_ns)
        add_event(event)

    def perf_func(name):
        """Decorator to time a function.

        Example
        -------
        @perf_func("draw")
        def draw(self):
            draw_stuff()
        """

        def decorator(func):
            @functools.wraps(func)
            def time_function(*args, **kwargs):
                with perf_timer(name):
                    return func(*args, **kwargs)

            return time_function


else:
    # Timing is disabled so null versions of both.
    if PYTHON_3_7:
        perf_timer = contextlib.nullcontext()
    else:

        @contextlib.contextmanager
        def perf_timer(name: str):
            yield

    def decorator(func):
        return func


if PYTHON_3_7:
    # Use the real perf_counter_ns
    perf_counter_ns = time.perf_counter_ns
else:

    def perf_counter_ns():
        """Fake version for pre Python 3.7."""
        return int(time.perf_counter() * 1e9)
