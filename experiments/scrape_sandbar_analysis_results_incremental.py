import sqlite3
import csv
import datetime

resultfile = "D:/Temp/GCMRC/ModelRun_20170301_122321/results_incremental.csv"
workbenchDB = "D:/Code/sandbar-analysis/Workbench/Database/workbench.sqlite"

modelAddedBy = "Philip Bailey"
modelRunTitle = "Development Test Run by {0} on {1:%Y-%m-%d %H:%M}".format(modelAddedBy, datetime.datetime.now())
modelRunType = 11
modelRunInstallationGuid = "3acd5ec3-9fc7-42a9-b2c3-e7a6cfd20667"

# Open the database
conn = sqlite3.connect(workbenchDB)
c = conn.cursor()

# Load the Section IDs for each survey and SectionTypeID
'''
c.execute("SELECT SurveyID, SectionID, SectionID FROM SandbarSections ORDER BY SurveyID, SectionID")
dSections = {}
for aRow in c.fetchall():
    if not aRow[0] in dSections:
        dSections[aRow[0]] = {}
    dSections[aRow[0]][aRow[1]] = aRow[2]
'''

c.execute("INSERT INTO ModelRuns (Title, RunTypeID, AddedBy, UpdatedBy, RunBy, InstallationGuid) VALUES (?, ?, ?, ?, ?, ?)", [modelRunTitle, modelRunType, modelAddedBy, modelAddedBy, modelAddedBy, modelRunInstallationGuid])
nRunID = c.lastrowid

sectionID = 0
nRows = 0
nMissingSurveys = 0
nMissingSections = 0
with open(resultfile, 'rb') as csvfile:
    csvReader = csv.DictReader(csvfile)
    for csvRow in csvReader:
        c.execute("INSERT INTO ModelResultsIncremental (RunID, SectionID, Elevation, Area, Volume) VALUES (?, ?, ?, ?, ?)", [nRunID, csvRow["sectionid"], csvRow["elevation"], csvRow["area"], csvRow["volume"] ])
        nRows += 1

conn.commit()
print "{0} records inserted into the database and associated with model run ID {1}".format(nRows, nRunID)
print "{0} missing surveys and {1} missing sections encountered.".format(nMissingSurveys, nMissingSections)