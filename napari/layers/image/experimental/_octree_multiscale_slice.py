"""OctreeMultiscaleSlice class.

For viewing one slice of a multiscale image using an octree.
"""
import logging
from typing import Callable, List, Optional

import numpy as np

from ....components.experimental.chunk import ChunkRequest
from ....types import ArrayLike
from .._image_view import ImageView
from .octree import Octree
from .octree_intersection import OctreeIntersection
from .octree_level import OctreeLevelInfo
from .octree_util import ImageConfig, OctreeChunk, OctreeLocation

LOGGER = logging.getLogger("napari.async.octree")


class OctreeMultiscaleSlice:
    """View a slice of an multiscale image using an octree."""

    def __init__(
        self,
        data,
        image_config: ImageConfig,
        image_converter: Callable[[ArrayLike], ArrayLike],
    ):
        self.data = data

        self._image_config = image_config

        self._octree = Octree.from_multiscale_data(data, image_config)
        self._octree_level = self._octree.num_levels - 1

        thumbnail_image = np.zeros(
            (64, 64, 3)
        )  # blank until we have a real one
        self.thumbnail: ImageView = ImageView(thumbnail_image, image_converter)

    @property
    def octree_level(self) -> int:
        """The current octree level.

        Return
        ------
        int
            The current octree level.
        """
        return self._octree_level

    @octree_level.setter
    def octree_level(self, level: int) -> None:
        """Set the octree level that the slice is showing.

        This will be ignore if AUTO_LEVEL is one.

        Parameters
        ----------
        level : int
            The new level to display.
        """
        self._octree_level = level

    @property
    def loaded(self) -> bool:
        """Return True if the data has been loaded.

        Because octree multiscale is async, we say we are loaded up front even
        though none of our chunks/tiles might be loaded yet.
        """
        return self.data is not None

    @property
    def octree_level_info(self) -> Optional[OctreeLevelInfo]:
        """Return information about the current octree level.

        Return
        ------
        Optional[OctreeLevelInfo]
            Information about current octree level, if there is one.
        """
        if self._octree is None:
            return None
        return self._octree.levels[self._octree_level].info

    def get_intersection(self, corners_2d, auto_level: bool):
        """Return the intersection with the octree."""
        if self._octree is None:
            return None
        level_index = self._get_octree_level(corners_2d, auto_level)
        level = self._octree.levels[level_index]
        return OctreeIntersection(level, corners_2d)

    def _get_octree_level(self, corners_2d, auto_level):
        if not auto_level:
            return self._octree_level

        # Find the right level automatically.
        width = corners_2d[1][1] - corners_2d[0][1]
        tile_size = self._octree.image_config.tile_size
        num_tiles = width / tile_size

        # TODO_OCTREE: compute from canvas dimensions instead
        max_tiles = 5

        # Slow way to start, redo this O(1).
        for i, level in enumerate(self._octree.levels):
            if (num_tiles / level.info.scale) < max_tiles:
                return i

        return self._octree.num_levels - 1

    def get_visible_chunks(self, corners_2d, auto_level) -> List[OctreeChunk]:
        """Return the chunks currently in view.

        Return
        ------
        List[OctreeChunk]
            The chunks inside this intersection.
        """
        intersection = self.get_intersection(corners_2d, auto_level)

        if intersection is None:
            return []

        if auto_level:
            # Set current level according to what was automatically selected.
            level_index = intersection.level.info.level_index
            self._octree_level = level_index

        # Return the chunks in this intersection.
        return intersection.get_chunks(id(self))

    def _get_octree_chunk(self, location: OctreeLocation):
        level = self._octree.levels[location.level_index]
        return level.tiles[location.row][location.col]

    def on_chunk_loaded(self, request: ChunkRequest) -> None:
        """An asynchronous ChunkRequest was loaded.

        Override Image.on_chunk_loaded() fully.

        Parameters
        ----------
        request : ChunkRequest
            This request was loaded.
        """
        location = request.key.location
        if location.slice_id != id(self):
            # There was probably a load in progress when the slice was changed.
            # The original load finished, but we are now showing a new slice.
            # Don't consider it error, just ignore the chunk.
            LOGGER.debug("on_chunk_loaded: wrong slice_id: %s", location)
            return False  # Do not load.

        octree_chunk = self._get_octree_chunk(location)
        if not isinstance(octree_chunk, OctreeChunk):
            # This location in the octree is not a OctreeChunk. That's unexpected,
            # becauase locations are turned into OctreeChunk's when a load
            # is initiated. So this is an error, but log it and keep going.
            LOGGER.error(
                "on_chunk_loaded: missing OctreeChunk: %s", octree_chunk
            )
            return False  # Do not load.

        # Looks good, we are loading this chunk.
        LOGGER.debug("on_chunk_loaded: loading %s", octree_chunk)

        # Get the data from the request.
        incoming_data = request.chunks.get('data')

        # Loaded data should always be an ndarray.
        assert isinstance(incoming_data, np.ndarray)

        # Shove the request's ndarray into the octree's OctreeChunk. This octree
        # chunk now has an ndarray as its data, and it can be rendered.
        octree_chunk.data = incoming_data

        # OctreeChunk should no longer need to be loaded. We can probably
        # remove this check eventually, but for now to be sure.
        assert not self._get_octree_chunk(location).needs_load

        return True  # Chunk was loaded.
