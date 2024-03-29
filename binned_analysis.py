"""
Run the binned analysis
"""
import csv
from typing import Dict, List
from raster_analysis import get_vol_and_area
from raster import Raster
from logger import Logger
from sandbar_site import SandbarSite
from analysis_bin import AnalysisBin


def run_binned_analysis(
        sites: Dict[int, SandbarSite],
        analysis_bins: Dict[int, AnalysisBin],
        cell_size: float,
        result_file_path: str) -> None:
    """
    Run the binned analysis
    """

    model_results: List[tuple] = []
    log = Logger('Binned Analysis')
    log.info('Starting binned analysis...')

    for site_id, site in sites.items():

        # Only process sites that have computation extent polygons
        if site.ignore:
            continue

        log.info(f'Binned analysis on site {site.site_code5} with {len(site.surveys)} surveys.')

        # Loop over all the surveys for the site and perform the binned (<8k,
        # 8-25k, > 25k) analysis
        for survey_id, survey in site.surveys.items():

            # Only proceed with this survey if it is flagged to be apart of the analysis.
            if survey.is_analysis is True:

                for section in survey.surveyed_sections.values():

                    # Only process sections that have computation extent polygons
                    if section.ignore:
                        continue

                    survey_raster = Raster(filepath=section.raster_path)

                    for anal_bin in analysis_bins.values():

                        # Get the lower and upper elevations for the discharge. Either could be None
                        lower_elev = survey.get_stage(anal_bin.lower_discharge)
                        upper_elev = survey.get_stage(anal_bin.upper_discharge)

                        # Get volume and area between the surveyed surface and minimum surface
                        area_vol = get_vol_and_area(survey_raster.array, site.min_surface.array, lower_elev, upper_elev, cell_size)

                        # Get the volume and area between the maximum surface and minimum surface
                        # This is only needed for the 8-25k and above 25k bins
                        maxmin_area_vol = (None, None, None, None, None, None)
                        if lower_elev is not None:
                            maxmin_area_vol = get_vol_and_area(site.max_surface.array, site.min_surface.array, lower_elev, upper_elev, cell_size)

                        model_results.append((site_id, site.site_code5, survey_id, survey.survey_date.strftime('%Y-%m-%d'),
                                             section.section_type_id, section.section_type, section.section_id,
                                             anal_bin.bin_id, anal_bin.title,
                                             area_vol[0], area_vol[1], area_vol[2], area_vol[3], area_vol[4], area_vol[5],
                                             maxmin_area_vol[0], maxmin_area_vol[1]))

    # Write the binned results to CSV
    log.info(f'Binned analysis complete. Writing {len(model_results)} results to {result_file_path}')

    with open(result_file_path, 'w', encoding='utf8') as out:
        csv_out = csv.writer(out)
        csv_out.writerow(['siteid', 'sitecode', 'surveyid', 'surveydate', 'sectiontypeid', 'sectiontype', 'sectionid', 'binid', 'bin',
                          'area', 'volume', 'surveyvol', 'minsurfarea', 'minsurfvol', 'netminsurfvol',
                          'maxminsurfarea', 'maxminsurfvol'])

        for row in model_results:
            csv_out.writerow(row)
