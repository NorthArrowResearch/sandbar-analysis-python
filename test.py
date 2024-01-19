"""

    Sandbar Analysis Unit Testing

    How to use in pyCharm:
        1. preferncecs => Tools => Python Integrated Tools => Default Test Runner => Unittest
        2. Create a new run configuration using the run configuration dropdown in the top
            left. use the "+" button to choose Python Tests => Unittest
            Just se the default options
        3. Now you can run Unittests in sandbar-analysis

"""

# Utility functions we need
import unittest
from os import path, makedirs
import shutil
from osgeo import gdal
import numpy as np

# Here's what we're testing
import raster_analysis
from logger import Logger
from raster import Raster, delete_raster
from csv_lib import union_csv_extents


class TempPathHelper():
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


class TestLoggerSingletonClass(unittest.TestCase):
    """_summary_

    Args:
        unittest (_type_): _description_
    """

    def test_singleton(self):
        """
        Test the singleton. If it's not the same object nothing else matters
        """
        log1 = Logger("testMessages")
        log2 = Logger("Other things")
        self.assertIs(log1.instance.instance, log2.instance.instance)

    def test_messages(self):
        """
        Test all the basic message types
        """
        log = Logger('TestMessages')
        log.setup(logRoot='test',
                  xmlFilePath='TestMessages.xml',
                  verbose=False,
                  config={})
        log.info("Info Message")
        log.warning("Warning Message")
        log.error("Error Message")
        log.error("Error Message with exception",
                  Exception("thing is an exception"))
        log.destroy()
        self.assertTrue(True)

    def test_MultipleLoggers(self):
        log1 = Logger("Method1")
        log2 = Logger("Method2")
        log1.setup(logRoot='test',
                   xmlFilePath='TestMultipleLoggers.xml',
                   verbose=False,
                   config={})

        log1.info('TestMessages from log1')
        log2.info('TestMessages from log2')

        log1.destroy()
        log2.destroy()
        self.assertTrue(True)

    def test_DebugFlag(self):
        log = Logger('TestMessages With Verbose')
        log.setup(logRoot='test',
                  xmlFilePath='TestDebugFlagFalse.xml',
                  verbose=False,
                  config={})
        log.info("This message should appear on its own")
        log.debug("This message should not appear")

        log.setup(logRoot='test',
                  xmlFilePath='TestDebugFlagTrue.xml',
                  verbose=True,
                  config={})
        log.info("This message should appear and one below it")
        log.debug("This message should also appear")
        log.destroy()
        self.assertTrue(True)

    def test_DebugMultiObj(self):
        log = Logger('TestDebugMultiObj')
        log.setup(logRoot='test',
                  xmlFilePath='TestDebugMultiObj.xml',
                  verbose=True,
                  config={})
        log.debug("Some things:", {"thing1": "thing1Val"}, [
                  0, 1, 2, 3, 4, 5], 2232.343)
        log.destroy()
        self.assertTrue(True)


class TestRasterClass(unittest.TestCase):
    """
    Before we do anything we need to test that the mechanism
    we use to verify tests is ok.
    """

    def test_Write(self):
        """_summary_
        """
        tmp = TempPathHelper()
        filename1 = path.join(tmp.path, 'raster1.tif')
        filename2 = path.join(tmp.path, 'raster1-neg-cell-height.tif')
        nd_val = -9999.0
        data_type = gdal.GDT_Float32
        extent = (0, 0.4, 0, 0.3)
        proj = ""
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
                      cellHeight=0.1, nodata=nd_val, proj=proj)
        r_in.write(filename1)

        # Now load it into another raster object and compare the two
        r_out = Raster(filepath=filename1)
        # r_out.PrintRawArray()
        # r_out.PrintArray()
        # r_out.ASCIIPrint()
        # The input array equals the output array
        self.assertTrue((r_in.array == r_out.array).all())
        # The output array is what we expect
        self.assertTrue((r_in.array == ra_out).all())
        self.assertTrue(r_out.nodata == nd_val)
        self.assertTrue(r_out.proj == proj)
        self.assertTrue(r_out.top == extent[2])
        self.assertTrue(r_out.left == extent[0])
        self.assertTrue(r_out.data_type == data_type)

        # Try again, this time with negative cell height
        r_in2 = Raster(array=np.flipud(in_ras), extent=extent,
                       cellWidth=0.1, cellHeight=-0.1, nodata=nd_val, proj=proj)
        r_in2.write(filename2)

        # Now load it into another raster object and compare the two
        r_out2 = Raster(filepath=filename2)
        # r_out2.PrintRawArray()
        # r_out2.PrintArray()
        # r_out2.ASCIIPrint()
        self.assertTrue(r_out2.nodata == nd_val)
        self.assertTrue(r_out2.proj == proj)
        self.assertTrue(r_out2.top == extent[3])  # Top is now different
        self.assertTrue(r_out2.left == extent[0])
        self.assertTrue(r_out2.data_type == data_type)

        # The input array equals the output array
        self.assertTrue((r_in2.array == r_out2.array).all())
        # The output array is what we expect
        self.assertTrue((r_in2.array == np.flipud(ra_out)).all())

        # Clean up any files created
        delete_raster(filename1)
        delete_raster(filename2)
        tmp.destroy()

    def test_SetArray(self):
        cellSize = 1
        theExtent = (0, 3, 10, 12)
        maskedArray = np.ma.masked_array([
            [924.846, 926.17, 901.45, 942.184],
            [904.828, 912.693, np.nan, np.nan],
            [937.801, 928.423, 941.453, 912.141]],
            mask=np.array([
                [0, 0, 0, 0],
                [0, 0, 1, 1],
                [0, 0, 0, 0]]))

        unmaskedArray = np.array([
            [924.846, 926.17, 901.45, 942.184],
            [904.828, 912.693, np.nan, np.nan],
            [937.801, 928.423, 941.453, 912.141]])

        rTestMasked1 = Raster(
            extent=theExtent, cellWidth=cellSize, rows=3, cols=4)
        rTestMasked1.set_array(maskedArray)
        rTestMasked2 = Raster(
            array=maskedArray, extent=theExtent, cellWidth=cellSize, rows=3, cols=4)

        rTestNoMask1 = Raster(
            extent=theExtent, cellWidth=cellSize, rows=3, cols=4)
        rTestNoMask1.set_array(maskedArray)
        rTestNoMask2 = Raster(
            array=maskedArray, extent=theExtent, cellWidth=cellSize, rows=3, cols=4)

        print(rTestMasked1.array)
        print(rTestMasked2.array)
        print(rTestNoMask1.array)
        print(rTestNoMask2.array)

        # Compare direct Array setting to setting it later for MASKED input array
        self.assertTrue((rTestMasked1.array == rTestMasked2.array).all())
        self.assertTrue((rTestMasked1.array.mask ==
                        rTestMasked2.array.mask).all())

        # Compare direct Array setting to setting it later for UNMASKED input array
        self.assertTrue((rTestNoMask1.array == rTestNoMask2.array).all())
        self.assertTrue((rTestNoMask1.array.mask ==
                        rTestNoMask2.array.mask).all())

        # Compare masked to unmasked
        self.assertTrue((rTestMasked1.array == rTestNoMask1.array).all())
        self.assertTrue((rTestMasked1.array.mask ==
                        rTestNoMask1.array.mask).all())

        # Compare masked to unmasked
        self.assertTrue((rTestMasked2.array == rTestNoMask2.array).all())
        self.assertTrue((rTestMasked2.array.mask ==
                        rTestNoMask2.array.mask).all())

    def test_loadDEMFromCSV(self):
        tmp = TempPathHelper()
        filename = path.join(tmp.path, 'raster1.tif')
        cellSize = 1.0
        padding = 0
        gridPath = path.join(path.dirname(path.abspath(
            __file__)), 'test', 'assets', 'grids', 'grid1.txt')
        theExtent = union_csv_extents(
            [gridPath], padding, float=padding, cell_size=cellSize)
        rTest = Raster(extent=theExtent, cellWidth=cellSize)

        # Here's what we're testing:
        rTest.load_dem_from_csv(gridPath, theExtent, Raster.PointShift.CENTER)

        testArray = np.ma.masked_array([
            [924.846, 926.17, 901.45, 942.184],
            [904.828, 912.693, np.nan, np.nan],
            [937.801, 928.423, 941.453, 912.141]],
            mask=np.array([
                [0, 0, 0, 0],
                [0, 0, 1, 1],
                [0, 0, 0, 0]]))

        # If the extent is wrong then this test is invalid
        self.assertTupleEqual(theExtent, (-0.5, 3.5, 9.5, 12.5))
        self.assertEqual(theExtent[0], rTest.left)
        self.assertEqual(theExtent[3], rTest.top)

        # Now the real test begins
        self.assertEqual(rTest.cell_height, -cellSize)
        self.assertEqual(rTest.cell_width, cellSize)
        self.assertEqual(rTest.rows, 3)
        self.assertEqual(rTest.cols, 4)
        self.assertEqual(rTest.left, -0.5)
        self.assertEqual(rTest.top, 12.5)
        self.assertEqual(rTest.array.shape, (3, 4))
        self.assertTrue((rTest.array == testArray).all())
        rTest.write(filename)
        delete_raster(filename)
        tmp.destroy()

    def test_MergeMinSurface(self):
        cellSize = 1
        gridPath1 = path.join(path.dirname(path.abspath(
            __file__)), 'test', 'assets', 'grids', 'grid1.txt')
        gridPath2 = path.join(path.dirname(path.abspath(
            __file__)), 'test', 'assets', 'grids', 'grid2.txt')

        theExtent = union_csv_extents([gridPath1, gridPath2], padding, float=0)
        # Create our two grids from CSV files that we can add into the min surface
        rTest1 = Raster(extent=theExtent, cellWidth=cellSize)
        rTest1.load_dem_from_csv(gridPath1, theExtent,
                                 pt_center=Raster.PointShift.CENTER)
        rTest2 = Raster(extent=theExtent, cellWidth=cellSize)
        rTest2.load_dem_from_csv(gridPath2, theExtent,
                                 pt_center=Raster.PointShift.CENTER)

        # Now let's create a min surface we can use to test things
        rMinSrf = Raster(extent=theExtent, cellWidth=cellSize)
        rMinSrf.set_array(np.nan * np.empty((rTest1.rows, rTest1.cols)))

        rMinSrf.merge_min_surface(rTest1)
        testArray = np.ma.masked_array([
            [924.846, 926.17, 901.45, 942.184],
            [904.828, 912.693, np.nan, np.nan],
            [937.801, 928.423, 941.453, 912.141]],
            mask=np.array([
                [0, 0, 0, 0],
                [0, 0, 1, 1],
                [0, 0, 0, 0]]))
        self.assertTrue((rMinSrf.array == testArray).all())

        rMinSrf.merge_min_surface(rTest2)
        testArray2 = np.ma.masked_array([
            [911.511, 922.517, 901.45, 923.232],
            [904.828, 911.819, 907.663, 931.264],
            [919.413, 920.007, 941.453, 912.141]],
            mask=np.array([
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0]]))
        self.assertTrue((rMinSrf.array == testArray2).all())

    def test_ResampleDEM(self):
        cellSize = 1
        nd_val = -9999.0
        theExtent = (0, 3, 10, 12)
        theTestArray = np.ma.masked_array([
            [0.0, 1, 2, 3],
            [nd_val, np.nan, 6, 3],
            [100, 200.0, 300, 500000.0]],
            mask=np.array([
                [0, 0, 1, 0],
                [1, 1, 0, 0],
                [0, 0, 0, 0]]))

        rTest1 = Raster(array=theTestArray,
                        extent=theExtent, cellWidth=cellSize)
        rTest1.print_array()
        rTest1.ascii_print()
        rLinear = rTest1.resample_dem(0.5, 'linear')
        rLinear.print_array()
        rLinear.ascii_print()

        rBilinear = rTest1.resample_dem(0.5, 'bilinear')
        rBilinear.print_array()

        rCubic = rTest1.resample_dem(0.5, 'cubic')
        rCubic.print_array()
        rCubic.ascii_print()

        rNearest = rTest1.resample_dem(0.5, 'nearest')
        rNearest.print_array()
        rNearest.ascii_print()

        # We have no test for this so it should always fail
        self.assertTrue(False)

    def test_ResampleCSVDEM(self):
        tmp = TempPathHelper()
        padding = 5

        cellSize = 1
        gridPath1 = path.join(path.dirname(path.abspath(
            __file__)), 'test', 'assets', 'grids', 'realgrid.txt')
        theExtent = union_csv_extents([gridPath1], padding, float=padding)
        # Create our grid from CSV file that we can add into the min surface
        rTest1 = Raster(extent=theExtent, cellWidth=cellSize)
        rTest1.load_dem_from_csv(gridPath1, theExtent,
                                 pt_center=Raster.PointShift.CENTER)
        rTest1filename = path.join(tmp.path, 'realgrid.tif')
        rTest1.write(rTest1filename)

        rLinear = rTest1.resample_dem(0.5, 'linear')
        rLinearFilename = path.join(tmp.path, 'realgridLinear.tif')
        rLinear.write(rLinearFilename)

        rBilinear = rTest1.resample_dem(0.5, 'bilinear')
        rBilinearFilename = path.join(tmp.path, 'realgridBilinear.tif')
        rBilinear.write(rBilinearFilename)

        rCubic = rTest1.resample_dem(0.5, 'cubic')
        rCubicfilename = path.join(tmp.path, 'realgridCubic.tif')
        rCubic.write(rCubicfilename)

        rNearest = rTest1.resample_dem(0.5, 'nearest')
        rNearestFilename = path.join(tmp.path, 'realgridNearest.tif')
        rNearest.write(rNearestFilename)

        delete_raster(rTest1filename)
        delete_raster(rLinearFilename)
        delete_raster(rBilinearFilename)
        delete_raster(rCubicfilename)
        delete_raster(rNearestFilename)
        tmp.destroy()

        # We have no test for this so it should always fail
        self.assertTrue(False)


class TestSandbarSite(unittest.TestCase):
    """
    Testing raster creation from CSV
        All these methods have been done by hand first. Compare to this:
        https://docs.google.com/spreadsheets/d/1fimx0WABf2cm7fhs_EUithfgGOwky5tTX2_IRf9M1aI/edit#gid=0
    """

    def test_getRasterTXTUnionExtent(self):
        padding = 10
        cellsize = 1.0
        tmp = TempPathHelper()
        currdir = path.dirname(path.abspath(__file__))
        gridPath1 = path.join(currdir, 'test', 'assets', 'grids', 'grid1.txt')
        gridPath2 = path.join(currdir, 'test', 'assets', 'grids', 'grid2.txt')
        gridPath3 = path.join(currdir, 'test', 'assets', 'grids', 'grid3.txt')

        theExtent = union_csv_extents(
            [gridPath1, gridPath2, gridPath3], padding, float=10)
        self.assertTupleEqual(theExtent, (-10.5, 14.5, -0.5, 23.5))


class TestAreaVolume(unittest.TestCase):
    """
    Refer to this spreadsheet: https://docs.google.com/spreadsheets/d/1MmjVkg4lg50rC0n6xYBTeor0T3_QPLQRaEYFmBnB5OA/edit#gid=0

    NOTE: THE FOLLOWING ASSUMES THRESHOLDING ASSUMES BOTH ">" AND "<" (AS OPPOSED TO "<=" AND/OR ">=")
    """

    def setUp(self):
        # Input Array. here we test lots of different kinds of values
        self.nd_val = -9999.0
        self.cellSize = 0.1

        self.arSurf = np.ma.masked_array([
            [10.0, 12, self.nd_val, 13],
            [np.nan, 18, 24.0, 3],
            [100, 3.0, 30.0, 20.0]],
            mask=np.array([
                [0, 0, 1, 0],
                [1, 0, 0, 0],
                [0, 0, 0, 0]]))

        # Set the minimum surface up with some values
        self.arMin = np.ma.masked_array([
            [10, 0.5, 0.1, 0.002],
            [self.nd_val, 15, 0.1, 0.003],
            [0.0, 0.5, 20, 0.004]],
            mask=np.array([
                [0, 0, 1, 0],
                [1, 0, 0, 0],
                [0, 1, 0, 0]]))

    def test_LowZeroNoHigh(self):
        """
        Test when low threshold is 0 and there is no high threshold
        """
        test = raster_analysis.get_vol_and_area(
            self.arSurf, self.arMin, 0, None, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.08, places=7)
        self.assertAlmostEqual(test[1], 1.8439, places=7)

    def test_LowNoHigh(self):
        """
        Test when low threshold is 1 and there is no high threshold
        """
        test = raster_analysis.get_vol_and_area(
            self.arSurf, self.arMin, 10, None, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.07, places=7)
        self.assertAlmostEqual(test[1], 1.32, places=7)

    def test_HighNoLow(self):
        """
        Test when there is a high threshold but no low threshold
        """
        test = raster_analysis.get_vol_and_area(
            self.arSurf, self.arMin, None, 20, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.04, places=7)
        self.assertAlmostEqual(test[1], 0.305, places=7)

    def test_LowAndHigh(self):
        test = raster_analysis.get_vol_and_area(
            self.arSurf, self.arMin, 10, 20, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.03, places=7)
        self.assertAlmostEqual(test[1], 0.08, places=7)

    def test_MinEqualSurface(self):
        """
        Test when the minimum surface is equal to the surface being tested
        """
        test = raster_analysis.get_vol_and_area(
            self.arMin, self.arMin, 0, None, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.08, places=7)
        self.assertAlmostEqual(test[1], 0.0, places=7)

        test = raster_analysis.get_vol_and_area(
            self.arMin, self.arMin, 10, None, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.02, places=7)
        self.assertAlmostEqual(test[1], 0.0, places=7)

        test = raster_analysis.get_vol_and_area(
            self.arMin, self.arMin, None, 20, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.08, places=7)
        self.assertAlmostEqual(test[1], 0.0, places=7)

        test = raster_analysis.get_vol_and_area(
            self.arMin, self.arMin, 10, 20, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.01, places=7)
        self.assertAlmostEqual(test[1], 0.0, places=7)

    def test_HighThresholds(self):
        """
        Test when the thresholds are all super high (above the surface and the minimum)
        """
        test = raster_analysis.get_vol_and_area(
            self.arSurf, self.arMin, 101, None, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.0, places=7)
        self.assertAlmostEqual(test[1], 0.0, places=7)

        test = raster_analysis.get_vol_and_area(
            self.arSurf, self.arMin, None, 200, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.08, places=7)
        self.assertAlmostEqual(test[1], 1.8439, places=7)

        test = raster_analysis.get_vol_and_area(
            self.arSurf, self.arMin, 101, 200, self.cellSize, "")
        self.assertAlmostEqual(test[0], 0.0, places=7)
        self.assertAlmostEqual(test[1], 0.0, places=7)


if __name__ == '__main__':
    unittest.main()
