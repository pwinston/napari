"""LayerInfo class.
"""
import logging
import weakref

import dask.array as da

from ._request import ChunkRequest
from ._utils import StatWindow

LOGGER = logging.getLogger("ChunkLoader")


def _get_type_str(data) -> str:
    """Get human readable name for the data's type.

    Returns
    -------
    str
        A string like "ndarray" or "dask".
    """
    data_type = type(data)

    if data_type == list:
        if len(data) == 0:
            return "EMPTY"
        else:
            # Recursively get the type string of the zeroth level.
            return _get_type_str(data[0])

    if data_type == da.Array:
        # Special case this because otherwise data_type.__name__
        # below would just return "Array".
        return "dask"

    # For class numpy.ndarray this returns "ndarray"
    return data_type.__name__


class LayerInfo:
    """Information about one layer the ChunkLoader is tracking.

    Parameters
    ----------
    layer : Layer
        The layer we are loading chunks for.
    """

    # Window size for timing statistics. We use a simple average over the
    # window. This is better than the just "last load time" because it
    # won't jump around from one fluke. But we could do something much
    # fancier in the future with filtering.
    WINDOW_SIZE = 10

    def __init__(self, layer):
        self.layer_id: int = id(layer)
        self.layer_ref: weakref.ReferenceType = weakref.ref(layer)
        self.data_type: str = _get_type_str(layer.data)

        self.num_loads: int = 0
        self.num_chunks: int = 0
        self.num_bytes: int = 0

        # Keep running average of load times.
        self.load_time_ms: StatWindow = StatWindow(self.WINDOW_SIZE)

    def get_layer(self):
        """Resolve our weakref to get the layer, log if not found.

        Returns
        -------
        layer : Layer
            The layer for this ChunkRequest.
        """
        layer = self.layer_ref()
        if layer is None:
            LOGGER.info(
                "LayerInfo.get_layer: layer %d was deleted", self.layer_id
            )
        return layer

    def load_finished(self, request: ChunkRequest) -> None:
        """This ChunkRequest was satisfied, record stats.

        Parameters
        ----------
        request : ChunkRequest
            Record stats related to loading these chunks.
        """
        # Record the number of loads and chunks.
        self.num_loads += 1
        self.num_chunks += request.num_chunks

        # Total bytes loaded.
        self.num_bytes += request.num_bytes

        # Record the load time.
        load_ms = request.timers['load_chunks'].duration_ms
        self.load_time_ms.add(load_ms)
