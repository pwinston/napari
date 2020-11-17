"""Functions to downsample images and create multi-scale images.

This file is early/placeholder. In normal useage we might never create
tiles, because downsampling images is very slow. But for debugging and
development we do make tiles on the fly, for test images and other reasons.

Long term we might possible make tiles in the background at some point. So
as you browse a large image that doesn't have tiles, they are created in
the background. But that's pretty speculative and far out.
"""
import time
from typing import List, Optional

import dask
import dask.array as da
import numpy as np
from scipy import ndimage as ndi

from ....types import ArrayLike
from .octree_util import NormalNoise, TileArray


def _get_tile(tiles: TileArray, row, col):
    try:
        return tiles[row][col]
    except IndexError:
        return None


def _none(items):
    return all(x is None for x in items)


def _one_tile(tiles: TileArray) -> bool:
    return len(tiles) == 1 and len(tiles[0]) == 1


def _add_delay(array, delay_ms: NormalNoise):
    """Add a random delay when this array is first accessed.

    Parameters
    ----------
    noise : NormalNoise
        The amount of the random delay in milliseconds.
    """

    @dask.delayed
    def delayed(array):
        sleep_ms = max(0, np.random.normal(delay_ms.mean, delay_ms.std_dev))
        time.sleep(sleep_ms / 1000)
        return array

    return da.from_delayed(delayed(array), array.shape, array.dtype)


def create_tiles(
    array: np.ndarray, tile_size: int, delay_ms: Optional[NormalNoise] = None
) -> np.ndarray:
    """
    Return an NxM array of (tile_size, tile_size) ndarrays except the edge
    tiles might be smaller if the array did not divide evenly.

    TODO_OCTREE: Could we use slices_from_chunks() from dask.array.core to
    do this without loops, faster? Right now this is just used for
    testing/development, but if we do this in production, maybe upgrade it.

    Parameters
    ----------
    array : np.ndarray
        The array to create tiles out of.
    tiles_size : int
        Edge length of the square tiles.
    """
    # Array is either ndim==2 (grayscale) or ndim==3 (RGB).
    if array.ndim < 2 or array.ndim > 3:
        raise ValueError(f"Unexpected array dimension {array.ndim}")
    rows, cols = array.shape[:2]

    tiles = []

    print(f"create_tiles array={array.shape} tile_size={tile_size}")

    row = 0
    while row < rows:
        row_tiles = []
        col = 0
        while col < cols:
            array_slice = (
                slice(row, row + tile_size),
                slice(col, col + tile_size),
            )
            if array.ndim == 3:
                array_slice += (slice(None),)  # Add the colors.

            tile = array[array_slice]

            if not delay_ms.is_zero:
                tile = _add_delay(tile, delay_ms)

            row_tiles.append(tile)
            col += tile_size
        tiles.append(row_tiles)
        row += tile_size

    return tiles


def _combine_tiles(*tiles: np.ndarray) -> np.ndarray:
    """Combine between one and four tiles into a single tile.

    The single resulting tile is not downsampled, so its size is the size
    of the four tiles combined together. However, typically the result will
    be downsampled by half in the following steps.

    Parameters
    ----------
    tiles
        The 4 child tiles, some might be None.
    """
    if len(tiles) != 4:
        raise ValueError("Must have 4 values")

    if tiles[0] is None:
        raise ValueError("Position 0 cannot be None")

    # The layout of the children is:
    # 0 1
    # 2 3
    if _none(tiles[1:4]):
        # We only have one tile:
        # 0 X
        # X X
        return tiles[0]
    if _none(tiles[2:4]):
        # We only have the top two tiles:
        # 0 1
        # X X
        return np.hstack(tiles[0:2])
    if _none((tiles[1], tiles[3])):
        # We only have the left two tiles:
        # 0 X
        # 2 X
        return np.vstack((tiles[0], tiles[2]))

    # We have all four tiles:
    # 0 1
    # 2 3
    row1 = np.hstack(tiles[0:2])
    row2 = np.hstack(tiles[2:4])
    return np.vstack((row1, row2))


def _create_downsampled_tile(*tiles: np.ndarray) -> np.ndarray:
    """Create one parent tile from four child tiles.

    Parameters
    ----------
    tiles
        The 4 child tiles, some could be None.
    """
    # Combine 1-4 tiles together.
    combined_tile = _combine_tiles(*tiles)

    # Down sample by half.
    return ndi.zoom(
        combined_tile, [0.5, 0.5, 1], mode='nearest', prefilter=True, order=1
    )


def _create_coarser_level(tiles: TileArray) -> TileArray:
    """Return a level that is one level coarser.

    Combine each 2x2 group of tiles into one downsampled tile. This is slow
    so currently it's only used for testing. Most multi-scale data will
    be provided pre-downsampled into multiple levels.

    Parameters
    ----------
    tiles : TileArray
        The tiles to combine.

    Returns
    -------
    TileArray
        The coarser level of tiles.
    """

    level = []

    for row in range(0, len(tiles), 2):
        row_tiles = []
        for col in range(0, len(tiles[row]), 2):
            # The layout of the children is:
            # 0 1
            # 2 3
            group = (
                _get_tile(tiles, row, col),
                _get_tile(tiles, row, col + 1),
                _get_tile(tiles, row + 1, col),
                _get_tile(tiles, row + 1, col + 1),
            )
            tile = _create_downsampled_tile(*group)
            row_tiles.append(tile)
        level.append(row_tiles)

    return level


def create_multi_scale_from_image(
    image: np.ndarray, tile_size: int
) -> List[np.ndarray]:
    """Turn an image into a multi-scale image with levels.

    The given image is level 0, the full resolution image. Each additional
    level is downsized by half. The final root level is small enough to
    fit in one tile.

    Parameters
    ----------
    image : np.darray
        The full image to create levels from.
    """
    levels = [image]

    # Repeat until we have level that will fit in a single tile, that will
    # be come the root/highest level.
    while max(levels[-1].shape) > tile_size:
        next_level = ndi.zoom(
            levels[-1], [0.5, 0.5, 1], mode='nearest', prefilter=True, order=1
        )
        levels.append(next_level)

    return levels


def create_levels_from_multiscale_data(
    data: List[ArrayLike], tile_size: int, delay_ms: NormalNoise
):
    """Create octree levels from multiscale data.

    The data is already a list of ArrayLike levels, each own downsampled
    by half. We are just creating the TileArray list of lists format
    that the octree code expects today.

    We'll almost certainly replace this lists of lists format with Dask or
    some nicer chunked format. But this is what we've done since day one
    until we upgrade it.
    """

    return [
        create_tiles(level_data, tile_size, delay_ms) for level_data in data
    ]
