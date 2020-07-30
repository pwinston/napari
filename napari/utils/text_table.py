"""TextTable class.
"""
from typing import List, Optional


# We could use an external package like colorit, printy, etc. for colors
# but now just doing it by hand.


def red(string):
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

    widths: Optional[List[int]]
        Use these widths instead of automatic widths, 0 means auto for that column.
    """

    # For auto-width columns, pad max width by this many columns to
    # leave a little room between columns.
    PADDING = 2

    def __init__(self, headers: List[str], widths: List[int] = None):
        self.headers: List[str] = headers
        self.widths: Optional[List[int]] = widths
        self.rows: List[list] = []

    def add_row(self, row: List[str]):
        """Add one row of data to the table.

        Parameters
        ----------
        row : List[str]
            The row values such as ["Fred", "25"].
        """
        self.rows.append(row)

    def _get_max_data_width(self, column_index: int) -> int:
        """Return maximum width of this column in the data."""
        if self.rows:
            return max([len(str(row[column_index])) for row in self.rows])
        return 0

    def _get_width(self, column_index: int) -> int:
        """Return column width at the given index.."""
        if self.widths is None or self.widths[column_index] == 0:
            # Auto sized column look at the data.
            data_width = self._get_max_data_width(column_index)

            # Use wider of data or the header, plus some padding.
            header_width = len(self.headers[column_index])
            return max(data_width, header_width) + self.PADDING
        else:
            # Fixed width column.
            return self.widths[column_index]

    @property
    def header_str(self):
        """Print the header of the table with the column names."""
        header_str = ""
        for i, heading in enumerate(self.headers):
            width = self._get_width(i)
            header_str += f"{str(heading):<{width}}"
        return header_str

    def row_str(self, row):
        """Print the rows of the table."""
        row_str = ""
        for i, value in enumerate(row):
            width = self._get_width(i)
            row_str += f"{str(value):<{width}}"
        return row_str

    def print(self):
        """Print the entire table: header line plus the rows."""
        print(red(self.header_str))
        for row in self.rows:
            print(self.row_str(row))
