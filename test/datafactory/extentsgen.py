import json
import os
from osgeo import gdal, ogr, osr
from os import path
import numpy as np
from shapely.geometry import *

ogr.UseExceptions()
gdal.UseExceptions()

proj = 'PROJCS["NAD_1983_2011_StatePlane_Arizona_Central_FIPS_0202",GEOGCS["GCS_NAD_1983_2011",DATUM["NAD_1983_2011",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["false_easting",213360.0],PARAMETER["false_northing",0.0],PARAMETER["central_meridian",-111.9166666666667],PARAMETER["scale_factor",0.9999],PARAMETER["latitude_of_origin",31.0],UNIT["Meter",1.0]]'

class Raster:
    def __init__(self, filepath):
        gdal.UseExceptions()
        self.errs = ""
        self.filename = path.basename(filepath)
        try:
            src_ds = gdal.Open( filepath )
        except RuntimeError, e:
            print('Unable to open %s' % filepath)
            exit(1)
        try:
            # Read Raster Properties
            self.srcband = src_ds.GetRasterBand(1)
            self.bands = src_ds.RasterCount
            self.driver = src_ds.GetDriver().LongName
            self.gt = src_ds.GetGeoTransform()

            """ Turn a Raster with a single band into a 2D [x,y] = v array """
            self.array = self.srcband.ReadAsArray()
            self.dataType = self.srcband.DataType
            self.band_array = self.srcband.ReadAsArray()
            self.nodata = self.srcband.GetNoDataValue()
            self.min = self.srcband.GetMinimum()
            self.max = self.srcband.GetMaximum()
            self.proj = src_ds.GetProjection()
            self.left = self.gt[0]
            self.cellWidth = self.gt[1]
            self.top = self.gt[3]
            self.cellHeight = self.gt[5]
            self.cols = src_ds.RasterXSize
            self.rows = src_ds.RasterYSize

        except RuntimeError as e:
            print('Could not retrieve meta Data for %s' % filepath)
            exit(1)

class Shapefile:

    def __init__(self, sFilename=None):
        self.driver = ogr.GetDriverByName("ESRI Shapefile")
        self.datasource = None
        if sFilename:
            self.load(sFilename)

    def create(self, sFilename, spatialRef=None, geoType=ogr.wkbPolygon):
        if os.path.exists(sFilename):
            self.driver.DeleteDataSource(sFilename)
        self.driver = None
        self.driver = ogr.GetDriverByName("ESRI Shapefile")
        self.datasource = self.driver.CreateDataSource(sFilename)
        self.layer = self.datasource.CreateLayer(sFilename, spatialRef, geom_type=geoType)

    def createField(self, fieldName, ogrOFT):
        """
        Create a field on the layer
        :param fieldName:
        :param ogrOFT:
        :return:
        """
        aField = ogr.FieldDefn(fieldName, ogrOFT)
        self.layer.CreateField(aField)

def CreateShape(traster, topoffset, leftoffset, pxwidth, pxheight, margin):

    rWidth = pxwidth * traster.cellWidth
    rHeight = pxheight * traster.cellHeight

    vMargin = margin * traster.cellHeight
    hMargin = margin * traster.cellWidth

    pts = [
        (traster.left + leftoffset + hMargin, traster.top + topoffset + vMargin),
        (traster.left + leftoffset + hMargin, traster.top + topoffset + rHeight - vMargin),
        (traster.left + leftoffset + rWidth - hMargin, traster.top + topoffset + rHeight - vMargin),
        (traster.left + leftoffset + rWidth - hMargin, traster.top + topoffset + vMargin)
    ]
    shape1 = Polygon([
        pts[0],
        pts[1],
        pts[2],
        pts[0]
    ])
    shape2 = Polygon([
        pts[2],
        pts[3],
        pts[0],
        pts[2]
    ])

    return (shape1, shape2)


def main():
    templateRaster = Raster('SampleData/0003L_19950623_dem.tif')

    # Create shapes with the following parameters
    pxwidth = 100
    pxheight = 100
    squaregrid = 3
    spacing = 100
    margin = 10

    folder = 'output' + path.sep
    outShape = Shapefile()

    spatialRef = osr.SpatialReference()
    spatialRef.ImportFromWkt(proj)

    outShape.create(folder + 'extent.shp', spatialRef, geoType=ogr.wkbPolygon)

    outShape.createField("OBJECT_ID", ogr.OFTInteger)
    outShape.createField("Section", ogr.OFTString)
    outShape.createField("Site", ogr.OFTString)

    featid = 0
    for idx in range(0,squaregrid):
        for idy in range(0, squaregrid):

            topoffset = idx * (pxheight + spacing) * templateRaster.cellHeight
            leftoffset = idy * (pxwidth + spacing) * templateRaster.cellWidth
            shape1, shape2 = CreateShape(templateRaster, topoffset, leftoffset, pxwidth, pxheight, margin)
            obj = {
                "channel": shape1,
                "eddy": shape2
            }
            for name, shape in obj.iteritems():

                featid += 1
                featureDefn = outShape.layer.GetLayerDefn()
                outFeature = ogr.Feature(featureDefn)

                featureID = featid
                outFeature.SetField('OBJECT_ID', featureID)
                outFeature.SetField('Section', name)
                outFeature.SetField("Site", '0001R')

                ogrmultiline = ogr.CreateGeometryFromJson(json.dumps(mapping(shape)))
                outFeature.SetGeometry(ogrmultiline)
                outShape.layer.CreateFeature(outFeature)


if __name__ == '__main__':

    main()
