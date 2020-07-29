"""AsyncConfig to configure asynchronous loading and the ChunkLoader.
"""
import errno
import json
import logging
import os
from pathlib import Path

LOGGER = logging.getLogger("ChunkLoader")

# NAPARI_ASYNC an be used to enable or configure async loading.
# If NAPARI_ASYNC is the path of a JSON file we use that as the config.
ASYNC_ENV_VAR = "NAPARI_ASYNC"

# NAPARI_ASYNC=0 or unset will use these settings:
DEFAULT_SYNC_CONFIG = {"synchronous": True}

# NAPARI_ASYNC=1 will use these settings:
DEFAULT_ASYNC_CONFIG = {
    "synchronous": False,
    "num_workers": 6,
    "log_path": None,
    "use_procesess": False,
    "delay_seconds": 0.1,
    "load_seconds": 0,
}


def _log_to_file(path: str) -> None:
    """Log to the given file path.

    Parameters
    ----------
    path : str
        Log to this file path.
    """
    if path:
        fh = logging.FileHandler(path)
        LOGGER.addHandler(fh)
        LOGGER.setLevel(logging.INFO)


class AsyncConfig:
    """Reads the config file pointed to by NAPARI_ASYNC.

    Parameters
    ----------
    data : dict
        The config settings from the config file or defaults.
    """

    def __init__(self, data: dict):
        self.data = data
        _log_to_file(self.log_path)
        LOGGER.info("AsyncConfig.__init__ config = ")
        LOGGER.info(json.dumps(data, indent=4, sort_keys=True))

    @property
    def synchronous(self) -> bool:
        """True if loads should be done synchronously."""
        return self.data.get("synchronous", True)

    @property
    def num_workers(self) -> int:
        """The number of worker threads or processes to create."""
        return self.data.get("num_workers", 6)

    @property
    def log_path(self) -> str:
        """The file path where the log file should be written."""
        return self.data.get("log_path")

    @property
    def use_processes(self) -> bool:
        """True if we should use processes instead of threads."""
        return self.data.get("use_processes", False)

    @property
    def delay_seconds(self) -> float:
        """The number of seconds to delay before initiating a load.

        The default of 100ms makes sure that we don't spam the workers with
        tons of loads requests while scrolling with the slice slider. The
        data from those loads would just be ignored since we'd no longer
        be on those slices when the load finished, so it would waste
        bandwidth and it might mean no worker is available when we finally
        do stop on a slice we care about.
        """
        return self.data.get("delay_seconds", 0.1)

    @property
    def load_seconds(self) -> float:
        """Add a sleep this many seconds long during load.

        This is only usefull during debugging or development, it can be used
        to simulate a slow internet connection, for example.
        """
        return self.data.get("load_seconds", 0)


def _load_config(config_path: str) -> dict:
    """Load the JSON formatted config file.

    config_path : str
        The file path of the JSON file we should load.
    """

    path = Path(config_path).expanduser()
    if not path.exists():
        # The exception message looks like:
        # "Config file NAPARI_ASYNC=missing-file.json not found"
        raise FileNotFoundError(
            errno.ENOENT,
            f"Config file {ASYNC_ENV_VAR}={path} not found",
            path,
        )

    with path.open() as infile:
        return json.load(infile)


def _get_config_data() -> dict:
    """Return the user's config file data or a default config.
    """
    value = os.getenv(ASYNC_ENV_VAR)

    if value is None or value == "0":
        return DEFAULT_SYNC_CONFIG  # Async is disabled.
    elif value == "1":
        return DEFAULT_ASYNC_CONFIG  # Async is enabled with defaults.
    else:
        return _load_config(value)  # Load the user's config file.


# The global instance
async_config = AsyncConfig(_get_config_data())
