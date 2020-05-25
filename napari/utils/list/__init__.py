from ._base import List
from ._config import USE_PERFMON
from ._model import ListModel
from ._multi import MultiIndexList
from ._timers import PerfTimers
from ._typed import TypedList


if USE_PERFMON:

    def add_event(event: PerfEvent):
        """Add a PerfEvent.

        Parameters
        ----------
        event: PerfEvent
            Add this event.
        """
        PerfTimers.add_event(event)


else:

    def add_event(event: PerfEvent):
        """Disabled routine.

        Parameters
        ----------
        event: PerfEvent
            Ignored.

        Raises
        ------
        NotImplementedError
            Always raises this!
        """
        # No one should be calling this if the env var is not set.
        # All 3 of these should be disabled:
        #
        # 1) Qt Events timers.
        # 2) Our perf_timer context object.
        # 3) Our perf_func decorator.
        #
        # Anyone else should disable themselves based on the env var.
        raise NotImplementedError("Timers are not enabled")
