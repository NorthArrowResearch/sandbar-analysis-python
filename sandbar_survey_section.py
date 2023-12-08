"""
Class deifiing an individual sandbar survey section
"""


class SandbarSurveySection:
    """
    Class deifiing an individual sandbar survey section
    """

    def __init__(self, section_id, section_type_id, section_type: str):
        self.section_id = section_id
        self.section_type_id = section_type_id
        self.section_type = section_type
        self.raster_path = ""
        self.ignore = False
