import sqlite3
import csv
import datetime

resultfile = "D:/Temp/GCMRC/results_binned.csv"
workbenchDB = "D:/Code/sandbar-analysis/Workbench/Database/workbench.sqlite"

modelAddedBy = "Philip Bailey"
modelRunTitle = "Development Test Run by {0} on {1:%Y-%m-%d %H:%M}".format(modelAddedBy, datetime.datetime.now())
modelRunType = 11

# Open the database
conn = sqlite3.connect(workbenchDB)
c = conn.cursor()

c.execute("INSERT INTO ModelRuns (Title, RunTypeID, AddedBy) VALUES (?, ?, ?)", [modelRunTitle, modelRunType, modelAddedBy])
nRunID = c.lastrowid

nRows = 0
with open(resultfile, 'rb') as csvfile:
	csvReader = csv.DictReader(csvfile)
	for csvRow in csvReader:
		c.execute("INSERT INTO ModelResultsBinned (RunID, SectionID, BinID, Area,Volume) VALUES (?, ?, ?, ?, ?)", [nRunID, csvRow["sectionid"], csvRow["binid"], csvRow["area"], csvRow["vol"] ])
		nRows += 1

conn.commit()
print "{0} records inserted into the database and associated with model run ID {1}".format(nRows, nRunID)
