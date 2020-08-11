"""ConsoleProcessor class for our IPython console.
"""
from ._loader import LoaderCommands
from ._utils import highlight

HELP_STR = f"""
{highlight("Available Commands:")}
cmd.help
cmd.loader
cmd.loader_config
"""


class CommandProcessor:
    """Command processor designed for interactive use in the IPython console.

    Type "viewer.cmd.help" in Python for valid commands.
    """

    def __init__(self, layerlist):
        self.loader_commands = LoaderCommands(layerlist)

    def __repr__(self):
        return HELP_STR

    @property
    def help(self):
        print(HELP_STR)

    @property
    def loader(self):
        """Print a table with per-layer ChunkLoader information."""
        return self.loader_commands.loader

    @property
    def loader_config(self):
        """Print a table with ChunkLoader config."""
        return self.loader_commands.loader_config

    def loads(self, layer_index):
        """Print a table with ChunkLoader config."""
        return self.loader_commands.loads(layer_index)

    def set_sync(self, layer_index):
        return self.loader_commands.set_sync(layer_index)

    def set_async(self, layer_index):
        return self.loader_commands.set_async(layer_index)

    def set_default(self, layer_index):
        return self.loader_commands.set_default(layer_index)
