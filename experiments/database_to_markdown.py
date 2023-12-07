import argparse
import sqlite3

def databaseToMarkdown(databasePath, outputPath, includeAuditFields):
    """
    Outputs a markdown description of a SQLite database
    :param databasePath: Path to the SQLite database
    :param outputPath: Path to the output markdown file that is produced
    :return:

    If the SQLite database doesn't have the manually populated VersionDBTables
    and VersionDBColumns then the markdown just contains a list of tables
    and columns with their types. If the manually populated tables exist then
    the markdown incorporates the descriptions from these tables.
    """

    # Load the database table information
    conn = sqlite3.connect(databasePath)
    c = conn.cursor()

    databaseInfo = {}

    # Get the list of database tables from SQLite
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for aRow in c.fetchall():
        databaseInfo[aRow[0]] = {'Description' : '', 'Columns' : {}}

    # Get the list of columns for each table
    for tableName, tableInfo in databaseInfo.iteritems():
        c.execute("Pragma table_info({0})".format(tableName))

        colInfo = tableInfo['Columns']
        for aRow in c.fetchall():
            colInfo[aRow[1]] = {}
            colInfo[aRow[1]]['Description'] = ''

            notNull = ''
            if aRow[3] == 1:
                notNull = ', NN'

            pk = ''
            if aRow[5] == 1:
                pk = ', **PK**'

            colInfo[aRow[1]]['Info'] = '{0}{1}{2}'.format(aRow[2], notNull, pk)

    # Get the manually populate database table and column descriptions
    c.execute("SELECT TableName, T.Description, ColumnName, C.Description"
              " FROM VersionDBTables T LEFT JOIN VersionDBColumns C ON T.TableID = C.TableID"
              " ORDER BY TableName, ColumnName")

    for aRow in c.fetchall():
        tableName = aRow[0]

        if tableName not in databaseInfo:
            databaseInfo[tableName] = {}
            databaseInfo[tableName]['Columns'] = {}

        databaseInfo[tableName]['Description'] = aRow[1]

        colName = aRow[2]
        if colName:
            if colName not in databaseInfo[tableName]['Columns']:
                databaseInfo[tableName]['Columns'][colName] = {'Description' : '', 'Info' : ''}

            databaseInfo[tableName]['Columns'][colName]['Description'] = aRow[3]


    # Output the database info as markdown
    text_file = open(outputPath, 'wb')
    for tableName, tableInfo in databaseInfo.iteritems():
        text_file.write('## {0}\n\n'.format(tableName))
        text_file.write('{0}\n\n'.format(tableInfo['Description']))

        text_file.write('| Field | Info | Description |\n')
        text_file.write('| --- | --- | --- |\n')
        for colName, colInfo in tableInfo['Columns'].iteritems():

            # Skip audit fields if the script argument is false
            if includeAuditFields == 0 and colName in ['AddedOn', 'AddedBy', 'UpdatedOn', 'UpdatedBy']:
                continue

            if 'PK' in colInfo['Info']:
                colName = '**{0}**'.format(colName)

            text_file.write('| {0} | {1} | {2} |\n'.format(colName, colInfo['Info'], colInfo['Description']))

        text_file.write('\n')

    text_file.close()

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('database', help = 'Path to SQLite database.', type = str)
    parser.add_argument('output', help='Path output markdown file.', type=str)
    parser.add_argument('auditfields', help='Whether to include audit fields.', type=int)
    args = parser.parse_args()

    databaseToMarkdown(args.database, args.output, args.auditfields)