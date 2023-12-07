import os
import re
import sqlite3
from datetime import datetime

# This file contains little utility functions needed
# during the construction of the Sandbar Analysis Script

# Retrieve the dates of sandbar surveys
def RetrieveSandbarSitesAndDates(dirDataFolder):
    
    nSurveyFiles = 0
    siteList = {}
    for (dirpath, dirnames, filenames) in os.walk(dirDataFolder):
        for aFileName in filenames:
            junkName, anExt = os.path.splitext(aFileName) 
            if anExt.lower() == ".txt":
                #siteCode = re.search("[0-9]{3}(L|R)", dirpath)
                siteCode = os.path.split(dirpath)[1]
                if siteCode.endswith("corgrids") or siteCode.startswith("m006"):
                    siteCode = siteCode[0:4]
                                        
                    theDate = re.search("_([0-9]{6})_grid.txt",aFileName.lower(), re.IGNORECASE)
                    if theDate:
                        if theDate.group(1)[0] == '9':
                            fullDate = '19' + theDate.group(1)[0:6]
                        else:
                            fullDate = '20' + theDate.group(1)[0:6]
                        date_object =  datetime.strptime(fullDate, '%Y%m%d')
                        
                        if not siteList.has_key(siteCode):
                            siteList[siteCode] = []

                        siteList[siteCode].append(date_object) # (siteCode, date_object))
                        nSurveyFiles +=1
                        # print "Site", siteCode, "and a file", aFileName, "theDate ", theDate, "Formatted ", date_object # , " folder ", dirpath
    # print siteList
    print len(siteList), " Sandbar sites found and ", nSurveyFiles, " survey files with valid dates."
    return siteList

def InsertSandbarSurveys(dbPath, sitesandDates):
    
    conn = sqlite3.connect(dbPath)
    c = conn.cursor()

    nSuccess = 0
    lMissingTrips = []
    lMissingSites = []
    nMissingSurveys = 0
    for aSiteCode in sitesandDates:

        c.execute("SELECT SiteID FROM SandbarSites WHERE siteCode = ?", [aSiteCode])
        siteCodes = c.fetchone()
        if siteCodes:
            siteID = siteCodes[0]

            for aSurveyDate in sitesandDates[aSiteCode]:
                # Get the trip ID
                c.execute("SELECT TripID FROM Trips WHERE TripDate <= ? ORDER BY TripDate DESC", [aSurveyDate])
                trips = c.fetchone()
                if trips:
                    tripID = trips[0]

                    c.execute("INSERT INTO SandbarSurveys (SiteID, TripID, SurveyDate, AddedBy, UpdatedBy) VALUES (?, ?, ?, 'pgb', 'pgb')", [siteID, tripID, aSurveyDate])
                    nSuccess +=1
                else:
                    lMissingTrips.append((aSiteCode, aSurveyDate))
        else:
            lMissingSites.append(aSiteCode)
            nMissingSurveys += len(sitesandDates[aSiteCode])

    if len(lMissingSites) > 0 or len(lMissingTrips) > 0:
        print "Error: Rolling back database operation."
        print "Successful survey count: ", nSuccess
        print "Missing site IDs: ", len(lMissingSites)
        print "Missing trip IDs:", len(lMissingTrips)
        print "Missing surveys:", nMissingSurveys

        print "Missing sites: ", lMissingSites
        print "Missing trips: ", lMissingTrips
        conn.rollback()
    else:
        conn.commit()
        print "Success: committing sandbar survey insert"
 
    conn.close()