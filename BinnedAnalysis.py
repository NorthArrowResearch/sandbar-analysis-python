"""
Run the binned analysis
"""

import csv
from typing import Dict, List
from RasterAnalysis import get_vol_and_area
from Raster import Raster
from logger import Logger
from SandbarSite import SandbarSite
from AnalysisBin import AnalysisBin


def run_binned_analysis(
        sites: Dict[int, SandbarSite],
        analysis_bins: Dict[int, AnalysisBin],
        cell_size: float,
        result_file_path: str) -> None:
    """
    Run the binned analysis
    """

    model_results: List[tuple] = []
    log = Logger("Binned Analysis")
    log.info("Starting binned analysis...")

    for site_id, site in sites.items():

        # Only process sites that have computation extent polygons
        if site.Ignore:
            continue

        log.info(f'Binned analysis on site {site.siteCode5} with {len(site.surveyDates)} surveys.')

        # Loop over all the surveys for the site and perform the binned (<8k,
        # 8-25k, > 25k) analysis
        for survey_id, survey_date in site.survey_dates.items():

            # Only proceed with this survey if it is flagged to be apart of the analysis.
            if survey_date.IsAnalysis:

                for section in survey_date.surveyedSections.values():

                    # Only process sections that have computation extent polygons
                    if section.Ignore:
                        continue

                    survey_raster = Raster(filepath=section.rasterPath)

                    for bin_id, bin in analysis_bins.items():

                        # Get the lower and upper elevations for the discharge.  Either
                        # could be None
                        lower_elev = site.getStage(bin.lowerDischarge)
                        upper_elev = site.getStage(bin.upperDischarge)

                        area_vol = get_vol_and_area(
                            survey_raster.array, site.MinimumSurface.array, lower_elev, upper_elev, cell_size, site.MinimumSurfacePath)

                        model_results.append((site_id, site.site_code5, survey_id, survey_date.survey_date.strftime("%Y-%m-%d"),
                                             section.section_type_id, section.section_type,
                                             section.section_id, bin_id, bin.title, area_vol[0], area_vol[1], area_vol[2], area_vol[3], area_vol[4], area_vol[5]))

    # Write the binned results to CSV
    log.info(f'Binned analysis complete. Writing {len(model_results)} results to {result_file_path}')

    with open(result_file_path, 'wb') as out:
        csv_out = csv.writer(out)
        csv_out.writerow(['siteid', 'sitecode', 'surveyid', 'surveydate', 'sectiontypeid', 'sectiontype', 'sectionid',
                         'binid', 'bin', 'area', 'volume', 'surveyvol', 'minsurfarea', 'minsurfvol', 'netminsurfvol'])

        for row in model_results:
            csv_out.writerow(row)
