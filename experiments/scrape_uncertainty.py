from datetime import datetime
import sqlite3
import csv
import re

csvFilePath = "D:/Temp/2016_07_29_gcmrc_data_error_lookup.csv"
workbenchDB = "D:/Code/sandbar-analysis/Workbench/Database/workbench.sqlite"
dBins = {'minto8k' : 1, '8kto25k' : 2, 'above25k' : 3}



# Open the database
conn = sqlite3.connect(workbenchDB)
c = conn.cursor()

dMissingSurveys = []
cIncorrectTrip = []

dUncertainties = {}
dDifferentUncertainties = []

lInsertSections = []

# Open the CSV file and loop over each line
with open(csvFilePath, 'rb') as csvfile:
	csvReader = csv.DictReader(csvfile)
	for csvRow in csvReader:

		# Retrieve the site
		c.execute("SELECT SiteID FROM SandbarSites WHERE SiteCode = ?", [csvRow["Site"].upper()])
		dbRow = c.fetchone()
		assert dbRow, "unable to find site {0}".format(csvRow["Site"])
		nSiteID = dbRow[0]

		dtSurvey = datetime.strptime(csvRow["SurveyDate"], '%m/%d/%Y')
		c.execute("SELECT SurveyID FROM SandbarSurveys WHERE SiteID = ? AND SurveyDate = ?", [nSiteID, dtSurvey])
		dbRow = c.fetchone()
		if not dbRow:
			dMissingSurveys.append( (csvRow["Site"], nSiteID, dtSurvey) )
		assert dbRow, "unable to find survey for site {0} ({1}) and survey date {2:%Y-%m-%d}".format(csvRow["Site"], nSiteID, dtSurvey)
		nSurveyID = dbRow[0]

		# dtTrip = datetime.strptime(csvRow["TripDate"], '%m/%d/%Y')
		# c.execute("SELECT T.TripID FROM Trips AS T INNER JOIN SandbarSurveys AS S ON (T.TripID = S.TripID) WHERE S.SiteID = ? AND S.SurveyID = ? AND T.TripID = ?", [nSiteID, nSurveyID, dtTrip.strftime("%Y-%m-%d")])
		# dbRow = c.fetchone()
		# cIncorrectTrip.append( (csvRow["Site"], nSiteID, dtSurvey, nSurveyID, dtTrip) )

		if "minto8k" in csvRow["Bin"]:
			binID = 1
		elif "8kto25k" in csvRow["Bin"]:
			binID = 2
		elif "above25k" in csvRow["Bin"]:
			binID = 3
		else:
			raise "Unknown bin {0}".format(csvRow["Bin"])


		fUncertainty = float(csvRow["Uncertainty"])

		# find out where this uncertainty applies to a single channel section or all the eddy sections
		nSectionTypeID = 0
		theMatch = re.search("(chan|eddy)", csvRow["Bin"], re.IGNORECASE)
		if "chan" in theMatch.group(1).lower():
			sWhere = "="
			nSectionTypeID = 9
		else:
			sWhere = "<>"
			nSectionTypeID = 10

		# Select all the surveyed sections for this site during this survey
		c.execute("SELECT SectionID FROM SandbarSections WHERE (SurveyID = ?) AND (SectionTypeID {0} 9)".format(sWhere), [nSurveyID])
		lSections = c.fetchall()
		if len(lSections) < 1:
			print "no section found for site {0} ({1}) survey {2} ({3}) and type {4}".format(csvRow["Site"], nSiteID, csvRow["SurveyDate"], nSurveyID, theMatch.group(1))
			c.execute("INSERT INTO SandbarSections (SurveyID, SectionTypeID) VALUES (?, ?)", [nSurveyID, nSectionTypeID])

		#for aRow in lSections:
			#c.execute("INSERT INTO SandbarSectionUncertainties (SectionID, BinID, Uncertainty, AddedBy, UpdatedBy) VALUES ({0}, {1}, {2}, 'pgb', 'pgb')".format(aRow[0], binID, fUncertainty))

		# sKey = "{0}_{1}_{2}".format(nSiteID, nSurveyID, sSection)
		# if sKey in dUncertainties:
		# 	if dUncertainties[sKey] != fUncertainty:
		# 		dDifferentUncertainties.append("{0} {1} {2}".format(sKey, fUncertainty, dUncertainties[sKey]))
		# else:
		# 	dUncertainties[sKey] = fUncertainty

conn.commit()

print dMissingSurveys
print cIncorrectTrip
print dDifferentUncertainties