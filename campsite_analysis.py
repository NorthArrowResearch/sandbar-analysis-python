"""
Run the binned analysis
"""
from typing import Dict, List, Tuple
import re
import os
import csv
import math
from datetime import datetime
from osgeo import ogr
from raster_analysis import get_vol_and_area
from logger import Logger
from sandbar_site import SandbarSite
from analysis_bin import AnalysisBin
from clip_raster import clip_raster
from points_to_raster import points_to_raster

file_name_pattern = re.compile(r'^(?P<site_name>[^_]+)_(?P<survey_date>\d{8})_.*')

# Column indices for the corgrids text file
CORGRIDS_X_COL = 1
CORGRIDS_Y_COL = 2
CORGRIDS_Z_COL = 3


def run_campsite_analysis(
        campsite_parent_folder: str,
        sites: Dict[int, SandbarSite],
        analysis_folder: str,
        analysis_bins: Dict[int, AnalysisBin],
        cell_size: float,
        result_file_path: str,
        gdal_warp: str,
        reuse_rasters: bool) -> None:
    """
    Run the binned analysis
    """

    model_results: List[tuple] = []
    log = Logger('Campsite Analysis')
    log.info('Starting campsite analysis...')

    for site_id, site in sites.items():

        campsite_folder = os.path.join(campsite_parent_folder, site.site_code)
        campsite_surveys = get_campsite_surveys(campsite_folder)

        if len(campsite_surveys) < 1:
            continue

        for campsite_survey_date_str, campsite_shapefile in campsite_surveys.items():
            campsite_survey_date = datetime.strptime(campsite_survey_date_str, '%Y%m%d')
            # loop over each sandbar survey to find the one with the closest date to the campsite survey
            closest_survey_date = None
            closest_survey = None
            for survey in site.surveys.values():
                survey_date = survey.survey_date
                if closest_survey_date is None or abs((survey_date - campsite_survey_date).days) < abs((closest_survey_date - campsite_survey_date).days):
                    closest_survey_date = survey_date
                    closest_survey = survey

            # Create a new folder for this campsite survey
            processing_folder = os.path.join(analysis_folder, site.site_code5, 'campsites', campsite_survey_date_str)
            if os.path.exists(processing_folder):
                # delete existing folder and all files in it in one command
                os.system(f'rm -rf {processing_folder}')
            os.makedirs(processing_folder)

            merged_shapefile = os.path.join(processing_folder, 'merged_points.shp')
            polygon_shapefile = os.path.join(processing_folder, 'campsite_polygons.shp')
            raster_path = os.path.join(processing_folder, 'merged_dem.tif')
            clipped_path = os.path.join(processing_folder, 'clipped_dem.tif')
            buffered_extent = get_buffered_campsite_extent(campsite_shapefile, cell_size)

            create_points_shapefile_from_campsite_shapefile(campsite_shapefile, merged_shapefile)
            create_campsite_polygons(campsite_shapefile, polygon_shapefile)
            append_corgrid_points_to_shapefile(closest_survey.points_path, merged_shapefile)
            points_to_raster(gdal_warp.replace('gdalwarp', 'gdal_grid'), merged_shapefile, 'z', raster_path, cell_size, buffered_extent)
            clip_raster(gdal_warp, raster_path, clipped_path, polygon_shapefile, '')

        log.info(f'Binned analysis on site {site.site_code5} with {len(site.surveys)} surveys.')


def create_points_shapefile_from_campsite_shapefile(campsite_shapefile: str, merged_points: str) -> None:
    """
    Create a point ShapeFile from the campsite polyline ShapeFile vertices
    """

    # Open the campsite polyline ShapeFile
    input_ds = ogr.Open(campsite_shapefile)
    if input_ds is None:
        raise ValueError(f'Could not open campsite ShapeFile {campsite_shapefile}')
    input_layer = input_ds.GetLayerByIndex(0)
    input_spatial_ref = input_layer.GetSpatialRef()

   # Create a new point ShapeFile to contain both the survey points from textfile
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    output_ds = shp_driver.CreateDataSource(merged_points)
    output_layer = output_ds.CreateLayer(os.path.splitext(os.path.basename(merged_points))[0], geom_type=ogr.wkbPoint, srs=input_spatial_ref)
    output_layer.CreateField(ogr.FieldDefn('z', ogr.OFTReal))

    for feature in input_layer:
        polyline_geom = feature.GetGeometryRef().Clone()
        # Loop over all vertices in this campsite polyline
        for idx in range(polyline_geom.GetPointCount()):
            # Write the point to the merged point ShapeFile
            x, y, z = polyline_geom.GetPoint(idx)
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint(x, y)
            feature = ogr.Feature(output_layer.GetLayerDefn())
            feature.SetGeometry(point)
            feature.SetField('z', z)
            output_layer.CreateFeature(feature)
            feature = None

    input_ds = None
    output_ds = None


def get_buffered_campsite_extent(campsite_shapefile: str, cell_size: float) -> Tuple[float, float, float, float]:
    """
    Get the extent of the campsite ShapeFile
    """

    # Open the campsite polyline ShapeFile
    input_ds = ogr.Open(campsite_shapefile)
    if input_ds is None:
        raise ValueError(f'Could not open campsite ShapeFile {campsite_shapefile}')
    input_layer = input_ds.GetLayerByIndex(0)
    raw_extent = input_layer.GetExtent()

    buffered_extent = [
        math.floor(raw_extent[0] - raw_extent[0] % cell_size - cell_size),
        math.ceil(raw_extent[1] + raw_extent[1] % cell_size + cell_size),
        math.floor(raw_extent[2] - raw_extent[2] % cell_size - cell_size),
        math.ceil(raw_extent[3] + raw_extent[3] % cell_size + cell_size)
    ]

    return buffered_extent


def create_campsite_polygons(campsite_lines: str, polygon_shapefile) -> None:
    """
    Create a polygon ShapeFile from the campsite polyline ShapeFile
    """

    # Open the campsite polyline ShapeFile
    input_ds = ogr.Open(campsite_lines)
    if input_ds is None:
        raise ValueError(f'Could not open campsite ShapeFile {campsite_lines}')
    input_layer = input_ds.GetLayerByIndex(0)
    input_spatial_ref = input_layer.GetSpatialRef()
    lines_extent = input_layer.GetExtent()

    # Create a new polygon ShapeFile to contain the campsite polygons
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    polygon_ds = shp_driver.CreateDataSource(polygon_shapefile)
    polygon_layer = polygon_ds.CreateLayer(os.path.splitext(os.path.basename(polygon_shapefile))[0], geom_type=ogr.wkbPolygon, srs=input_spatial_ref)
    polygon_layer.CreateField(ogr.FieldDefn('Site', ogr.OFTString))

    # Add the vertices of the campsite polyline to the output layer
    for feature in input_layer:
        polyline_geom = feature.GetGeometryRef().Clone()

        # Create a linear ring for this campsite polygon
        linear_ring = ogr.Geometry(ogr.wkbLinearRing)

        # Loop over all vertices in this campsite polyline
        for idx in range(polyline_geom.GetPointCount()):
            x, y, __z = polyline_geom.GetPoint(idx)
            linear_ring.AddPoint(x, y)

        # Write this feature to the polygon ShapeFile
        linear_ring.CloseRings()
        polygon_geom = ogr.Geometry(ogr.wkbPolygon)
        polygon_geom.AddGeometry(linear_ring)
        polygon_geom.CloseRings()
        polygon_feature = ogr.Feature(polygon_layer.GetLayerDefn())
        polygon_feature.SetGeometry(polygon_geom)
        polygon_layer.CreateFeature(polygon_feature)
        polygon_feature = None

    input_ds = None
    polygon_ds = None


def append_corgrid_points_to_shapefile(corgrids_path: str, merged_shapefile: str) -> None:
    """
    Append the points from the corgrids text file to the merged point ShapeFile
    """

    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    output_ds = shp_driver.Open(merged_shapefile, update=True)
    output_layer = output_ds.GetLayerByIndex(0)

    # Loop over the rows in corgrids text file and add them to the merged point ShapeFile
    with open(corgrids_path, 'r', encoding='utf8') as corgrids_file:
        reader = csv.reader(corgrids_file, delimiter=' ')
        for row in reader:
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint(float(row[CORGRIDS_X_COL]), float(row[CORGRIDS_Y_COL]))
            feature = ogr.Feature(output_layer.GetLayerDefn())
            feature.SetGeometry(point)
            feature.SetField('z', float(row[CORGRIDS_Z_COL]))
            output_layer.CreateFeature(feature)
            feature = None

    output_ds = None


def get_campsite_surveys(site_folder: str) -> Dict[str, str]:
    """
    Get the surveys for the site
    """

    surveys = {}

    if not os.path.isdir(site_folder):
        return surveys

    for file in os.listdir(site_folder):
        if file.endswith('.shp'):
            input_shapefile = os.path.join(site_folder, file)
            match = file_name_pattern.match(os.path.basename(input_shapefile))
            if match:
                site_name = match.group('site_name')
                survey_date = match.group('survey_date')
                surveys[survey_date] = input_shapefile
            else:
                raise ValueError(f'Could not parse site name and survey date from file name {input_shapefile}')

    return surveys
