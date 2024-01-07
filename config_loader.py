'''
Load the configuration from the input.xml file
'''
import os
import xml.etree.ElementTree as ET


def load_config(xml_file: str) -> dict:
    '''
    Load the configuration from the input.xml file
    '''

    config = {}
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # The analysis folder is the same location as the input.xml
    config['AnalysisFolder'] = os.path.dirname(xml_file)

    meta = root.find('MetaData')
    # Just put the whole meta into the config object
    config['MetaData'] = meta

    tags = root.find('Outputs')
    for the_tag in tags:
        config[the_tag.tag] = the_tag.text

    tags = root.find('Inputs')
    # For inputs and outputs create a dictionary
    for the_tag in tags:
        if the_tag.tag == 'Sites' \
                or the_tag.tag == 'SectionTypes' \
                or the_tag.tag == 'AnalysisBins' \
                or the_tag.tag == 'CampsiteBins':

            config[the_tag.tag] = the_tag

        elif the_tag.tag == 'CSVCellSize' \
                or the_tag.tag == 'RasterCellSize' \
                or the_tag.tag == 'ElevationIncrement' \
                or the_tag.tag == 'ElevationBenchmark':

            config[the_tag.tag] = float(the_tag.text)

        elif the_tag.tag == 'ReUseRasters':
            config['ReUseRasters'] = the_tag.text.upper() == 'TRUE'

        else:
            config[the_tag.tag] = the_tag.text

    return config
