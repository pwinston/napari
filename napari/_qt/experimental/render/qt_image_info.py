"""QtImageInfo class.
"""
from qtpy.QtWidgets import QFrame, QLabel, QVBoxLayout

from .qt_labeled_spin_box import LabeledSpinBox


class QtImageInfoLayout(QVBoxLayout):
    """Layout of the image info frame.

    Parameters
    ----------
    layer : Layer
        The layer we are associated with.
    on_new_octree_level
        Call this when the octree level is changed.
    """

    def __init__(self, layer, on_new_octree_level):
        super().__init__()

        # Octree level SpinBox.
        max_level = layer.num_octree_levels - 1
        self.octree_level = LabeledSpinBox(
            "Octree Level",
            max_level,
            range(0, max_level, 1),
            connect=on_new_octree_level,
        )
        self.addLayout(self.octree_level)

        # Dimension information labels.
        shape = layer.data.shape
        height, width = shape[1:3]  # Which dims are really width/height?
        self.addWidget(QLabel(f"Shape: {shape}"))
        self.addWidget(QLabel(f"Width: {width}"))
        self.addWidget(QLabel(f"Height: {height}"))


class QtImageInfo(QFrame):
    """Frame showing the octree level and image dimensions.

    layer : Layer
        Show info about this layer.
    """

    def __init__(self, layer):
        super().__init__()

        def _update_layer(value):
            layer.octree_level = value

        layout = QtImageInfoLayout(layer, _update_layer)
        self.setLayout(layout)

        def _update_layout(event=None):
            layout.octree_level.set(layer.octree_level)

        # Update layout now and hook to event for future updates.
        _update_layout()
        layer.events.octree_level.connect(_update_layout)
