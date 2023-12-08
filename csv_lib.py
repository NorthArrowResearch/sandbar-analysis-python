"""
Parse a delimited text file of volcano data and create a shapefile
"""
from typing import List
import numpy as np
from logger import Logger


def union_csv_extents(csv_files: List[str], delimiter: str = ' ', cell_size: float = 1.0, padding: float = 10.0) -> tuple:
    """
    Take a list of csvfiles and finds the unioned extent of them
    We are assuming csvfile points are the center of the cell so we
    also introduce a shift by 1/2 cell height and width so that
    the raster cell centers line up
    :param csvfiles:
    :param delimiter:
    :param cellSize:
    :param padding:
    :return:
    """
    cell_size = float(cell_size)
    log = Logger('unionCSVExtents')
    value_extent: tuple = ()

    for file in csv_files:

        file_arr = np.loadtxt(open(file, 'rb'), delimiter=delimiter)

        # Get the extents (plus some padding):
        x_max = np.amax(file_arr[:, 1])
        y_max = np.amax(file_arr[:, 2])

        x_min = np.amin(file_arr[:, 1])
        y_min = np.amin(file_arr[:, 2])

        file_extent = (x_min, x_max, y_min, y_max)

        if not value_extent:
            value_extent = file_extent[:]  # Slice deep copy
        else:
            value_extent = (min(file_extent[0], value_extent[0]),
                            max(file_extent[1], value_extent[1]),
                            min(file_extent[2], value_extent[2]),
                            max(file_extent[3], value_extent[3]))

    log.debug(f'Uncorrected extent for {value_extent} delimited files is {len(csv_files)}')

    # We're calculating the extent of cell centers. To get the extent of
    # the raster we need to shift by one half cell.
    pad_and_shift = (padding * cell_size) + cell_size / 2

    # tuple(x + y for x, y in zip((0, -1, 7), (3, 4, -7)))
    corrected_extent = (
        value_extent[0] - pad_and_shift,
        value_extent[1] + pad_and_shift,
        value_extent[2] - pad_and_shift,
        value_extent[3] + pad_and_shift
    )
    log.debug(f'Corrected extent for {corrected_extent} delimited files is {len(csv_files)}')

    return corrected_extent
