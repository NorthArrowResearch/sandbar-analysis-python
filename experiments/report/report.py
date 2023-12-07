import argparse
import sqlite3
import os, json

def resultViewer(workbenchDB):

    conn = sqlite3.connect(workbenchDB)
    c = conn.cursor()

    metadata = {
        149: 'Raster',
        148: 'TIN'
    }
    binnedData= {}
    for runID, runTypeName in metadata.iteritems():

        c.execute('SELECT SiteCode5, SS.Title, B.Title, R.SurveyDAte, R.Area, R.Volume' \
                  + ' FROM vwBinnedResults R INNER JOIN SandbarSites S ON R.SiteID = S.SiteID' \
                  + ' INNER JOIN LookupListItems SS ON R.SectionTypeID = SS.ItemID' \
                  + ' INNER JOIN AnalysisBins B ON R.BinID = B.BinID' \
                  + ' WHERE R.RunID = ? ORDER BY R.SiteId, R.SectionID,R.SurveyDate', [runID])

        for aRow in c.fetchall():

            sectionType = aRow[1]
            if sectionType not in binnedData:
                binnedData[sectionType] = {}

            siteName = aRow[0]
            if siteName not in binnedData[sectionType]:
                binnedData[sectionType][siteName] = {}

            bin = aRow[2]
            if bin not in binnedData[sectionType][siteName]:
                binnedData[sectionType][siteName][bin] = {}

            theDate = aRow[3]
            if theDate not in binnedData[sectionType][siteName][bin]:
                binnedData[sectionType][siteName][bin][theDate] = {}

            if runTypeName not in binnedData[sectionType][siteName][bin][theDate]:
                binnedData[sectionType][siteName][bin][theDate][runTypeName] = {}

                binnedData[sectionType][siteName][bin][theDate][runTypeName]['Area'] = aRow[4]
                binnedData[sectionType][siteName][bin][theDate][runTypeName]['Volume'] = aRow[5]

    output1 = {}
    output1['meta'] = metadata
    output1['data'] = binnedData
    with open('binned.json', 'w') as f:
        f.write(json.dumps(output1, ensure_ascii=False))

    increData = {}
    for runID, runTypeName in metadata.iteritems():
        c.execute('SELECT SiteCode5, SS.Title, R.SurveyDAte, R.Elevation, R.Area, R.Volume' \
                  + ' FROM vwIncrementalResults R INNER JOIN SandbarSites S ON R.SiteID = S.SiteID' \
                  + ' INNER JOIN LookupListItems SS ON R.SectionTypeID = SS.ItemID' \
                  + ' WHERE R.RunID = ? ORDER BY R.SiteId, R.SectionID,R.SurveyDate', [runID])

        for aRow in c.fetchall():

            sectionType = aRow[1]
            if sectionType not in increData:
                increData[sectionType] = {}

            siteName = aRow[0]
            if siteName not in increData[sectionType]:
                increData[sectionType][siteName] = {}

            bin = "incremental"
            if bin not in increData[sectionType][siteName]:
                increData[sectionType][siteName][bin] = {}

            theDate = aRow[2]
            if theDate not in increData[sectionType][siteName][bin]:
                increData[sectionType][siteName][bin][theDate] = {}

            elevation = aRow[3]
            if elevation not in increData[sectionType][siteName][bin][theDate]:
                increData[sectionType][siteName][bin][theDate][elevation] = {}

            if runTypeName not in increData[sectionType][siteName][bin][theDate][elevation]:
                increData[sectionType][siteName][bin][theDate][elevation][runTypeName] = {}

            increData[sectionType][siteName][bin][theDate][elevation][runTypeName]['Area'] = aRow[4]
            increData[sectionType][siteName][bin][theDate][elevation][runTypeName]['Volume'] = aRow[5]

    output2 = {}
    output2['meta'] = metadata
    output2['data'] = increData
    with open('incremental.json', 'w') as f:
        f.write(json.dumps(output2, ensure_ascii=False))

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('database', help = 'Path to SQLite database.', type = str)
    args = parser.parse_args()

    resultViewer(args.database)