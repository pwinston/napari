"""Performance Monitoring init.
"""
from ._config import USE_PERFMON
from ._event import PerfEvent
from ._timers import add_event, get_timers, clear_timers, record_trace_file
from ._utils import perf_timer, perf_func
