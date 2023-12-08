"""
Incremental sandbar analysis
"""
from typing import Dict
import csv
from RasterAnalysis import get_vol_and_area
from Raster import Raster
from logger import Logger
from SandbarSite import SandbarSite
from SandbarSurveySection import SandbarSurveySection


def run_incremental_analysis(sites: Dict[int, SandbarSite], elev_benchmark: float, elev_increment: float, cell_size: float, result_file_path: str) -> None:
    """
    Perform the incremental sandbar analysis on all sites in the dictionary.
    :param sites: Dictionary of all SandbarSite objects to be processed.
    :param elev_benchmark: The lower limit of the analysis (typically 8K discharge)
    :param elev_increment: Vertical increment at which to perform the analysis (default is 0.1m)
    :param cell_size: The raster cell size (m)
    :param result_file_path: The path to the output CSV file
    :return:
    """

    log = Logger("Inc. Analysis")
    log.info("Starting incremental analysis...")
    model_results = []

    for site in sites.values():

        # Only process sites that have computation extent polygons
        if site.ignore:
            continue

        log.info(f'Incremental analysis on site {site.site_code5} with {len(site.surveys)} surveys.')

        for survey in site.surveys.values():

            # Only proceed with this survey if it is flagged to be apart of the analysis.
            if survey.is_analysis is False:
                continue

            for section in survey.surveyed_sections.values():

                # Only process sections that have computation extent polygons
                if section.ignore:
                    continue

                log.debug(f'Incremental on site {site.site_code5}, survey {survey.survey_date.strftime("%Y-%m-%d")}, {section.section_type} {section.raster_path}')

                # Run the analysis on this section and get back a list of tuples (Elevation, Area, Volume)
                section_results = run_section(site, section, elev_benchmark, elev_increment, cell_size)

                if section_results is None:
                    # Nothing found
                    log.info("No section results found.")
                else:
                    # Append the results to the master list that will be written to the output CSV file
                    for (elevation, area, vol) in section_results:
                        model_results.append((site.site_id, site.site_code5, survey.survey_id,
                                              survey.survey_date.strftime('%Y-%m-%d'),
                                              section.section_type_id, section.section_type,
                                              section.section_id, f'{elevation:.2f}', area, vol))

    log.info(f'Incremental analysis complete. Writing {len(model_results)} results to {result_file_path}')

    with open(result_file_path, 'w', encoding='utf8') as out:
        csv_out = csv.writer(out)
        csv_out.writerow(['siteid', 'sitecode', 'surveyid', 'surveydate', 'sectiontypeid', 'section', 'sectionid', 'elevation', 'area', 'volume'])
        for row in model_results:
            csv_out.writerow(row)


def run_section(site: SandbarSite, section: SandbarSurveySection, elev_benchmark: float, elev_increment: float, cell_size: float) -> list:
    """
    Run the incremental analysis on a single section
    """

    # The results for this section will be a list of tuples (Elevation, Area, Volume)
    section_results = []

    # Open the clipped raster for this site, survey and section and get the minimum surveyed elevation in this section
    survey_raster = Raster(filepath=section.raster_path)
    analysis_elev = site.get_min_analysis_stage(survey_raster.min, elev_benchmark, elev_increment)

    if analysis_elev is None:
        # There is no survey data in this section
        return None

    # We do the diff once and then mask it later
    assert survey_raster.array.size == site.min_surface.array.size, 'The two arrays are not the same size!'

    while analysis_elev < survey_raster.max:
        area_vol = (-1.0, -1)
        area_vol = get_vol_and_area(survey_raster.array, site.min_surface.array, analysis_elev, None,
                                    cell_size, site.min_surface_path)

        if area_vol[0] > 0:
            section_results.append((analysis_elev, area_vol[0], area_vol[1]))

        analysis_elev += elev_increment

    return section_results
