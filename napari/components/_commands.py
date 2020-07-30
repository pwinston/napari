"""Commands class for IPython console.
"""
from ..utils.text_table import TextTable, red

HELP_STR = f"""
{red("Available Commands:")}
cmd.help
cmd.list
cmd.inspect(layer_id)
"""


class ListLayersTable:
    """Table showing the layers and their names, types and shapes.

    """

    def __init__(self, layers):
        self.layers = layers
        self.table = TextTable(["ID", "NAME", "TYPE", "SHAPE"])
        for i, layer in enumerate(self.layers):
            self._add_row(i, layer)

    def _get_shape_str(self, data):
        """Get shape string for the data.

        For example:
            (10, 100, 100)
            (10, 10000, 10000) (5 levels)
            NONE
        """
        if isinstance(data, list):
            if len(data) == 0:
                return "NONE"  # e.g. Shape layer
            else:
                # Multi-scale
                return f"{data[0].shape} ({len(data)} levels)"  # Multi-scale
        else:
            return str(data.shape)

    def _add_row(self, i, layer):
        """Add one row to the layer list table."""
        layer_type = type(layer).__name__
        shape_str = self._get_shape_str(layer.data)
        self.table.add_row([i, layer.name, layer_type, shape_str])

    def print(self):
        """Print the whole table."""
        self.table.print()


class InspectLayerTable:
    """Table showing the levels in a single layer.

    """

    def __init__(self, layer_id, layer):
        self.layer_id = layer_id
        self.layer = layer
        self.table = TextTable(["LEVEL", "SHAPE"])
        data = layer.data
        if isinstance(data, list):
            for i, level in enumerate(data):
                shape_str = level.shape if level.shape else "NONE"
                self.table.add_row([i, shape_str])

    def print(self):
        """Print the whole table."""

        self.table.print()


class ConsoleCommands:
    """Command object for interactive use in the console.

    Usage:
        viewer.cmd.help
        viewer.cmd.list
        etc.
    """

    def __init__(self, layerlist):
        self.layers = layerlist

    def __repr__(self):
        return HELP_STR

    @property
    def help(self):
        print(HELP_STR)

    @property
    def list(self):
        """Print the current list of layers."""
        table = ListLayersTable(self.layers)
        table.print()

    def inspect(self, layer_id):
        """Inspect a single layer"""
        try:
            layer = self.layers[layer_id]
        except KeyError:
            print(f"Invalid layer index: {layer_id}")
            return

        num_levels = len(layer.data)
        header = f"ID: {layer_id} {layer.name} has {num_levels} levels"
        print(red(header))
        if num_levels > 0:
            InspectLayerTable(layer_id, layer).print()
