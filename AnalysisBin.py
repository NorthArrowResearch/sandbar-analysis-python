'''
Analysis bins represent different discharges that are used to calculate the
sandbar analysis. These discharges correspond to different elevations.
'''
from typing import Dict
from logger import Logger


class AnalysisBin:
    '''
    Analysis bins represent different discharges that are used to calculate the
    sandbar analysis. These discharges correspond to different elevations.
    '''

    def __init__(self, bin_id, title, lower_discharge, upper_discharge):
        self.bin_id = bin_id
        self.title = title
        self.lower_discharge = lower_discharge
        self.upper_discharge = upper_discharge

    def __repr__(self):
        return f'Analysis Bin: {self.bin_id} - {self.title} lower: {self.lower_discharge} upper: {self.upper_discharge}'


def load_analysis_bins(analysis_bin_element) -> Dict[int, AnalysisBin]:
    '''
    Load analysis bins from input XML file
    '''

    analysis_bins = {}
    log = Logger('Load Bins')

    # Note that lower or upper Discharge may be NULL
    for bin_tag in analysis_bin_element.iterfind('Bin'):

        lower_discharge = float(bin_tag.attrib['lower']) if len(bin_tag.attrib['lower']) > 0 else None
        upper_discharge = float(bin_tag.attrib['upper']) if len(bin_tag.attrib['upper']) > 0 else None

        analysis_bins[int(bin_tag.attrib['id'])] = AnalysisBin(
            int(bin_tag.attrib['id']),
            bin_tag.attrib['title'],
            lower_discharge,
            upper_discharge)

    assert len(analysis_bins) > 0, f'{len(analysis_bins)} analysis bins loaded from the input XML file.'

    log.info(f'{len(analysis_bins)} analysis bins loaded from the input XML file.')
    log.debug('Analysis Bins:', analysis_bins, 'original Element:', analysis_bin_element)

    return analysis_bins
