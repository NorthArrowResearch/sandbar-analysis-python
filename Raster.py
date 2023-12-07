"""
Generic raster class for basic raster operations
"""
from os import path
from typing import Type
from osgeo import gdal, osr
import numpy as np
from scipy import interpolate
from logger import Logger

# this allows GDAL to throw Python Exceptions
gdal.UseExceptions()


class Raster:
    """
    Generic raster class for basic raster operations
    """

    class PointShift:
        CENTER = (0.5, -0.5)
        TOPLEFT = (1.0, -1.0)
        TOPRIGHT = (1.0, 0)
        BOTTOMLEFT = (0.0, -1.0)
        BOTTOMRIGHT = (0.0, 1.0)

    def __init__(self, *args, **kwargs):

        self.log = Logger("Raster")
        self.filename = kwargs.get('filepath', None)

        # Got a file. Load it
        if self.filename is not None:
            self.errs = ""
            try:
                src_ds = gdal.Open(self.filename)
            except RuntimeError as e:
                self.log.error(f'Unable to open {self.filename}', e)
                raise e
            try:
                # Read Raster Properties
                srcband = src_ds.GetRasterBand(1)
                self.bands = src_ds.RasterCount
                self.driver = src_ds.GetDriver().LongName
                self.gt = src_ds.GetGeoTransform()
                self.nodata = srcband.GetNoDataValue()
                """ Turn a Raster with a single band into a 2D [x,y] = v array """
                self.array = srcband.ReadAsArray()

                # Now mask out any NAN or nodata values (we do both for consistency)
                if self.nodata is not None:
                    self.array = np.ma.array(self.array, mask=(np.isnan(self.array) | (self.array == self.nodata)))

                self.data_type = srcband.DataType
                self.min = np.nanmin(self.array)
                self.max = np.nanmax(self.array)

                if self.min is np.ma.masked:
                    self.min = np.nan
                if self.max is np.ma.masked:
                    self.max = np.nan

                self.proj = src_ds.GetProjection()

                # Remember:
                # [0]/* top left x */
                # [1]/* w-e pixel resolution */
                # [2]/* rotation, 0 if image is "north up" */
                # [3]/* top left y */
                # [4]/* rotation, 0 if image is "north up" */
                # [5]/* n-s pixel resolution */
                self.left = self.gt[0]
                self.cell_width = self.gt[1]
                self.top = self.gt[3]
                self.cell_height = self.gt[5]
                self.cols = src_ds.RasterXSize
                self.rows = src_ds.RasterYSize
                # Important to throw away the srcband
                srcband.FlushCache()
                srcband = None

            except RuntimeError as e:
                self.log.error(f'Could not retrieve meta Data for {self.filename}', e)
                raise e

        # No file to load. this is a new raster
        else:
            self.nodata = kwargs.get('nodata', -9999.0)
            self.min = None
            self.max = None
            self.array = None

            self.rows = int(kwargs.get('rows', 0))
            self.cols = int(kwargs.get('cols', 0))
            self.cell_width = float(kwargs.get('cellWidth', 0.1))
            self.cell_height = float(kwargs.get('cellHeight', -self.cell_width))
            self.proj = kwargs.get('proj', "")
            self.data_type = kwargs.get('dataType', gdal.GDT_Float32)

            temp_array = kwargs.get('array', None)
            if temp_array is not None:
                self.set_array(temp_array)
                self.min = np.nanmin(self.array)
                self.max = np.nanmax(self.array)

            extent = kwargs.get('extent', None)

            # Expecting extent in the form [Xmin, Xmax, Ymin, Ymax]
            if extent is not None:
                self.left = float(extent[0] if self.cell_width > 0 else extent[1])  # What we mean by left is : top left 'X'
                self.top = float(extent[2] if self.cell_height > 0 else extent[3])  # What we mean by top is : top left 'Y'

                self.rows = abs(int(round((extent[3] - extent[2]) / self.cell_height)))
                self.cols = abs(int(round((extent[1] - extent[0]) / self.cell_width)))
            else:
                self.top = float(kwargs.get('top', -9999.0))
                self.left = float(kwargs.get('left', -9999.0))

    def load_dem_from_csv(self, csv_path: str, the_extent, pt_center=None) -> None:
        """
        Populate a raster's grid with values from a CSV file
        :param sCSVPath:
        :return:
        """
        if not pt_center:
            pt_center = self.PointShift.CENTER

        file_arr = np.loadtxt(open(csv_path, "rb"), delimiter=" ")

        # Set up an empty array with the right size
        z_array = np.empty((self.rows, self.cols))
        z_array[:] = np.nan

        # If there is a :, python will pass .cellHeight))a slice:
        # Remember: theExtent = (Xmin, Xmax, Ymin, Ymax)
        x = (file_arr[:, 1] - (the_extent[0] + (pt_center[0] * self.cell_width))).astype(int)
        y = (file_arr[:, 2] - (the_extent[2] + (pt_center[1] * self.cell_height))).astype(int)

        # Assign every point in the flat array to a grid point
        z_array[y, x] = file_arr[:, 3]

        # This array might be upside-down from GDAL's perspective
        if self.cell_height < 0:
            self.set_array(np.flipud(z_array), True)
        else:
            self.set_array(z_array, True)

    def meta_copy(self):
        """
        Copy everything but the array
        :return:
        """
        return Raster(left=self.left, top=self.top, nodata=self.nodata, proj=self.proj,
                      dataType=self.data_type, cellWidth=self.cell_width, cellHeight=self.cell_height)

    def merge_min_surface(self, arr_dem: np.array) -> None:
        """
        :param rDEM:
        :return:
        """
        # TODO: the masks are more complicated than this but we can make assumptions
        # because we always get to the mask the same way.
        min_arr = np.ma.masked_invalid(np.fmin(self.array.data, arr_dem.array.data))

        self.set_array(min_arr)

    def resample_dem(self, new_cell_size: float, method: str) -> Type['Raster']:
        """
        Resample the raster and return a new resampled raster
        current raster
        :param newCellSize:
        :param method:
        :return:
        """
        # Create a blank copy with everything but the array
        new_dem = self.meta_copy()

        self.log.debug(f'Resampling original data from {self.cell_width}m to {new_cell_size}m using {method} method')
        array_resampled = None

        x_axis_old, y_axis_old = np.ma.masked_array(np.mgrid[0:self.rows:self.cell_width, 0:self.cols:abs(self.cell_height)],
                                                    (self.array.mask, self.array.mask))

        x_axis_new, y_axis_new = np.mgrid[0:self.rows:new_cell_size, 0:self.cols:new_cell_size]
        new_mask = interpolate.griddata((x_axis_old.ravel(), y_axis_old.ravel()), self.array.mask.ravel(),
                                        (x_axis_new, y_axis_new), method='nearest', fill_value=np.nan)

        # Put us in the middle of the cell
        x_axis_old += abs(self.cell_width) / 2
        y_axis_old += abs(self.cell_height) / 2

        # Bilinear is a lot slower that the others and it's its own
        # method, written based on the
        # well known wikipedia article.
        if method == "bilinear":
            # Now we resample based on the method passed in here.
            factor = self.cell_width / new_cell_size
            new_shape = (int(self.rows * factor), int(self.cols * factor))
            array_resampled = bilinear_resample(self.array, new_shape)
        elif method == "linear" or method == "cubic" or method == "nearest":
            array_resampled = interpolate.griddata((x_axis_old.ravel(), y_axis_old.ravel()), self.array.ravel(),
                                                   (x_axis_new, y_axis_new), method=method, fill_value=np.nan)
        else:
            raise ValueError(f"Resample Method: '{method}' not recognized")

        # Set the new cell size and set the new array
        new_dem.cell_width = new_cell_size
        new_dem.cell_height = -new_cell_size
        new_dem.set_array(np.ma.masked_array(array_resampled, new_mask), False)
        self.log.debug("Successfully Resampled Raster")
        return new_dem

    def set_array(self, incoming_array: np.array, copy=False) -> None:
        """
        You can use the self.array directly but if you want to copy from one array
        into a raster we suggest you do it this way
        :param incomingArray:
        :return:
        """
        masked = isinstance(self.array, np.ma.MaskedArray)
        if copy:
            if masked:
                self.array = np.ma.copy(incoming_array)
            else:
                self.array = np.ma.masked_invalid(incoming_array, copy=True)
        else:
            if masked:
                self.array = incoming_array
            else:
                self.array = np.ma.masked_invalid(incoming_array)

        self.rows = self.array.shape[0]
        self.cols = self.array.shape[1]
        self.min = np.nanmin(self.array)
        self.max = np.nanmax(self.array)

    def write(self, output_raster: str) -> None:
        """
        Write this raster object to a file. The Raster is closed after this so keep that in mind
        You won't be able to access the raster data after you run this.
        :param outputRaster:
        :return:
        """
        if path.isfile(output_raster):
            delete_raster(output_raster)

        driver = gdal.GetDriverByName('GTiff')
        out_raster = driver.Create(output_raster, self.cols, self.rows, 1, self.data_type, ['COMPRESS=LZW'])

        # Remember:
        # [0]/* top left x */
        # [1]/* w-e pixel resolution */
        # [2]/* rotation, 0 if image is "north up" */
        # [3]/* top left y */
        # [4]/* rotation, 0 if image is "north up" */
        # [5]/* n-s pixel resolution */
        out_raster.SetGeoTransform([self.left, self.cell_width, 0, self.top, 0, self.cell_height])
        outband = out_raster.GetRasterBand(1)

        # Set nans to the original No Data Value
        outband.SetNoDataValue(self.nodata)
        self.array.data[np.isnan(self.array)] = self.nodata
        # Any mask that gets passed in here should have masked out elements set to
        # Nodata Value
        if isinstance(self.array, np.ma.MaskedArray):
            np.ma.set_fill_value(self.array, self.nodata)
            outband.WriteArray(self.array.filled())
        else:
            outband.WriteArray(self.array)

        spatial_ref = osr.SpatialReference()
        spatial_ref.ImportFromWkt(self.proj)

        out_raster.SetProjection(spatial_ref.ExportToWkt())
        outband.FlushCache()
        # Important to throw away the srcband
        outband = None
        self.log.debug(f'Finished Writing Raster: {output_raster}')

    def print_raw_array(self):
        """
        Raw print of raster array values. useful to visualize rasters on the command line
        :return:
        """
        print('\n----------- Raw Array -----------')
        masked = isinstance(self.array, np.ma.MaskedArray)
        for row in range(self.array.shape[0]):
            row_str = ' '.join(map(str, self.array[row])).replace('-- ', '- ').replace('nan ', '_ ')
            print(f'{row}:: {row_str}')
        print('\n')

    def print_array(self):
        """
        Print the array flipped if the cellHeight is negative
        useful to visualize rasters on the command line
        :return:
        """
        arr = None
        str_flipped = "False"
        if self.cell_height >= 0:
            arr = np.flipud(self.array)
            str_flipped = "True"
        else:
            arr = self.array
        print(f'\n----------- Array Flip: {str_flipped} -----------')
        masked = isinstance(arr, np.ma.MaskedArray)
        for row in range(arr.shape[0]):
            row_str = ' '.join(map(str, arr[row])) + ' '
            row_str = row_str.replace('-- ', '- ').replace('nan ', '_ ')
            print(f'{row}:: {row_str}')
        print('\n')

    def ascii_print(self):
        """
        Print an ASCII representation of the array with an up-down flip if the
        the cell height is negative.

        Int this scenario:
            - '-' means masked
            - '_' means nodata
            - '#' means a number
            - '0' means 0
        :param arr:
        """
        arr = None
        if self.cell_height >= 0:
            arr = np.flipud(self.array)
        else:
            arr = self.array
        print('\n')
        masked = isinstance(arr, np.ma.MaskedArray)
        for row in range(arr.shape[0]):
            row_str = ""
            for col in range(arr[row].shape[0]):
                col_str = str(arr[row][col])
                if col_str == 'nan':
                    row_str += "_"
                elif masked and arr.mask[row][col]:
                    row_str += "-"
                elif arr[row][col] == 0:
                    row_str += "0"
                else:
                    row_str += "#"
            print(f'{row}:: {row_str}')
        print('\n')


def delete_raster(full_path: str) -> None:
    """
    Delete a raster on disk
    :param path:
    :return:
    """

    log = Logger("Delete Raster")

    if path.isfile(full_path):
        try:
            # Delete the raster properly
            driver = gdal.GetDriverByName('GTiff')
            gdal.Driver.Delete(driver, full_path)
            log.debug(f'Raster Successfully Deleted: {full_path}')
        except Exception as e:
            log.error(f'Failed to remove existing clipped raster at {full_path}')
            raise e
    else:
        log.debug(f'No raster file to delete at {full_path}')


def bilinear_resample(old_grid: np.array, new_shape: tuple) -> np.array:
    '''
    :param oldGrid: A 2D array. This must be a regularly spaced grid (like a raster band array)
    :param newShape: the new shape you want in tuple format eg: (200,300)
    :return: newArr: The resampled array.
    '''
    new_arr = np.nan * np.empty(new_shape)
    old_cols, old_rows = old_grid.shape
    new_cols, new_rows = new_shape
    x_mult = float(new_cols) / old_cols  # 4 in our test case
    y_mult = float(new_rows) / old_rows

    for (x, y), __element in np.ndenumerate(new_arr):
        # do a transform to figure out where we are ont he old matrix
        fx = x / x_mult
        fy = y / y_mult

        ix1 = int(np.floor(fx))
        iy1 = int(np.floor(fy))

        # Special case where point is on upper bounds
        if fx == float(new_cols - 1):
            ix1 -= 1
        if fy == float(new_rows - 1):
            iy1 -= 1

        ix2 = ix1 + 1
        iy2 = iy1 + 1

        # Test if we're within the raster midpoints
        if (ix1 >= 0) and (iy1 >= 0) and (ix2 < old_cols) and (iy2 < old_rows):
            # get the 4 values we need
            vals = [old_grid[ix1, iy1], old_grid[ix1, iy2], old_grid[ix2, iy1], old_grid[ix2, iy2]]

            # Here's where the actual interpolation is but make sure
            # there aren't any nan values.
            if not np.any([np.isnan(v) for v in vals]):
                new_arr[x, y] = (vals[0] * (ix2 - fx) * (iy2 - fy) + vals[1] * (fx - ix1) * (iy2 - fy) + vals[2] * (ix2 - fx) * (fy - iy1) + vals[3] * (fx - ix1) * (fy - iy1)) / ((ix2 - ix1) * (iy2 - iy1) + 0.0)

    return new_arr


def array2raster_template(array: np.array, output_raster: str, template_raster: str) -> None:
    """
    This is similar to the function above only it gets its initial values from an
    input "template" raster. Useful when creating a new raster based on an old one
    :param array:
    :param outputRaster:
    :param templateRaster:
    :return:
    """
    raster = Raster(filepath=template_raster)
    raster.set_array(array)
    raster.write(output_raster)
