"""Utilities to support performance monitoring:

1) context manager: perf_timer times a block of code.
2) decorator: perf_func times a function.
"""
import contextlib
import functools
from typing import Optional

from ._compat import perf_counter_ns
from ._config import USE_PERFMON, PYTHON_3_7
from ._event import PerfEvent
from ._timers import add_event


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
    # Timing is disabled so we want null versions of both that have
    # essentially zero runtime overhead.
    def perf_func(name):
        def decorator(func):
            return func

    if PYTHON_3_7:
        perf_timer = contextlib.nullcontext()
    else:

        @contextlib.contextmanager
        def perf_timer(name: str):
            yield
