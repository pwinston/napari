"""SimpleStat class.
"""


class SimpleStat:
    """Keep min/max/average on an integer value.

    Attributes
    ----------
    min : int
        Minimum value so far.
    max : int
        Maximum value so far.
    sum : int
        Sum of all values seen.
    count : int
        How many values we've seen.
    """

    def __init__(self, value: int):
        """Create SimpleStat with an initial value.

        Parameters
        ----------
        value : int
            Initial value.
        """
        self.min = value
        self.max = value
        self.sum = value
        self.count = 1

    def add(self, value: int) -> None:
        """Add a new value.

        Parameters
        ----------
        value : int
            The new value.
        """
        self.sum += value
        self.count += 1
        self.max = max(self.max, value)
        self.min = min(self.min, value)

    @property
    def average(self) -> int:
        """Average value."""
        if self.count > 0:
            return self.sum / self.count
        raise ValueError("no values")
