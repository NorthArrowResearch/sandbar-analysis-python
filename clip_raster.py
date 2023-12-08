"""
Clip a raster using filtered features from a ShapeFile
This is used for clipping the DEM rasters to the computation extent polygons
"""
import os
from subprocess import call, PIPE
from raster import delete_raster
from logger import Logger


def clip_raster(gdal_warp_path: str, in_raster: str, out_raster: str, shape_file: str, where_clause: str) -> None:
    """
    :param gdal_warp_path: The path to the GDAL Warp executable
    :param in_raster: The path to the input raster
    :param out_raster: The path to the output raster
    :param shape_file: The path to the shapefile to use for clipping
    :param where_clause: Feature filter for selecting which features to use for clipping
    """

    log = Logger('Clip Raster')

    assert os.path.isfile(gdal_warp_path), f'Missing GDAL Warp executable at {gdal_warp_path}'
    assert os.path.isfile(in_raster), f'Missing clipping operation input at {in_raster}'
    assert os.path.isfile(shape_file), f'Missing clipping operation input ShapeFile at {shape_file}'

    # Make sure the rasters get removed before they get re-made
    delete_raster(out_raster)

    # Reset the where parameter to an empty string if no where clause is provided
    # TODO: This is giving us 64-bit rasters for some reason and a weird nodata value with nan as well. We're probably losing precision somewhere
    where_param = f"-cwhere \"{where_clause}\"" if len(where_clause) > 0 else ''

    gdal_args = f' -cutline {shape_file} {where_param} {in_raster} {out_raster}'
    log.debug('RUNNING GdalWarp: ' + gdal_warp_path + gdal_args)

    return_val = call(gdal_warp_path + gdal_args, stdout=PIPE, shell=True)

    assert return_val == 0, f'Error clipping raster. Input raster {in_raster}. Output raster {out_raster}. ShapeFile {shape_file}'
