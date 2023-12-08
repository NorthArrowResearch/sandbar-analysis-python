"""
GCMRC Sandbar Processing Script
"""
import os
import sys
import argparse
from logger import Logger

from AnalysisBin import load_analysis_bins
from ComputationExtents import ComputationExtents
from SandbarSite import load_sandbar_data, validate_site_codes
# from SectionTypes import load_section_types
from IncrementalAnalysis import run_incremental_analysis
from BinnedAnalysis import run_binned_analysis
from RasterPreparation import raster_preparation

from ConfigLoader import load_config

# Initialize logger.
log = Logger()

# if 'DEBUG' in os.environ:
#     import pydevd
#     pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True)


def main(conf: dict) -> None:
    """
    The main Sandbar processing routine
    """

    Logger('Initializing')

    # Load a dictionary of SandbarSites and their surveys from the workbench
    # database for the sites that need to be processed.
    # section_types = load_section_types(config['SectionTypes'])
    analysis_bins = load_analysis_bins(conf['AnalysisBins'])
    sites = load_sandbar_data(conf['TopLevelFolder'], conf['Sites'])

    # Load the ShapeFile containing computational extent polygons for sandbar sites
    # Validate all sites have polygon extent features in this ShapeFile.
    comp_extent = ComputationExtents(conf['CompExtentShpPath'], conf['srsEPSG'])
    validate_site_codes(comp_extent, sites)

    # Create the DEM rasters and then clip them to the sandbar sections
    raster_preparation(sites, conf['AnalysisFolder'], conf['CSVCellSize'], conf['RasterCellSize'],
                       conf['ResampleMethod'], conf['srsEPSG'], conf['ReUseRasters'], conf['GDALWarp'],
                       comp_extent)

    # prepare result file paths
    inc_results_path = os.path.join(conf['AnalysisFolder'], conf['IncrementalResults'])
    bin_results_path = os.path.join(conf['AnalysisFolder'], conf['BinnedResults'])

    # Run the analyses
    run_incremental_analysis(sites, conf['ElevationBenchmark'], conf['ElevationIncrement'], conf['RasterCellSize'], inc_results_path)
    run_binned_analysis(sites, analysis_bins, conf['RasterCellSize'], bin_results_path)

    log.info('Sandbar analysis process complete.')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('input_xml', help='Path to the input XML file.', type=str)
    parser.add_argument('--verbose', help='Get more information in your logs.', action='store_true', default=False)
    args = parser.parse_args()

    # Load the XML into a simple dictionary
    config = load_config(args.input_xml)

    log = Logger('Program')
    log.setup(logRoot=config['AnalysisFolder'], xmlFilePath=config['Log'], verbose=args.verbose, config=config)

    log.debug('Config file', config)

    try:
        # Now kick things off
        log.info(f'Starting Sandbar script with: input_xml: {args.input_xml}')
        main(config)
    except AssertionError as e:
        log.error('Assertion Error', e)
        sys.exit(0)
    except Exception as e:
        log.error(f'Unexpected error: {sys.exc_info()[0]}', e)
        sys.exit(0)
