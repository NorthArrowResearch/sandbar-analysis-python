"""
GCMRC Sandbar Processing Script
"""
import os
import sys
import argparse
from logger import Logger

from AnalysisBin import load_analysis_bins
from ComputationExtents import ComputationExtents
from SandbarSite import load_sandbar_data
from SectionTypes import load_section_types
from IncrementalAnalysis import run_incremental_analysis
from BinnedAnalysis import run_binned_analysis
from RasterPreparation import raster_preparation

from ConfigLoader import load_config

# Initialize logger.
log = Logger()

# if 'DEBUG' in os.environ:
#     import pydevd
#     pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True)


def main(config):
    """
    The main Sandbar processing routine
    """

    Logger('Initializing')

    # Load a dictionary of SandbarSites and their surveys from the workbench
    # database for the sites that need to be processed.
    section_types = load_section_types(config['SectionTypes'])
    analysis_bins = load_analysis_bins(config['AnalysisBins'])
    sites = load_sandbar_data(config['TopLevelFolder'], config['Sites'])

    # Load the ShapeFile containing computational extent polygons for sandbar sites
    # Validate all sites have polygon extent features in this ShapeFile.
    comp_extent_shp = ComputationExtents(config['CompExtentShpPath'], config['srsEPSG'])
    comp_extent_shp.validate_site_codes(sites)

    # Create the DEM rasters and then clip them to the sandbar sections
    raster_preparation(sites, config['AnalysisFolder'], config['CSVCellSize'], config['RasterCellSize'],
                       config['ResampleMethod'], config['srsEPSG'], config['ReUseRasters'], config['GDALWarp'],
                       section_types, comp_extent_shp)

    # prepare result file paths
    inc_results_path = os.path.join(config['AnalysisFolder'], config['IncrementalResults'])
    bin_results_path = os.path.join(config['AnalysisFolder'], config['BinnedResults'])

    # Run the analyses
    run_incremental_analysis(sites, config['ElevationBenchmark'], config['ElevationIncrement'], config['RasterCellSize'], inc_results_path)
    run_binned_analysis(sites, analysis_bins, config['RasterCellSize'], bin_results_path)

    log.info('Sandbar analysis process complete.')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('input_xml', help='Path to the input XML file.', type=str)
    parser.add_argument('--verbose', help='Get more information in your logs.', action='store_true', default=False)
    args = parser.parse_args()

    # Load the XML into a simple dictionary
    conf = load_config(args.input_xml)

    log = Logger('Program')
    log.setup(logRoot=conf['AnalysisFolder'], xmlFilePath=conf['Log'], verbose=args.verbose, config=conf)

    log.debug('Config file', conf)

    try:
        # Now kick things off
        log.info(f'Starting Sandbar script with: input_xml: {args.input_xml}')
        main(conf)
    except AssertionError as e:
        log.error('Assertion Error', e)
        sys.exit(0)
    except Exception as e:
        log.error(f'Unexpected error: {sys.exc_info()[0]}', e)
        sys.exit(0)
