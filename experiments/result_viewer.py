import argparse
import sqlite3

def resultViewer(workbenchDB):

    conn = sqlite3.connect(workbenchDB)
    c = conn.cursor()

    data = {}
    for runID, runTypeName in {147: 'Python', 148: 'TIN'}.iteritems():

        c.execute('SELECT SiteCode5, SS.Title, B.Title, R.SurveyDAte, R.Area, R.Volume' \
                  + ' FROM vwBinnedResults R INNER JOIN SandbarSites S ON R.SiteID = S.SiteID' \
                  + ' INNER JOIN LookupListItems SS ON R.SectionTypeID = SS.ItemID' \
                  + ' INNER JOIN AnalysisBins B ON R.BinID = B.BinID' \
                  + ' WHERE R.RunID = ? ORDER BY R.SiteId, R.SectionID,R.SurveyDate', [runID])

        for aRow in c.fetchall():

            sectionType = aRow[1]
            if sectionType not in data:
                data[sectionType] = {}

            siteName = aRow[0]
            if siteName not in data[sectionType]:
                data[sectionType][siteName] = {}

            bin = aRow[2]
            if bin not in data[sectionType][siteName]:
                data[sectionType][siteName][bin] = {}

            theDate = aRow[3]
            if theDate not in data[sectionType][siteName][bin]:
                data[sectionType][siteName][bin][theDate] = {}

            if runTypeName not in data[sectionType][siteName][bin][theDate]:
                data[sectionType][siteName][bin][theDate][runTypeName] = {}

            data[sectionType][siteName][bin][theDate][runTypeName]['Area'] = aRow[4]
            data[sectionType][siteName][bin][theDate][runTypeName]['Volume'] = aRow[5]


    print data

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('database', help = 'Path to SQLite database.', type = str)
    args = parser.parse_args()

    resultViewer(args.database)