# This script is intended to scrape the historical sandbar analysis results from text files.
# The goal is to take the results produced by GCMRC and get them into the SQLite database used
# by the sandbar workbench.
#
# This script works on the folder hierarchy that contains the binvol text files. These binvol
# files contain both the incremental results at 10cm increments, as well as the summary rows 
# described the binned results. The four types of data rows in these files look like:
#
# 047r,19900929,above25k,1836.98834552,1862.71741558,1747.22169061
# 047r,19950428,minto8K(818.48),18936.1992569,19803.8273157,66504.8143088
# 047r,19910727,8kto25k,6298.94478924,6348.34642599,8338.19948344
# 047r,19910727,above834.38,7794.0067583,7874.68673376,9924.80022137
#
# This is a temporary, experimental script and not part of the main sandbar processing script. 
# To make it do certain tasks, different SQL operations need to be uncommented below.
#########################################################################################################

import os
import sqlite3
import re
from os import path
from datetime import datetime
from TempFunctions import InsertSandbarSurveys
import csv

#########################################################################################################
# Input configuration

# This is the folder under which all the result csv files exist. This script searches for csv
# files recursively so it will find all CSV files under this folder. Note that in the GCMRC 
# data structure the next folders under this are One_Sandbar_With_Bath_Test,
# One_Sandbar_WithOut_Bath_Text and Two_Bar_With_Bath_Text
topLevelFolder = "D:/GCMRC/PHYSICAL/Sandbars/sandbar_process_4-14-16/binvol_inputs"

# SQLite database where results will be inserted
workbenchDB = "D:/Code/sandbar-analysis/Workbench/Database/workbench.sqlite"

# The ModelRuns.RunID that must already be in the database and ready to receive results
RunID = 1

# The dictionary that helps look up analysis bins from the binvol files. These are matched
# against the first data row in the binvol files. e.g.
# 047r,19900929,above25k,1836.98834552,1862.71741558,1747.22169061
dBinsStr = { "minto8K" : 1, "8kto25k" : 2, "above25k" : 3}

#########################################################################################################
# Load all the sites into a dictionary keyed by their 4 character site code

dSitesStr = {}
conn = sqlite3.connect(workbenchDB)
c = conn.cursor()
c.execute("SELECT SiteCode, SiteID FROM SandbarSites WHERE SiteCode IS NOT NULL")
for aRow in c.fetchall():
    dSitesStr[aRow[0].lower()] = aRow[1]

#########################################################################################################
# Load all the surveys into a dictionary keyed by surveyID and value tuple of siteID and date
dSurveys = {}
conn = sqlite3.connect(workbenchDB)
c = conn.cursor()
c.execute("SELECT SurveyID, SiteID, SurveyDate FROM SandbarSurveys")
for aRow in c.fetchall():
    date_object =  datetime.strptime(aRow[2], '%Y-%m-%d %H:%M:%S')
    dSurveys[aRow[0]] = (aRow[1], date_object)

#########################################################################################################
# Scrape the binvol CSV files into a list of their full path
lFiles = []
nTotalFiles =0
for (dirpath, dirnames, filenames) in os.walk(topLevelFolder):
    nTotalFiles += len(filenames)
    for aFile in filenames:
        thePair = os.path.splitext(aFile)
        if thePair[1].lower() == ".txt":
            lFiles.append(os.path.join(dirpath, aFile))

print "Total files = {0}, TXT files in list = {1}".format(nTotalFiles, len(lFiles))

dMissingSurveys = {}
nBinnedRecords = 0
nIncrementalRecords = 0
nCSVlines = 0

#########################################################################################################
# Delete any results for this model run (sanity check that it's also manual
# c.execute("DELETE FROM ModelResultsIncremental WHERE (RunID = ?)", [RunID])
# c.execute("DELETE FROM ModelResultsBinned WHERE (RunID = ?)", [RunID])

for aFile in lFiles:
    theMatch = re.search("binvol_(eddy|chan)([0-9,a-z]*)_([0-9,a-z]*)_([0-9]{8}).txt", aFile.lower(), re.IGNORECASE)

    # Use the folder that the binvol file exists in to determine whether this file represents:
    #     channel
    #    single eddy site
    #     separation eddy at multiple eddy site
    #    reattachment eddy at multiple eddy site
    #
    if "Two_Bar_With_Bath_Text" in aFile:
        if "chan" in aFile:
            sSectionType = "Channel"
            nSectionType = 9
        elif "reattachment" in aFile:
            sSectionType = "Eddy - re"
            nSectionType = 14
        elif "separation" in aFile:
            sSectionType = "Eddy - se"
            nSectionType = 13
        else:
            assert False, "no section found in two bar site {0}".format(aFile)
    else:
        if "eddy" in aFile:
            sSectionType = "Eddy - si"
            nSectionType = 10
        elif "chan" in aFile:
            sSectionType = "Channel"
            nSectionType = 9
        else:
            assert False, "no section found in two bar site {0}".format(aFile)
    
    # Retrieve the other required attributes from the file name
    sAnalysisBin = theMatch.group(2)
    sSite = theMatch.group(3).lower()
    theDate = theMatch.group(4)
    objDate = datetime.strptime(theDate, '%Y%m%d')

    # lookup the **4** character site code and get the database site ID
    nSite = dSitesStr[sSite]

    # look up the survey ID within the site
    nSurvey = 0
    for nID, tSurvey in dSurveys.iteritems():
        if (nSite == tSurvey[0]) and (tSurvey[1] == objDate):
            nSurvey = nID

    # track any missing surveys
    if nSurvey == 0:
        if not sSite.upper() in dMissingSurveys:
            dMissingSurveys[sSite.upper()] = []
        dMissingSurveys[sSite.upper()].append(objDate.strftime("%Y-%m-%d 00:00:00"))

    # Uncomment this line and stop the script here to insert any surveys
    # that are missing from the database. Once there are no missing surveys then comment
    # out these lines and re-run the script.
    # c.execute("INSERT INTO SandbarSections2 (SurveyID, SectionTypeID) VALUES (?, ?)", [nSurvey, nSectionType])
    # break

    # Look up the section (channel, eddy, eddy separation, eddy reattachment) that this file represents
    c.execute("SELECT SectionID FROM SandbarSections WHERE SurveyID = ? AND SectionTypeID = ?", [nSurvey, nSectionType])
    aRow = c.fetchone()
    if aRow:
        nSection = aRow[0]
    else:
        # Insert section for this survey
        print "Failed to find section for site {0} in file {1}".format(sSite, aFile)
        #c.execute("INSERT INTO SandbarSections (SurveyID, SectionTypeID) VALUES (?, ?)", [nSurvey, nSectionType])
        #nSection = c.lastrowid

    assert nSection > 0, "failed to retrieve section type {0}".format(aFile)

    # Open the binvol file and process each row.
    # Note the use of a dictionary reader so that the code can refer to column names.
    # This also "hides" the header row so that the code doesn't need to skip it.
    # Each row is used. If the row represents a summary of a bin (below 8k, 8-25k or above 25k)
    # then the row is inserted into ModelResultsBinned. If it represents a 10cm
    # (Plane_Height column is above835.38 etc) then it is inserted into ModelResultsIncremental.

    with open(aFile, 'rb') as csvfile:
        csvReader = csv.DictReader(csvfile)
        for row in csvReader:
            nCSVlines += 1

            # both types of results require the numerical fields
            area = float(row["Area_2D"])
            vol = float(row["Volume"])
            area3D = float(row["Area_3D"])

            # binned results can be found by looking up their name in the dictionary
            # Annoyingly below 8k bin results also include the min elevation and therefore
            # require slightly special treatment
            if row["Plane_Height"].lower() in dBinsStr or "minto8k" in row["Plane_Height"].lower():
                if  row["Plane_Height"].lower() in dBinsStr:
                    binID = dBinsStr[row["Plane_Height"].lower()]
                else:
                    binID = 1

                # this is a summary row describing a bin
                c.execute("INSERT INTO ModelResultsBinned (RunID, SectionID, BinID, Area, Volume, Area3D) VALUES (?, ?, ?, ?, ?, ?)", [RunID, nSection, binID, area, vol, area3D])
                nBinnedRecords += 1
            
            else:
                #print row["Plane_Height"]
                # this is an incremental row describe area/vol above an elevation
                elevMatch = re.search("above([0-9.]*)", row["Plane_Height"])
                Elevation = float(elevMatch.group(1))
                #print "run {0}, section {1}, elevation {2}, area {3}, volume {4}".format(RunID, nSection, Elevation, area, vol)
                #c.execute("INSERT INTO ModelResultsIncremental (RunID, SectionID, Elevation, Area, Volume, Area3D) VALUES (?, ?, ?, ?, ?, ?)", [RunID, nSection, Elevation, area, vol, area3D])
                nIncrementalRecords += 1

    #print "Section: {0} ({1}), flow: {2} ({3}), site: {4} ({5}), date: {6:%Y-%m-%d} ({7})".format(sSectionType, nSectionType, sAnalysisBin, nAnalysisBin, sSite, nSite, objDate, nSurvey)
# These next two lines are used to insert any surveys for which there are binvol files but no DB survey records

conn.commit()

print "Total CSV lines read {0}".format(nCSVlines) # across all files
print "Binned records inserted {0}".format(nBinnedRecords)
print "Incremental records inserted {0}".format(nIncrementalRecords)
print "Total records inserted {0}".format(nIncrementalRecords + nBinnedRecords)

#InsertSandbarSurveys(workbenchDB, dMissingSurveys)
assert len(dMissingSurveys) == 0, " There are {0} missing surveys!".format(len(dMissingSurveys))