"""Commands class for IPython console.
"""
from ..utils.text_table import TextTable


class ConsoleCommands:
    """Command object for interactive use in the console.

    Usage:
        viewer.cmd.help
        viewer.cmd.list
        etc.
    """

    def __init__(self, layerlist):
        self.layers = layerlist

    @property
    def help(self):
        """Print the commands we understand."""
        print("Commands:")
        print("cmd.help")
        print("cmd.list")

    @property
    def list(self):
        """Print the current list of layers."""
        table = TextTable(
            ["ID", "TYPE", "MULTI", "SHAPE", "NAME"], [3, 8, 7, 0, 20]
        )

        for i, layer in enumerate(self.layers):
            layer_type = type(layer).__name__
            data_shape = layer.data.shape
            table.add_row(
                [i, layer_type, layer.multiscale, data_shape, layer.name]
            )
        table.print()
