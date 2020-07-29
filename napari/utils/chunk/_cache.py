"""ChunkCache stores loaded chunks.
"""
import logging
from typing import Dict, Optional

import numpy as np
from cachetools import LRUCache

from ._request import ChunkRequest

LOGGER = logging.getLogger("ChunkLoader")

# ChunkCache size as a fraction of total RAM, needs to be configurable
# and even dynamically configurable. Keep it small for now until we
# figure out how ChunkCache will work with the Dask cache.
CACHE_MEM_FRACTION = 0.1

# Once a ChunkRequest has been loaded its ChunkRequest.chunks attribute
# is a ChunkArrays dict, it's some number of named arrays.
ChunkArrays = Dict[str, np.ndarray]


def _get_cache_size_bytes(mem_fraction: float) -> int:
    """Return number of bytes the cache should use at most.

    Parameters
    ----------
    mem_fraction : float
        Size the cache to be this fraction of RAM, for example 0.5.

    Returns
    -------
    int
        Number of bytes the cache should limit itself to.
    """
    import psutil

    return psutil.virtual_memory().total * mem_fraction


def _getsizeof_chunks(chunks: ChunkArrays) -> int:
    """We pass this to the cachetoosl LRUCache.

    Parameters
    ----------
    chunks : ChunkArrays
        The arrays stored in one cache entry.

    Returns
    -------
    int
        How many bytes these arrays take up in memory.
    """
    return sum(array.nbytes for array in chunks.values())


class ChunkCache:
    """Cache of previously loaded chunks.

    Uses a cachetools LRUCache to implement a least recently used cache
    that will grow in memory usage up to some limit, then it will free
    the least recently entries so total usage does not exceed that limit.

    TODO_ASYNC:

    1) Should this cache be off by default? For data that is dynamically
    produced as a result of computation, we might want caching off since
    the results could be different with each call.

    2) Can we use the Dask cache instead of our own? It's hard to size
    two caches, they can't both be 0.5 * RAM.

    Attributes
    ----------
    chunks : LRUCache
        The cache of chunks.
    """

    def __init__(self):
        nbytes = _get_cache_size_bytes(CACHE_MEM_FRACTION)
        self.chunks = LRUCache(maxsize=nbytes, getsizeof=_getsizeof_chunks)

    def add_chunk(self, request: ChunkRequest) -> None:
        """Add this chunk to the cache.

        Parameters
        ----------
        request : ChunkRequest
            Add the data in this request to the cache.
        """
        LOGGER.info("ChunkCache.add_chunk: %s", request.key)
        self.chunks[request.key] = request.chunks

    def get_chunk(self, request: ChunkRequest) -> Optional[ChunkArrays]:
        """Get the cached data for this chunk request.

        Parameters
        ----------
        request : ChunkRequest
            Lookup cached data for this request.

        Returns
        -------
        ChunkArrays, optional
            The cached data or None of it was not found in the cache.
        """
        LOGGER.info("ChunkCache.get_chunk: %s", request.key)
        return self.chunks.get(request.key)
