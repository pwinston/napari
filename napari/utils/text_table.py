"""TextTable class.

Notes
-----
We could use an external package like colorit, printy, etc. for colors
but now just doing it by hand.
"""
from typing import List


def _red(string):
    return f"\x1b[31m{string}\x1b[0m"


class TextTable:
    """A printable text table with a header and rows.

    Usage:
        table = table(["NAME", "AGE"], [10, 5])
        table.add_row["Mary", "25"]
        table.add_row["Alice", "32"]
        table.print()

    Would print:
        NAME       AGE
        Mary       25
        Alice      32

    Parameters
    ----------
    headers : List[str]
        The column headers such as  ["NAME", "AGE"].

    widths: List[int]
        The column widths such as [10, 5]. Where 0 means auto-size.
    """

    # For auto-width columns, pad max width by this many columns to
    # leave a little room between columns.
    PADDING = 2

    def __init__(self, headers: List[str], widths: List[int]):
        self.headers: List[str] = headers
        self.widths: List[int] = widths
        self.rows: List[list] = []

    def add_row(self, row: List[str]):
        """Add one row of data to the table.

        Parameters
        ----------
        row : List[str]
            The row values such as ["Fred", "25"].
        """
        self.rows.append(row)

    def get_width(self, index: int) -> int:
        """Return max width of the column at the given index."""
        return max([len(str(x)) for x in self.rows[index]])

    @property
    def header_str(self):
        """Print the header of the table with the column names."""
        header_str = ""
        for heading, width in zip(self.headers, self.widths):
            header_str += f"{str(heading):<{width}}"
        return header_str

    def row_str(self, row):
        """Print the rows of the table."""
        row_str = ""
        for i, value in enumerate(row):
            width = self.widths[i]
            if width == 0:
                width = self.get_width(i) + self.PADDING
            row_str += f"{str(value):<{width}}"
        return row_str

    def print(self):
        """Print the entire table: header line plus the rows."""
        print(_red(self.header_str))
        for row in self.rows:
            print(self.row_str(row))
