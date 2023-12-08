"""
Build rasters from the CSV files
"""
from typing import Dict
import os.path
from logger import Logger
from SandbarSite import SandbarSite


def raster_preparation(
        sites: Dict[int, SandbarSite],
        analysis_folder: str,
        csv_cell_size: float,
        raster_cell_size: float,
        resample_method: str,
        epsg: int,
        reuse_rasters: bool,
        gdal_warp: str,
        comp_extent_shp: str) -> None:
    """
    Build rasters from the CSV files
    :param sites: Dictionary of all SandbarSite objects to be processed.
    :param analysis_folder: The path to the output folder
    :param csv_cell_size: The cell size of the CSV files (m)
    :param raster_cell_size: The cell size of the output rasters (m)
    :param resample_method: The resampling method to use when resampling the CSV files to the raster cell size
    :param epsg: The spatial reference code of the output rasters
    :param reuse_rasters: If True, existing rasters will be used if they exist
    :param gdal_warp: The path to the GDAL Warp executable
    :param section_types: The list of section types to process
    :param comp_extent_shp: The path to the computation extent shapefile
    :return: None"""

    log = Logger('Raster Prep')

    for site in sites.values():

        log.info(f'Site {site.site_code5}: Starting raster preparation...')

        # Verify that ALL text files for all surveys at this site are correctly formatted
        site.verify_txt_file_format()

        # Skip the site if it failed to find computational extent
        if site.ignore:
            continue

        # Make a subfolder in the output workspace for this survey
        survey_folder = os.path.join(analysis_folder, site.site_code5)
        if not os.path.exists(survey_folder):
            os.makedirs(survey_folder)

        assert os.path.exists(survey_folder), f'Failed to generate output folder for site {site.site_code5} at {survey_folder}'

        # Convert the TXT files to GeoTIFFs
        site.generate_dem_rasters(survey_folder, csv_cell_size, raster_cell_size, resample_method, epsg, reuse_rasters)
        site.clip_dem_rasters_to_sections(gdal_warp, survey_folder, comp_extent_shp, reuse_rasters)

        elevation8k = site.get_stage(8000)
        elevation25k = site.get_stage(25000)
        log.info(f'Site {site.site_code5}: Raster preparation is complete. Elevation at 8K is {elevation8k:.3f} and 25K is {elevation25k:.3f}')

    log.info(f'Raster preparation is complete for all {len(sites)} sites.')
