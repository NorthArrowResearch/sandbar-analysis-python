"""
GCMRC Sandbar Processing Script
"""
import os
import sys
import argparse
from logger import Logger

from analysis_bin import load_analysis_bins
from computation_extents import ComputationExtents
from sandbar_site import load_sandbar_data, validate_site_codes
from incremental_analysis import run_incremental_analysis
from binned_analysis import run_binned_analysis
from campsite_analysis import run_campsite_analysis
from raster_preparation import raster_preparation

from config_loader import load_config

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

    # Load a dictionary of SandbarSites and their surveys from the workbench database
    analysis_bins = load_analysis_bins(conf['AnalysisBins'])
    campsite_bins = load_analysis_bins(conf['CampsiteBins'])
    sites = load_sandbar_data(conf['TopLevelFolder'], conf['Sites'])

    # Load the ShapeFile containing computational extent polygons for sandbar sites
    # Validate all sites have polygon extent features in this ShapeFile.
    comp_extent = ComputationExtents(conf['CompExtentShpPath'], conf['srsEPSG'])
    validate_site_codes(comp_extent, sites)

    incremental = 'IncrementalResults' in conf and conf['IncrementalResults'] is not None
    binned = 'BinnedResults' in conf and conf['BinnedResults'] is not None
    campsite = 'CampsiteResults' in conf and conf['CampsiteResults'] is not None

    if incremental is True or binned is True:
        # Create the DEM rasters and then clip them to the sandbar sections
        raster_preparation(sites, conf['AnalysisFolder'], conf['CSVCellSize'], conf['RasterCellSize'],
                           conf['ResampleMethod'], conf['srsEPSG'], conf['ReUseRasters'], conf['GDALWarp'],
                           comp_extent)

    # Incremental Analysis
    if incremental is True:
        inc_results_path = os.path.join(conf['AnalysisFolder'], conf['IncrementalResults'])
        run_incremental_analysis(sites, conf['ElevationBenchmark'], conf['ElevationIncrement'], conf['RasterCellSize'], inc_results_path)

    # Binned Analysis
    if binned is True:
        bin_results_path = os.path.join(conf['AnalysisFolder'], conf['BinnedResults'])
        run_binned_analysis(sites, analysis_bins, conf['RasterCellSize'], bin_results_path)

    # Campsite Analysis
    if campsite is True:
        campsite_results_path = os.path.join(conf['AnalysisFolder'], conf['CampsiteResults'])
        run_campsite_analysis(
            conf['CampsiteShpPath'],
            sites,
            conf['AnalysisFolder'],
            campsite_bins,
            conf['RasterCellSize'],
            campsite_results_path,
            conf['GDALWarp'],
            conf['ReUseRasters'])

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
        sys.exit(0)
    except AssertionError as e:
        log.error('Assertion Error', e)
        sys.exit(1)
    except Exception as e:
        log.error(f'Unexpected error: {sys.exc_info()[0]}', e)
        sys.exit(1)

