"""
Class defining a sandbar site
"""
import re
import os
from typing import Dict
from math import ceil, isnan
from datetime import datetime
from osgeo import ogr
import numpy as np
from Raster import Raster
from CSVLib import union_csv_extents
from logger import Logger
from ClipRaster import clip_raster
from SandbarSurvey import SandbarSurvey, get_file_insensitive
from SandbarSurveySection import SandbarSurveySection
from ComputationExtents import ComputationExtents, SITE_CODE_FIELD


class SandbarSite:
    """
    Class defining a sandbar site
    """

    def __init__(self,
                 site_code: str,
                 site_code5: str,
                 site_id,
                 discharge_a: float,
                 discharge_b: float,
                 discharge_c: float,
                 survey_folder: str):

        self.site_code = site_code
        self.site_code5 = site_code5
        self.site_id = site_id
        self.dis_coefficient_a = discharge_a
        self.dis_coefficient_b = discharge_b
        self.dis_coefficient_c = discharge_c
        self.inputs_survey_folder = survey_folder

        self.surveys: Dict[int, SandbarSurvey] = {}

        self.log = Logger("Sandbar Site")

        self.min_surface_path = ""  # populated by GenerateDEMRasters()
        self.min_surface = None

        # This is set to true if issues occur with the site and it can't be processed.
        self.ignore = False

        assert len(self.site_code5), f"The siteCode5 field '{site_code5}' is not five character in length."

    def get_stage(self, discharge: float) -> float:
        """
        Get the elevation at the specified discharge
        """

        if discharge is None:
            return None
        else:
            stage = self.dis_coefficient_a + \
                (self.dis_coefficient_b * discharge) + \
                (self.dis_coefficient_c * (discharge ** 2))
            return round(stage, 2)

    def get_min_analysis_stage(self, min_survey_elev: float, benchmark_discharge: float, analysis_increment: float) -> float:
        """
        Get the minimum analysis elevation for the calculation of sand volumes by
        increments. This is the closest value below the minimum survey elevation that is an
        even number of analysis increments (default is 0.1m) below the benchmark discharge
        (default 8000cfs)
        :param minSurveyElevation:
        :param benchmarkDischrage:
        :param analysisIncrement:
        :return:
        """

        if isnan(min_survey_elev):
            return None

        benchmark_stage = self.get_stage(benchmark_discharge)
        min_analysis_stage = benchmark_stage - ceil((benchmark_stage - min_survey_elev) / analysis_increment) * analysis_increment

        if isnan(min_analysis_stage):
            min_analysis_stage = None

        return min_analysis_stage

    def get_numeric_site_code(self):
        """
        Remove the leading zero padding and just return the numeric part of the
        site code (e.g.  0033L returns 33)
        :return:
        """
        the_match = re.search("[0]*([0-9]+)", self.site_code)
        return the_match.group(1) if the_match else None

    def generate_dem_rasters(self, survey_folder: str, csv_cell_size: float, cell_size: float, resample_method: str, epsg, reuse_rasters: bool) -> None:
        """
        :param dirSurveyFolder:
        :param fCSVCellSize:
        :param fCellSize:
        :param resampleMethod:
        :param theExtent:
        :param nEPSG:
        :param bReUseRasters:
        :return:
        """
        dem_folder = os.path.join(survey_folder, 'DEMs_Unclipped')
        if not os.path.exists(dem_folder):
            os.makedirs(dem_folder)

        # Make sure we are clean and typed
        csv_cell_size = float(csv_cell_size)
        cell_size = float(cell_size)

        # Retrieve the union of all TXT files for this site
        csv_files = [site_survey.points_path for site_survey in self.surveys.values()]
        the_extent = union_csv_extents(csv_files, cell_size=csv_cell_size, padding=10.0)
        self.log.info(f'Site {self.site_code5}: Unioned extent for {len(self.surveys)} surveys is {the_extent}')

        # Create a temporary template raster object we can resample
        temp_raster = Raster(proj=epsg, extent=the_extent, cellWidth=csv_cell_size)
        self.log.info(f'Site {self.site_code5}: Generating {len(self.surveys)} rasters with {temp_raster.cols} cols, {temp_raster.rows} rows at {cell_size}m cell size...')

        # Initialize the Minimum Surface Raster and give it an array of appropriate size
        self.min_surface_path = os.path.join(survey_folder, f'{self.site_code5}_min_surface.tif')
        self.min_surface = Raster(proj=epsg, extent=the_extent, cellWidth=cell_size)
        self.min_surface.set_array(np.nan * np.empty((self.min_surface.rows, self.min_surface.cols)))

        for survey in self.surveys.values():

            survey.dem_path = os.path.join(dem_folder, f'{self.site_code5}_{survey.survey_date:%Y%m%d}_dem.tif')

            # option to skip that speeds up debugging
            if os.path.isfile(survey.dem_path) and reuse_rasters:
                continue

            # Create a raster object that will represent the raw CSV
            dem_raster = Raster(proj=epsg, extent=the_extent, cellWidth=csv_cell_size)
            # This function will add the array in-place to the raster object
            dem_raster.load_dem_from_csv(survey.points_path, the_extent)

            if csv_cell_size != cell_size:
                # This method resamples the array and returns a new raster object
                new_dem = dem_raster.resample_dem(cell_size, resample_method)

                # Only incorporate the DEM into the analysis if required
                if survey.is_min_surface:
                    self.min_surface.merge_min_surface(new_dem)

                new_dem.write(survey.dem_path)
            else:
                # No resample necessary.

                # Only incorporate the DEM into the analysis if required
                if survey.is_min_surface:
                    self.min_surface.merge_min_surface(dem_raster)

                # Write the raw DEM object
                dem_raster.write(survey.dem_path)

            assert os.path.isfile(survey.dem_path), f'Failed to generate raster for site {self.site_code5} at {survey.dem_path}'

        # write the minimum surface raster to file
        if not reuse_rasters:
            assert self.min_surface is not None, f'Error generating minimum surface raster for site {self.site_code5}'
            self.min_surface.write(self.min_surface_path)

        assert os.path.isfile(self.min_surface_path), f'Minimum surface raster is missing for site {self.site_code5} at {self.min_surface_path}'

    def clip_dem_rasters_to_sections(self, gdal_warp: str, survey_folder: str, comp_extent: ComputationExtents, reuse_rasters: bool) -> None:
        """
        :param gdal_warp:
        :param dirSurveyFolder:
        :param dSections:
        :param theCompExtent:
        :param bResUseRasters:
        :return:
        """
        clipped_count = 0
        sections_count = 0

        for survey in self.surveys.values():
            for section in survey.surveyed_sections.values():

                # Only attempt to produce clipped raster if the computational extent exists
                if section.ignore:
                    continue

                sections_count += 1
                section_folder = section.section_type
                hypthon = section.section_type.find("-")
                if hypthon >= 0:
                    section_folder = section.section_type.replace(" ", "").replace("-", "_")

                dem_folder = os.path.join(survey_folder, "DEMs_Clipped", section_folder)
                if not os.path.exists(dem_folder):
                    os.makedirs(dem_folder)

                clipped_path = os.path.join(dem_folder, f'{self.site_code5}_{survey.survey_date:%Y%m%d}_{section_folder}_dem.tif')

                # option to skip that speeds up debugging
                if not (os.path.isfile(clipped_path) and reuse_rasters):

                    # This clause ensures that only the desired features are
                    # used for the clipping
                    where_clause = comp_extent.get_filter_clause(self.site_code5, section.section_type)
                    clip_raster(gdal_warp, survey.dem_path, clipped_path, comp_extent.full_path, where_clause)

                # Store the clipped raster in a dictionary on the survey date
                # objects
                section.raster_path = clipped_path
                clipped_count += 1

        self.log.info(f'Site {self.site_code5}: Clipped {clipped_count} rasters across {len(self.surveys)} surveys and {sections_count} sections defined')

    # def getElevationRange(self, dSections):
    #     """
    #     :param dSections:
    #     :return:
    #     """
    #     minElevation = -1.0
    #     maxElevation = 0.0
    #     for SurveyID, aDate in self.surveys.items():
    #         for nSectionTypeID, aSurveyedSection in aDate.surveyedSections.iteritems():

    #             dsRaster = gdal.Open(aSurveyedSection.rasterPath)
    #             rbRaster = dsRaster.GetRasterBand(1)
    #             rasStats = rbRaster.GetStatistics(0, 1)

    #             # The clipped DEMs might not have any data in the section
    #             # (channel or eddy)
    #             # in which case the stats returns all zeroes

    #             if rasStats[0] and rasStats[0] > 0:
    #                 if minElevation < 0:
    #                     minElevation = rasStats[0]
    #                 else:
    #                     minElevation = min(minElevation, rasStats[0])

    #             if rasStats[1] and rasStats[1] > 0:
    #                 maxElevation = max(maxElevation, rasStats[1])

    #             rb = None
    #             dsRaster = None

    #     assert minElevation > 500, "The minimum elevation ({0}) is too low.".format(
    #         minElevation)
    #     assert maxElevation >= minElevation, "The maximum elevation ({0}) is below the minimum elevation ({1}).".format(
    #         maxElevation, minElevation)
    #     self.log.info("Site {0} elevation range (across {1} surveys) is {2}".format(
    #         self.site_code5, len(self.surveys), (minElevation, maxElevation)))
    #     return (minElevation, maxElevation)

    def verify_txt_file_format(self):
        """
        Verify that the text files for all surveys at this site are correctly formatted
        """

        for survey_date in self.surveys.values():
            # Opeen the text file and verify that it has the correct number of space-separated floating point values
            with open(survey_date.points_path, 'r', encoding='utf8') as f:
                the_match = re.match("^([0-9.]+\s){3}([0-9.]+)\s*$", f.readline())
                if not the_match:
                    self.log.warning(f'Site {self.site_code5}: The {survey_date.survey_date.strftime("%Y-%m-%d")} survey has an invalid text file format. Skipping loading surveys. This site will not be processed. {survey_date.points_path}')

                    # Any one survey fails then the minimum surface could be incorrect. Abort this site.
                    self.ignore = True
                    return False

        # If got to here then all surveys validated
        return True


def load_sandbar_data(top_level_folder: str, xml_sites) -> Dict[int, SandbarSite]:
    """
    :param dirTopoFolder: The folder under which all the sandbar site topo folders exist. Typically ends with 'cordgrids'
    :param xmlSites: XML Element representing the Sites collection in the input XML file
    :return: Dictionary of sandbar sites to be processed. Key is SiteID, value is SandbarSite object

    Note that the sandbar site ASCII grids are currently found using the 4 digit site identifiers. This is how
    GCMRC currently stores them. e.g. ...\corgrids\003Lcorgrids But the goal is to improve this structure
    and enforce all sandbar data to be stored using 5 digit identifiers. The code below will need changing
    when this change is made.
    """

    log = Logger("Load Sandbars")

    sites: Dict[int, SandbarSite] = {}

    survey_count = 0
    analysis_count = 0
    min_surface_count = 0

    for site_tag in xml_sites.iterfind("Site"):
        all_surveys_present = True
        site_code4 = site_tag.attrib["code4"]
        survey_folder = os.path.join(top_level_folder, site_code4 + "corgrids")
        if os.path.isdir(survey_folder):
            sandbar_site = SandbarSite(site_code4, site_tag.attrib["code5"], int(site_tag.attrib["id"]), float(
                site_tag.attrib["stagedisa"]), float(site_tag.attrib["stagedisb"]), float(site_tag.attrib["stagedisc"]), survey_folder)

            # Add the site to the main dictionary of sandbar sites
            sites[int(site_tag.attrib["id"])] = sandbar_site

            # Load all the child surveys for this site
            for survey_tag in site_tag.iterfind("Surveys//Survey"):

                survey_date = datetime.strptime(survey_tag.attrib["date"], "%Y-%m-%d")

                # Get the path to the ASCII points TXT file. The actual files have mixed case.
                points_path = os.path.join(sandbar_site.inputs_survey_folder, f'{sandbar_site.get_numeric_site_code()}_{survey_date:%y%m%d}_grid.txt')

                # The actual files sometimes have mixed case. Get the correct version
                points_path_corrected = get_file_insensitive(points_path)

                if points_path_corrected:
                    survey_count += 1
                    survey_id = int(survey_tag.attrib["id"])
                    is_analysis = survey_tag.attrib["analysis"].lower() == 'true'
                    is_min_surface = survey_tag.attrib["minimum"].lower() == 'true'

                    analysis_count += 1 if is_analysis is True else 0
                    min_surface_count += 1 if is_min_surface is True else 0

                    sandbar_survey = SandbarSurvey(survey_id, survey_date, points_path_corrected, is_analysis, is_min_surface)
                    sandbar_site.surveys[survey_id] = sandbar_survey

                    # Load all the child sections that were collected during this survey
                    for section_tag in survey_tag.iterfind("Sections//Section"):

                        section_id = int(section_tag.attrib["id"])
                        section_type_id = int(section_tag.attrib["sectiontypeid"])
                        sandbar_survey.surveyed_sections[section_type_id] = SandbarSurveySection(
                            section_id, section_type_id, section_tag.attrib["sectiontype"])

                else:
                    all_surveys_present = False
                    log.warning(f'Missing txt file for site {site_code4} at {points_path}')

            if not all_surveys_present:
                log.warning(f'One or more survey txt files missing for site {site_code4}. This site will not be processed.')

        else:
            log.warning(f'Missing folder for site {site_code4} at {survey_folder}. This site will not be processed.')

    log.info(f'{len(sites)} sandbar sites loaded from input XML.')
    log.info(f'{survey_count} total surveys loaded from the input XML. {analysis_count} for analysis and {min_surface_count} for minimum surface.')

    return sites


def validate_site_codes(comp_extent: ComputationExtents, sites: Dict[int, SandbarSite]) -> None:
    """
    Validates that at least one feature for each site can be found
    Pass in a list SandbarSite objects.
    :param lSites:
    :return:
    """

    log = Logger('Validate Site Codes')

    driver = ogr.GetDriverByName('ESRI Shapefile')
    # 0 means read-only. 1 means writeable.
    data_source = driver.Open(comp_extent.full_path, 0)
    layer = data_source.GetLayer()

    for site in sites.values():
        layer.SetAttributeFilter(f"{SITE_CODE_FIELD} = '{site.site_code5}'")
        feature_count = layer.GetFeatureCount()
        missing_sections = {}

        if feature_count >= 1:
            # Loop over all surveys and ensure that each section also occurs in the ShapeFile
            for survey_date in site.surveys.values():
                for section in survey_date.surveyed_sections.values():

                    layer.SetAttributeFilter(comp_extent.get_filter_clause(site.site_code5, section.section_type))
                    feature_count = layer.GetFeatureCount()

                    if feature_count < 1:
                        section.ignore = True
                        missing_sections[section.section_type] = "missing"

            # Now report just once for any missing sections for this site
            for section_type in missing_sections:
                log.warning(f"Site {site.site_code5} missing polygon feature for section type '{section_type}'. This section will not be processed for any surveys at this site.")
        else:
            site.ignore = True
            log.warning(f'Site {site.site_code5} missing polygon feature(s) in computational extent ShapeFile. This site will not be processed.')

    log.info(f'Computation extents ShapeFile confirmed to contain at least one polygon for all {len(sites)} sandbar site(s) loaded.')


# def get_raster_txt_path(top_level_folder: str, input_ascii_grids: str, site: SandbarSite, survey_date):
#     """

#     :param dirTopLevelFolder:
#     :param dirInputASCIIGrids:
#     :param aSite:
#     :param dtSurveyDate:
#     :return:
#     """
#     txtPath = os.path.join(top_level_folder, input_ascii_grids, site.siteCode + "corgrids", '{site.getNumericSiteCode()}_{survey_date:%y%m%d}_grid.txt')
#     casePath = ""  # getfile_insensitive(txtPath)

#     if casePath and os.path.isfile(casePath):
#         return casePath
#     else:
#         return None
