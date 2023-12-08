"""

    Sandbar Analysis Unit Testing

    How to use in pyCharm:
        1. preferncecs => Tools => Python Integrated Tools => Default Test Runner => Unittest
        2. Create a new run configuration using the run configuration dropdown in the top
            left. use the "+" button to choose Python Tests => Unittest
            Just se the default options
        3. Now you can run Unittests in sandbar-analysis

"""
from os import path
from os import makedirs
import shutil
import numpy as np
from osgeo import gdal
from Raster import Raster


class TempPathHelper():
    """_summary_
    """

    def __init__(self):
        """
        Create for us a tmp Path
        :return: the path to the tmp folder
        """
        cwd = path.dirname(path.abspath(__file__))
        self.path = path.join(cwd, 'TMP')
        if path.isdir(self.path):
            self.destroy()
        makedirs(self.path)

    def destroy(self):
        """
        Clean up our tmp folder
        :return:
        """
        if self.path is not None and path.isdir(self.path):
            shutil.rmtree(self.path)


# Here's what we're testing
tmp = TempPathHelper()
filename1 = path.join(tmp.path, 'raster1.tif')
filename2 = path.join(tmp.path, 'raster1-neg-cell-height.tif')
nd_val = -9999.0
data_type = gdal.GDT_Float32
extent = (0, 0.4, 0, 0.3)
# Input Array. here we test lots of different kinds of values
in_ras = np.ma.masked_array([
    [0.0, 1, 2, 3],
    [nd_val, np.nan, np.nan, 3],
    [100, 200.0, 300, 500000.0]],
    mask=np.array([
        [0, 0, 1, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0]]))

# And here's what we expect to get back when we read the file back in:
# NB: Note different mask and values
ra_out = np.ma.masked_array([
    [0.0, 1.0, nd_val, 3.0],
    [nd_val, nd_val, nd_val, 3.0],
    [100, 200.0, 300.0, 500000.0]],
    mask=np.array([
        [0, 0, 1, 0],
        [1, 1, 1, 0],
        [0, 0, 0, 0]
    ]))

r_in = Raster(array=in_ras, extent=extent, cellWidth=0.1,
              cellHeight=0.1, nodata=nd_val)
r_in.write(filename1)
