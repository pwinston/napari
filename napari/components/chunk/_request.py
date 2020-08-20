"""ChunkRequest is used to ask the ChunkLoader to load chunks.
"""
import logging
from typing import List, Tuple, Union

import numpy as np

from ...types import ArrayLike, Dict

LOGGER = logging.getLogger("napari.async")

# We convert slices to tuple for hashing.
SliceTuple = Tuple[int, int, int]

# The type of Layer.data
LayerData = Union[ArrayLike, List[ArrayLike]]


class ChunkKey:
    """The key which a ChunkRequest will load.

    Parameters
    ----------
    layer : Layer
        The layer to load data for.
    indices : ?
        The indices to load from the layer
    """

    def __init__(self, layer, indices):
        self.layer_id = id(layer)
        self.data_level = layer._data_level

        # Slice objects are not hashable, so turn them into tuples.
        self.indices = tuple(_index_to_tuple(x) for x in indices)

        # All together as one tuple for easy comparison.
        self.key = (self.layer_id, self.data_level, self.indices)

    def __str__(self):
        return (
            f"layer_id={self.layer_id} data_id={self.data_id} "
            f"data_level={self.data_level} indices={self.indices}"
        )

    def __eq__(self, other):
        return self.key == other.key


class ChunkRequest:
    """A request asking the ChunkLoader to load one or more arrays.

    Parameters
    ----------
    key : ChunkKey
        The key of the request.
    chunks : Dict[str, ArrayLike]
        The chunk arrays we need to load.

    Attributes
    ----------
    key : ChunkKey
        The key of the request.
    chunks : Dict[str, ArrayLike]
        The chunk arrays we need to load.
    load_seconds : float
        Delay for this long during the load portion, for testing.
    """

    def __init__(self, key: ChunkKey, chunks: Dict[str, ArrayLike]):
        # Make sure chunks is str->array as expected.
        for chunk_key, array in chunks.items():
            assert isinstance(chunk_key, str)
            assert array is not None

        self.key = key
        self.chunks = chunks

        # No delay by default, ChunkLoader.load_chunk() will set this if desired.
        self.load_seconds = 0

    def load_chunks(self):
        """Load all of our chunks now in this thread."""
        for key, array in self.chunks.items():
            loaded_array = np.asarray(array)
            self.chunks[key] = loaded_array

    def transpose_chunks(self, order):
        """Transpose all our chunks.

        Parameters
        ----------
        order
            Transpose the chunks with this order.
        """
        for key, array in self.chunks.items():
            self.chunks[key] = array.transpose(order)

    @property
    def image(self):
        """The image chunk if we have one or None.
        """
        return self.chunks.get('image')

    @property
    def thumbnail_source(self):
        """The chunk to use as the thumbnail_source or None.
        """
        try:
            return self.chunks['thumbnail_source']
        except KeyError:
            # For single-scale we use the image as the thumbnail_source.
            return self.chunks.get('image')

    def is_compatible(self, layer: LayerData) -> bool:
        """Return True if the given data is compatible with this request.

        Parameters
        ----------
        data : LayerData
            Compare this data to the data_id in the request.
        """
        return True  # stub for now


def _index_to_tuple(index: Union[int, slice]) -> Union[int, SliceTuple]:
    """Get hashable object for the given index.

    Slice is not hashable so we convert slices to tuples.

    Parameters
    ----------
    index
        Integer index or a slice.

    Returns
    -------
    Union[int, SliceTuple]
        Hashable object that can be used for the index.
    """
    if isinstance(index, slice):
        return (index.start, index.stop, index.step)
    return index