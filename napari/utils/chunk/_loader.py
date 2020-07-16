"""ChunkLoader and related classes.

There is one global chunk_loader instance to handle async loading for any
and all Viewer instances that are running. There are two main reasons we
just have one ChunkLoader and not one per Viewer:

1. We size the ChunkCache as a fraction of RAM, so having more than one
   would use too much RAM.

2. We (will) size the thread pool for optimal performance, and having
   multiple pools would result in more threads than we want.

The ChunkLoader is a shared resource like the network or the filesystem.
"""
from collections import defaultdict
from contextlib import contextmanager
from concurrent import futures
import ctypes
import logging
import os
import time
from typing import Dict, List, Optional
import weakref

from cachetools import LRUCache
import numpy as np

from ._request import ChunkRequest
from ...types import ArrayLike
from ...utils.event import EmitterGroup

LOGGER = logging.getLogger("ChunkLoader")

# ChunkCache size as a fraction of total RAM.
CACHE_MEM_FRACTION = 0.1

NUM_WORKERS = int(os.getenv("NAPARI_CHUNK_WORKERS", "6"))


def _hold_gil(seconds: float):
    """Hold the GIL for some number of seconds.

    This is used for debugging and performance testing only.
    """
    usec = seconds * 1000000
    _libc_name = ctypes.util.find_library("c")
    if _libc_name is None:
        raise RuntimeError("Cannot find libc")
    libc_py = ctypes.PyDLL(_libc_name)
    libc_py.usleep(usec)


def _log_to_file(path):
    """Write ChunkLoader log message to the own file."""
    path = os.getenv("NAPARI_CHUNK_LOG")
    if path is not None:
        fh = logging.FileHandler(path)
        LOGGER.addHandler(fh)
        LOGGER.setLevel(logging.INFO)


# Always on for now. ASYNC_TODO: command line option for this?
_log_to_file('chunk_loader.log')


def _get_synchronous_default() -> bool:
    """
    Return True if ChunkManager should load data synchronously.

    Returns
    -------
    bool
        True if loading should be synchronous.
    """
    # Async is off by default for now. Must opt-in with NAPARI_ASYNC_LOAD.
    synchronous_loading = True

    env_var = os.getenv("NAPARI_CHUNK_ASYNC")

    if env_var is not None:
        # Overide the deafult with the env var's setting.
        synchronous_loading = env_var == "0"

    return synchronous_loading


def _chunk_loader_worker(request: ChunkRequest):
    """Worker thread or process that loads the array.

    """
    # Note what worker we are.
    request.pid = os.getpid()

    # This delay is hopefully temporary, but it avoids some nasty
    # problems with the slider timer firing *prior* to the mouse release,
    # even though it was a single click lasting < 100ms.
    if request.delay_seconds > 0:
        time.sleep(request.delay_seconds)

    # This np.asarray() call might lead to IO or computation via dask
    # or similar means which is why we are doing it in a worker, so
    # that it does not block the GUI thread.
    request.array = np.asarray(request.array)
    return request


def _get_cache_size_bytes(mem_fraction):
    import psutil

    # Sizing approach borrowed from our create_dask_cache()
    return psutil.virtual_memory().total * mem_fraction


def _getsizeof_chunk(array: np.ndarray):
    return array.nbytes


class ChunkCache:
    """Cache of previously loaded chunks.
    """

    def __init__(self):
        nbytes = _get_cache_size_bytes(CACHE_MEM_FRACTION)
        self.chunks = LRUCache(maxsize=nbytes, getsizeof=_getsizeof_chunk)

    def add_chunk(self, request: ChunkRequest) -> None:
        """Add this chunk to the cache.

        Parameters
        ----------
        request : ChunkRequest
            Add the data in this request to the cache.
        """
        LOGGER.info("ChunkCache.add_chunk: %s", request.key)
        self.chunks[request.key] = request.array

    def get_chunk(self, request: ChunkRequest) -> Optional[ArrayLike]:
        """Get the cached data for this chunk request.

        TODO_ASYNC: assumes there's just one layer....
        """
        LOGGER.info("ChunkCache.get_chunk: %s", request.key)
        return self.chunks.get(request.key)


class ChunkLoader:
    """Load chunks for rendering.

    Operates in synchronous or asynchronous modes depeneding on
    self.synchronous.

    Attributes
    ----------
    synchronous : bool
        If True the ChunkLoader is essentially disabled, loads are done
        immediately and in the GUI thread. If False loads are done
        asynchronously in a worker thread.
    """

    def __init__(self):
        self.synchronous = _get_synchronous_default()

        LOGGER.info("ChunkLoader.__init__ synchronous=%d", self.synchronous)
        self.executor = futures.ProcessPoolExecutor(max_workers=NUM_WORKERS)

        # Maps data_id to futures for that layer.
        self.futures: Dict[int, List[futures.Future]] = defaultdict(list)
        self.cache = ChunkCache()

        # We emit only one event:
        #     chunk_loaded - a chunk was loaded
        self.events = EmitterGroup(
            source=self, auto_connect=True, chunk_loaded=None
        )

        # Maps layer_id to weakref of a Layer. ChunkRequest cannot hold a
        # layer reference or even a weakref because if using worker
        # processes those cannot be pickled. So ChunkRequest just holds
        # a layer_id that we can map back to a weakref.
        self.layer_map = {}

    def create_request(self, layer, indices, array: ArrayLike):
        """Create a ChunkRequest for submission to load_chunk.
        """
        # Update the layer_id to weakref mapping.
        layer_id = id(layer)
        self.layer_map[layer_id] = weakref.ref(layer)

        # Return the new request.
        return ChunkRequest(layer, indices, array)

    def _asarray(self, array):
        """Broken out for perfmon timing."""
        return np.asarray(array)

    def load_chunk(self, request: ChunkRequest) -> Optional[ChunkRequest]:
        """Load the array in the given ChunkRequest.

        If ChunkLoader is synchronous the load is performed immediately in
        the GUI thread and the satisfied request is returned.

        Otherwise an asynchronous load is requested and None is returned.
        The load will be performed in a worker thread and later
        Layer.chunk_loaded() will be called in the GUI thread with the
        satisfied result.

        Parameters
        ----------
        request : ChunkRequest
            Contains the array to load from and related info.

        ChunkRequest, optional
            The satisfied ChunkRequest or None indicating an async load.
        """
        # TODO_ASYNC: There's no point using threading for ndarray since
        # they are already raw data in memory, right?
        in_memory = isinstance(request.array, np.ndarray)

        if self.synchronous or in_memory:
            LOGGER.info("[sync] ChunkLoader.load_chunk")

            # Load it immediately right here in the GUI thread.
            request.array = self._asarray(request.array)
            return request

        # TODO_ASYNC: if we don't do this the slider gets timers events
        # as if it were held down too long, and the MouseRelease event
        # gets pushed way out. Need a real fix for this.
        request.delay_seconds = 0.1

        # This will be synchronous if it's a cache hit. Otherwise it will
        # initiate an asynchronous load and sometime later Layer.load_chunk
        # will be called with the loaded chunk.
        return self._load_async(request)

    def _load_async(self, request: ChunkRequest) -> None:
        """Initiate an asynchronous load of the given request.

        Parameters
        ----------
        request : ChunkRequest
            Contains the array to load from and related info.
        """
        LOGGER.info("[async] ChunkLoader._load_async: %s", request.key)

        # Clear any existing futures for this specific data_id. We only
        # support single-scale so there can only be one load in progress
        # per layer.
        self._clear_pending(request.data_id)

        # Check the cache first.
        array = self.cache.get_chunk(request)

        if array is not None:
            LOGGER.info(
                "[async] ChunkLoader._load_async: cache hit %s", request.key
            )
            request.array = array
            return request

        LOGGER.info(
            "[async] ChunkLoader.load_chunk: cache miss %s", request.key
        )

        request.start()

        future = self.executor.submit(_chunk_loader_worker, request)
        future.add_done_callback(self._done)

        # Future is in progress for this layer.
        self.futures[request.data_id].append(future)

        # Async load was started, nothing is available yet.
        return None

    def _clear_pending(self, data_id: int) -> None:
        """Clear any pending requests for this data_id.

        We can't clear in-progress requests that are already running in the
        worker. This is too bad since subsequent requests might have to
        wait behind requests whose results we don't care about. Terminating
        threads is not kosher, terminating processes is probably too
        heavyweight.

        Long term we could potentially give users a way to create
        "cancellable" tasks that perform better than the default opaque
        tasks that we cannot cancel.
        """
        future_list = self.futures[data_id]

        # Try to cancel them all, but cancel() will return False if the
        # task already started running.
        num_before = len(future_list)
        future_list[:] = [x for x in future_list if x.cancel()]
        num_after = len(future_list)
        num_cleared = num_before - num_after

        if num_before == 0:
            LOGGER.info("[async] ChunkLoader.clear_pending: empty")
        else:
            LOGGER.info(
                "[async] ChunkLoader.clear_pending: %d of %d cleared -> %d remain",
                num_cleared,
                num_before,
                num_after,
            )

    def _done(self, future: futures.Future) -> None:
        """Called when a future finished with success or was cancelled.

        Notes
        -----
        This method may be called in the worker thread. The documentation
        very intentionally does not specify which thread the callback will
        be called in, only that it will be called in the same process. On
        MacOS it seems to always be called in the worker thread with a
        thread pool.
        """
        try:
            request = future.result()
        except futures.CancelledError:
            LOGGER.info("[async] ChunkLoader._done: cancelled")
            return

        # Mark the end time.
        request.end()

        LOGGER.info("[async] ChunkLoader._done: %s", request.key)

        # Do this from worker thread for now. It's safe for now.
        # TODO_ASYNC: Ultimately we might want to this to happen from the
        # GUI thread so all cache access is from the same thread.
        self.cache.add_chunk(request)

        layer = self._get_layer_for_request(request)

        # layer_id was not found weakref failed to resolve.
        if layer is None:
            LOGGER.info(
                "[async] ChunkLoader._done: layer was deleted %d",
                request.layer_id,
            )
            return

        # Signal the chunk was loaded. QtChunkReceiver listens for this
        # and will forward the chunk to the layer in the GUI thread.
        self.events.chunk_loaded(layer=layer, request=request)

    def _get_layer_for_request(self, request: ChunkRequest):
        """Return Layer associated with this request or None.
        """
        layer_id = request.layer_id

        try:
            layer_ref = self.layer_map[layer_id]
        except KeyError:
            LOGGER.warn("[async] ChunkLoader._done: no layer_id %d", layer_id)
            return None

        # Could return None if Layer was deleted.
        return layer_ref()


@contextmanager
def synchronous_loading(enabled):
    """Context object to temporarily disable async loading.

    with synchronous_loading(True):
        layer = Image(data)
        ... use layer ...
    """
    previous = chunk_loader.synchronous
    chunk_loader.synchronous = enabled
    yield
    chunk_loader.synchronous = previous


# Global instance
chunk_loader = ChunkLoader()