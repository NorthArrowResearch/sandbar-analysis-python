"""
Clip a raster using a shapefile and a where clause
"""
import os
from subprocess import call
import subprocess
from Raster import delete_raster
from logger import Logger


def clip_raster(gdal_warp_path: str, input_raster: str, output_raster: str, shape_file_path: str, where_clause: str) -> None:
    """
    Clip a raster using a shapefile and a where clause
    """

    log = Logger("Clip Raster")

    assert os.path.isfile(gdal_warp_path), f'Missing GDAL Warp executable at {gdal_warp_path}'
    assert os.path.isfile(input_raster), f'Missing clipping operation input at {input_raster}'
    assert os.path.isfile(shape_file_path), f'Missing clipping operation input ShapeFile at {shape_file_path}'

    # Make sure the rasters get removed before they get re-made
    delete_raster(output_raster)

    # Reset the where parameter to an empty string if no where clause is provided
    # TODO: This is giving us 64-bit rasters for some reason and a weird nodata value with nan as well. We're probably losing precision somewhere
    where_param = "-cwhere \"{where_clause}\"" if len(where_clause) > 0 else ''

    gdal_args = f' -cutline {shape_file_path} {where_param} {input_raster} {output_raster}'
    log.debug('RUNNING GdalWarp: ' + gdal_warp_path + gdal_args)

    return_val = call(gdal_warp_path + gdal_args, stdout=subprocess.PIPE, shell=True)

    assert return_val == 0, f'Error clipping raster. Input raster {input_raster}. Output raster {output_raster}. ShapeFile {shape_file_path}'
