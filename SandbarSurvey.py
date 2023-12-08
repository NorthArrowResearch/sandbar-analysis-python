"""
Class defining an individual sandbar survey
"""
from typing import Dict
import os
from SandbarSurveySection import SandbarSurveySection


class SandbarSurvey:
    """
    Class defining an individual sandbar survey
    """

    def __init__(self, survey_id, survey_date, points_path: str, is_analysis: bool, is_min_surface: bool):

        self.survey_id = survey_id
        self.survey_date = survey_date
        self.points_path = points_path
        self.vrt_file_path = ""  # populated by generateVRTFile method
        self.dem_path = ""  # populated by SandbarSite.GenerateDEMRasters
        # Whether this survey will be incorporated into the analysis
        self.is_analysis = is_analysis
        # Whether this survey will be incorporated into the minimum surface
        self.is_min_surface = is_min_surface

        # dictionary of section types that are part of this survey. Index is SectionTypeID
        self.surveyed_sections: Dict[int, SandbarSurveySection] = {}

    # def get_points_layer_name(self):
    #     """
    #     Return the layer name for the txt Points file. This should
    #     be the base file name of the txt file. Note that GDAL expects
    #     this string as ASCII and not unicode.
    #     """
    #     return os.path.splitext(os.path.basename(self.points_path))[0].encode('ascii', 'ignore')


def get_file_insensitive(path: str) -> str or None:
    """
    Determin the filename in a case-insensitive manner
    """

    directory, filename = os.path.split(path)
    directory, filename = (directory or '.'), filename.lower()
    for f in os.listdir(directory):
        newpath = os.path.join(directory, f)
        if os.path.isfile(newpath) and f.lower() == filename:
            return newpath

    return None


# def isfile_insensitive(path: str) -> bool:
#     """
#     Return true if the file exists in a case-insensitive manner
#     """
#     return getfile_insensitive(path) is not None
