"""
Class deifiing an individual sandbar survey section
"""
import sqlite3
from logger import Logger


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


def load_sandbar_survey_sections(workbench_db, sites):
    """
    Load the SanbarSurveySections
    :param WorkbenchDB:
    :param lSites:
    :return:
    """
    log = Logger('LoadSurveySections')
    conn = sqlite3.connect(workbench_db)

    try:
        c = conn.cursor()
        survey_sections = 0

        # Load all sections for all surveys and all sites
        c.execute("""
                  SELECT S.SiteID, S.SiteCode5, SS.SurveyID, SSS.SectionTypeID, SSS.SectionID, L.Title
                  FROM (((SandbarSites S INNER JOIN SandbarSurveys SS ON S.SiteID = SS.SiteID)
                    INNER JOIN SandbarSections SSS ON SS.SurveyID = SSS.SurveyID)
                    INNER JOIN LookupListItems L ON SSS.SectionTypeID = L.ItemID)
                  """)

        for row in c.fetchall():
            if row[0] in sites:
                if row[2] in sites[row[0]].surveyDates:
                    # The site and survey are loaded
                    assert not row[3] in sites[row[0]].surveyDates[row[2]].surveyedSections, \
                        f'The SurveyID {row[2]} for site {row[0]} ({row[1]}) contains duplicate survey sections with SectionTypeID {row[3]}'

                    sites[row[0]].surveyDates[row[2]].surveyedSections[row[3]] = SandbarSurveySection(row[4], row[3], row[5])
                    survey_sections += 1
    finally:
        conn.close()
        log.info(f'{survey_sections} sandbar survey sections loaded from the database.')
