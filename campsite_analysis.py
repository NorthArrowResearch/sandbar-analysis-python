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
from raster import Raster
from raster_analysis import get_bin_area
from logger import Logger
from sandbar_site import SandbarSite
from analysis_bin import AnalysisBin
from clip_raster import clip_raster
from points_to_raster import points_to_raster
import numpy as np

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
    Run the binned campsite analysis
    """

    log = Logger('Campsite Analysis')
    log.info('Starting campsite analysis...')

    model_results: List[Tuple[int, int, str, int, float, float, float]] = []
    for site_id, site in sites.items():
        for survey_id, survey in site.surveys.items():

            # Find the most appropriate campsite survey for this sandbar survey
            campsite_shapefile = get_campsite_shapefile(campsite_parent_folder, site.site_code, survey.survey_date)

            if campsite_shapefile is None:
                # log.info(f'No campsite ShapeFile found for site {site.site_code5} and survey date {survey.survey_date.strftime("%Y-%m-%d")}')
                continue

            log.info(f'Campsite ShapeFile: {campsite_shapefile} for site {site.site_code5} and survey date {survey.survey_date.strftime("%Y-%m-%d")}')

            # Create a new folder for processing this campsite survey
            processing_folder = os.path.join(analysis_folder, site.site_code5, 'campsites', survey.survey_date.strftime('%Y%m%d'))
            merged_shapefile = os.path.join(processing_folder, 'merged_points.shp')
            polygon_shapefile = os.path.join(processing_folder, 'campsite_polygons.shp')
            raster_path = os.path.join(processing_folder, 'merged_dem.tif')
            clipped_path = os.path.join(processing_folder, 'clipped_dem.tif')

            if os.path.isfile(clipped_path):
                if reuse_rasters:
                    log.info(f'Reusing existing clipped campsite raster {clipped_path}')
                else:
                    log.info(f'Deleting existing campsite processing folder {processing_folder}')
                    os.system(f'rm -rf {processing_folder}')

            if not os.path.isdir(processing_folder):
                os.makedirs(processing_folder)

            # Determine the bounding rectangle of the campsite polygons, buffered outwards to the nearest metre
            buffered_extent = get_buffered_campsite_extent(campsite_shapefile, cell_size)

            # Create a new Shapefile containing the vertices of the campsite polylines
            create_points_from_campsite_polylines(campsite_shapefile, merged_shapefile)

            # Append to the ShapeFile the points from the sandbar survey corgrids text file
            append_corgrid_points(survey.points_path, merged_shapefile)

            # Create a raster from the merged points ShapeFile
            points_to_raster(gdal_warp.replace('gdalwarp', 'gdal_grid'), merged_shapefile, 'z', raster_path, cell_size, buffered_extent)

            # Create a polygon ShapeFile from the campsite polyline ShapeFile
            create_campsite_polygons(campsite_shapefile, polygon_shapefile)

            # Clip the raster to the campsite polygons
            clip_raster(gdal_warp, raster_path, clipped_path, polygon_shapefile, '')

            # Loop over the analysis bins and determine the campsite area between the elevations
            campsite_raster = Raster(filepath=clipped_path)
            for bin_id, anal_bin in analysis_bins.items():
                # Get the lower and upper elevations for the discharge. Either could be None
                lower_elev = survey.get_stage(anal_bin.lower_discharge)
                upper_elev = survey.get_stage(anal_bin.upper_discharge)

                masked_array = np.ma.array(campsite_raster.array)
                area = get_bin_area(masked_array, lower_elev, upper_elev, cell_size)
                model_results.append((site_id, survey_id, os.path.basename(campsite_shapefile), bin_id, anal_bin.lower_discharge, anal_bin.upper_discharge, area))

    # Write the results to the output file
    with open(result_file_path, 'w', newline='', encoding='utf8') as result_file:
        writer = csv.writer(result_file, delimiter=',')
        writer.writerow(['SiteID', 'SurveyID', 'CampsiteShapeFile', 'BinID', 'LowerDischarge', 'UpperDischarge', 'Area'])
        for result in model_results:
            writer.writerow(result)

    log.info(f'Campsite binned analysis is complete. Results at {result_file_path}')


def get_campsite_shapefile(campsite_folder: str, site_code: str, survey_date: datetime) -> str:
    """
    Get the path to the campsite ShapeFile for the site and survey date
    """

    campsite_folder = os.path.join(campsite_folder, f'{site_code}camps')
    if not os.path.isdir(campsite_folder):
        return None

    for file in os.listdir(campsite_folder):
        if file.endswith('.shp'):
            campsite_shapefile = os.path.join(campsite_folder, file)
            match = file_name_pattern.match(os.path.basename(file))
            if match:
                __site_name = match.group('site_name')
                campsite_date_str = match.group('survey_date')
                campsite_date = datetime.strptime(campsite_date_str, '%Y%m%d')
                if survey_date.year == campsite_date.year:
                    return campsite_shapefile
            else:
                raise ValueError(f'Could not parse site name and survey date from campsite file {campsite_shapefile}')

    # No campsite ShapeFile found for this site and survey date
    return None


def create_points_from_campsite_polylines(campsite_shapefile: str, merged_points: str) -> None:
    """
    Create a point ShapeFile from the campsite polyline ShapeFile vertices
    """

    log = Logger('Campsite Analysis')

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

    # Keep track of the number of valid campsite polylines
    valid_polylines = 0
    for feature in input_layer:
        polyline_geom = feature.GetGeometryRef().Clone()

        if polyline_geom is None or polyline_geom.IsEmpty():
            log.warning(f'Empty campsite polyline for feature {feature.GetFID()} in campsite ShapeFile {campsite_shapefile}')
            continue

        if not polyline_geom.IsValid():
            log.warning(f'Invalid campsite polyline for feature {feature.GetFID()} in campsite ShapeFile {campsite_shapefile}')
            continue

        valid_polylines += 1

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

    # Campsite analysis can't continue for this site if there are no valid campsite polylines
    if valid_polylines < 1:
        raise ValueError(f'No valid campsite polylines found in campsite ShapeFile {campsite_shapefile}')


def get_buffered_campsite_extent(campsite_shapefile: str, cell_size: float) -> Tuple[float, float, float, float]:
    """
    Get the extent of the campsite ShapeFile.
    This opens the campsite polyline ShapeFile, gets the bounding rectangle.
    It then buffers the rectangle to the nearest cell size and then rounds to the nearest metre.
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
    This builds a new ShapeFile with each campsite polyline turned into
    a polygon
    """

    log = Logger('Campsite Analysis')

    # Open the campsite polyline ShapeFile
    input_ds = ogr.Open(campsite_lines)
    if input_ds is None:
        raise ValueError(f'Could not open campsite ShapeFile {campsite_lines}')
    input_layer = input_ds.GetLayerByIndex(0)
    input_spatial_ref = input_layer.GetSpatialRef()

    # Create a new polygon ShapeFile to contain the campsite polygons
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    polygon_ds = shp_driver.CreateDataSource(polygon_shapefile)
    polygon_layer = polygon_ds.CreateLayer(os.path.splitext(os.path.basename(polygon_shapefile))[0], geom_type=ogr.wkbPolygon, srs=input_spatial_ref)
    polygon_layer.CreateField(ogr.FieldDefn('Site', ogr.OFTString))

    # Add the vertices of the campsite polyline to the output layer
    for feature in input_layer:
        polyline_geom = feature.GetGeometryRef().Clone()

        if polyline_geom is None or polyline_geom.IsEmpty():
            log.warning(f'Empty campsite polyline for feature {feature.GetFID()} in campsite ShapeFile {campsite_lines}')
            continue

        if not polyline_geom.IsValid():
            log.warning(f'Invalid campsite polyline for feature {feature.GetFID()} in campsite ShapeFile {campsite_lines}')
            continue

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

        if not polygon_geom.IsValid():
            log.error(f'Invalid campsite polygon for feature {feature.GetFID()} in campsite ShapeFile {campsite_lines}')
            # raise ValueError(f'Invalid campsite polygon for feature {feature.GetFID()} in campsite ShapeFile {campsite_lines}')
            continue

        polygon_feature = ogr.Feature(polygon_layer.GetLayerDefn())
        polygon_feature.SetGeometry(polygon_geom)
        polygon_layer.CreateFeature(polygon_feature)
        polygon_feature = None

    input_ds = None
    polygon_ds = None


def append_corgrid_points(corgrids_path: str, merged_shapefile: str) -> None:
    """
    Append the points from the corgrids text file to the merged point ShapeFile
    """

    if not os.path.isfile(merged_shapefile):
        raise ValueError(f'Could not find merged point ShapeFile {merged_shapefile}')

    if not os.path.isfile(corgrids_path):
        raise ValueError(f'Could not find corgrids text file {corgrids_path}')

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
