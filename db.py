"""
Python DB API wrapper. Provides a DB API-compliant API that wraps real
underlying DB API drivers, simplifying some non-portable operations like
connect() and providing some new operations.

Currently, this package supports the following database types and drivers:

    db.DUMMY       Dummy database type; does nothing.
    db.MYSQL       MySQL, using the MySQLdb DB API module
    db.POSTGRESQL  PostgreSQL, using the psycopg2 DB API module
    db.SQL_SERVER  Microsoft SQL Server, using the pymssql DB API module
    db.ORACLE      Oracle, using the cx_Oracle DB API module
    db.DB2         Not yet supported

$Id$
"""

import dummydb

__all__ = ['DUMMY', 'MYSQL', 'POSTGRESQL', 'SQL_SERVER', 'ORACLE', 'DB2',
           'get_driver']

DUMMY      = "dummy"
MYSQL      = "mysql"
POSTGRESQL = "postgresql"
SQL_SERVER = "sqlserver"
ORACLE     = "oracle"
DB2        = "db2"

def get_driver(db_type):
    """
    Get the DB API object for the specific database type. Legal types are:

    db.DUMMY       Dummy database type; does nothing.
    db.MYSQL       MySQL, using the MySQLdb DB API module
    db.POSTGRESQL  PostgreSQL, using the psycopg2 DB API module
    db.SQL_SERVER  Microsoft SQL Server, using the pymssql DB API module
    db.ORACLE      Oracle, using the cx_Oracle DB API module
    db.DB2         Not yet supported
    """
    try:
        return TYPE_TO_CONS[db_type]()
    except KeyError:
        raise ValueError, "Unknown database type: %s" % db_type
    
class Error(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class Warning(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class Cursor(object):
    def __init__(self, cursor, wrapper):
        self.__cursor = cursor
        self.__wrapper = wrapper

    def close(self):
        dbi = self.__wrapper.get_import()
        try:
            return self.__cursor.close()
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def execute(self, statement, parameters=None):
        dbi = self.__wrapper.get_import()
        try:
            result = self.__cursor.execute(statement, parameters)
            self.rowcount = self.__cursor.rowcount
            self.description = self.__cursor.description
            return result
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def executemany(self, statement, *parameters):
        dbi = self.__wrapper.get_import()
        try:
            result = self.__cursor.executemany(statement, *parameters)
            self.rowcount = self.__cursor.rowcount
            self.description = self.__cursor.description
            return result
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def fetchone(self):
        dbi = self.__wrapper.get_import()
        try:
            return self.__cursor.fetchone()
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def fetchall(self):
        dbi = self.__wrapper.get_import()
        try:
            return self.__cursor.fetchall()
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def fetchmany(self, n):
        dbi = self.__wrapper.get_import()
        try:
            self.__cursor.fetchmany(n)
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def get_table_metadata(self, table):
        """
        Get the metadata for a table. Returns a list of tuples, one for
        each column. Each tuple consists of the following:

        (column_name, type_as_string, max_char_size, precision, scale, nullable)

        column_name     the name of the column
        type_as_string  the column type, as a string
        max_char_size   maximum size for a character field, or None
        precision       precision, for a numeric field, or None
        scale           scale, for a numeric field, or None
        nullable        True or False

        The data may come from the DB API's cursor.description field, or
        it may be richer, coming from a direct SELECT against database-specific
        tables.
        """
        # Default implementation
        dbi = self.__wrapper.get_import()
        try:
            return self.__wrapper.get_table_metadata(table, self.__cursor)
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def get_index_metadata(self, table):
        """
        Get the metadata for the indexes for a table. Returns a list of
        tuples, one for each index. Each tuple consists of the following:

        (index_name, [index_columns], description)

        index_keys is a list of column names
        description may be None

        Returns None if not supported in the underlying database
        """
        dbi = self.__wrapper.get_import()
        try:
            return self.__wrapper.get_index_metadata(table, self.__cursor)
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

class DB(object):
    def __init__(self, db, wrapper):
        self.__db = db
        self.__wrapper = wrapper
        dbi = wrapper.get_import()
        self.BINARY = dbi.BINARY
        self.NUMBER = dbi.NUMBER
        self.STRING = dbi.STRING
        self.DATETIME = dbi.DATETIME
        try:
            self.ROWID = dbi.ROWID
        except AttributeError:
            self.ROWID = self.NUMBER

    def cursor(self):
        dbi = self.__wrapper.get_import()
        try:
            return Cursor(self.__db.cursor(), self.__wrapper)
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def commit(self):
        dbi = self.__wrapper.get_import()
        try:
            self.__db.commit()
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def rollback(self):
        dbi = self.__wrapper.get_import()
        try:
            self.__db.rollback()
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def close(self):
        dbi = self.__wrapper.get_import()
        try:
            self.__db.close()
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

class Wrapper(object):

    def get_import(self):
        pass

    def connect(self,
                host="localhost",
                port=None,
                user="sa",
                password="",
                database="default"):
        pass

    def get_index_metadata(self, table, cursor):
        return None

    def get_table_metadata(self, table, cursor):
        """Default implementation"""
        dbi = self.get_import()
        cursor.execute('SELECT * FROM %s WHERE 1=0' % table)
        result = []
        for col in cursor.description:
            name = col[0]
            type = col[1]
            size = col[2]
            internal_size = col[3]
            precision = col[4]
            scale = col[5]
            nullable = col[6]

            if type == dbi.BINARY:
                stype = 'blob'
            elif type == dbi.DATETIME:
                stype = 'datetime'
            elif type == dbi.NUMBER:
                stype = 'numeric'
            elif type == dbi.STRING:
                sz = internal_size
                if sz == None:
                    sz = size
                elif sz <= 0:
                    sz = size

                if sz == 1:
                    stype = 'char'
                else:
                    stype = 'varchar'
                size = sz
            elif type == dbi.ROWID:
                stype = 'id'
            else:
                stype = 'unknown (type code=%s)' % str(type)

            result += [(name, stype, size, precision, scale, nullable)]

        return result

class MySQLWrapper(Wrapper):
    def get_import(self):
	import MySQLdb
        return MySQLdb

    def connect(self,
                host="localhost",
                port=None,
                user="sa",
                password="",
                database="default"):
        dbi = self.get_import()
        try:
            self.__db = dbi.connect(host=host, user=user, passwd=password,
                                    db=database)
            return DB(self.__db, self)
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def get_index_metadata(self, table, cursor):
        dbi = self.get_import()
        cursor.execute("SHOW INDEX FROM %s" % table)
        rs = cursor.fetchone()
        result = []
        columns = {}
        descr = {}
        while rs != None:
            name = rs[2]
            try:
                columns[name]
            except KeyError:
                columns[name] = []

            columns[name] += [rs[4]]
            if rs[1] or (name.lower() == "primary"):
                description = "Unique"
            else:
                description = "Non-unique"
            if rs[10] != None:
                description += ", %s index" % rs[10]
            descr[name] = description
            rs = cursor.fetchone()

        names = columns.keys()
        names.sort()
        for name in names:
            result += [(name, columns[name], descr[name])]

        return result

class SQLServerWrapper(Wrapper):
    def get_import(self):
	import pymssql
        return pymssql

    def connect(self,
                host="localhost",
                port=None,
                user="sa",
                password="",
                database="default"):
        dbi = self.get_import()
        try:
            if port == None:
                port = "1433"
            self.__db = dbi.connect(host='%s:%s' % (host, port),
                                    user=user,
                                    password=password,
                                    database=database)
            return DB(self.__db, self)
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def get_table_metadata(self, table, cursor):
        """Default implementation"""
        dbi = self.get_import()
        cursor.execute("SELECT column_name, data_type, " \
                       "character_maximum_length, numeric_precision, " \
                       "numeric_scale, is_nullable "\
                       "FROM information_schema.columns WHERE "\
                       "LOWER(table_name) = '%s'" % table)
        rs = cursor.fetchone()
        results = []
        while rs != None:
            is_nullable = False
            if rs[5] == 'YES':
                is_nullable = True
            results += [(rs[0], rs[1], rs[2], rs[3], rs[4], is_nullable)]
            rs = cursor.fetchone()
        return results

    def get_index_metadata(self, table, cursor):
        dbi = self.get_import()
        cursor.execute("EXEC sp_helpindex '%s'" % table)
        rs = cursor.fetchone()
        results_by_name = {}
        while rs != None:
            name = rs[0]
            description = rs[1]
            columns = rs[2].split(', ')
            results_by_name[name] = (name, columns, description)
            rs = cursor.fetchone()

        names = results_by_name.keys()
        names.sort()
        result = []
        for name in names:
            result += [results_by_name[name]]

        return result

class PostgreSQLWrapper(Wrapper):
    def get_import(self):
        import psycopg2
        return psycopg2

    def connect(self,
                host="localhost",
                port=None,
                user="sa",
                password="",
                database="default"):
        dbi = self.get_import()
        try:
            dsn = 'host=%s dbname=%s user=%s password=%s' %\
                  (host, database, user, password)
            self.__db = dbi.connect(dsn=dsn)
            return DB(self.__db, self)
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

    def get_index_metadata(self, table, cursor):
        dbi = self.get_import()
        # First, issue one query to get the list of indexes for the table.
        index_names = self.__get_index_names(table, cursor)

        # Now we need two more queries: One to get the columns in the
        # index and another to get descriptive information.
        results = []
        for name in index_names:
            columns = self.__get_index_columns(name, cursor)
            desc = self.__get_index_description(name, cursor)
            results += [(name, columns, desc)]

        return results

    def __get_index_names(self, table, cursor):
        # Adapted from the pgsql command "\d indexname", PostgreSQL 8.
        # (Invoking the pgsql command from -E shows the issued SQL.)

        sel = "SELECT n.nspname, c.relname as \"IndexName\", c2.relname " \
              "FROM pg_catalog.pg_class c " \
              "JOIN pg_catalog.pg_index i ON i.indexrelid = c.oid " \
              "JOIN pg_catalog.pg_class c2 ON i.indrelid = c2.oid " \
              "LEFT JOIN pg_catalog.pg_user u ON u.usesysid = c.relowner " \
              "LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace " \
              "WHERE c.relkind IN ('i','') " \
              "AND n.nspname NOT IN ('pg_catalog', 'pg_toast') " \
              "AND pg_catalog.pg_table_is_visible(c.oid) " \
              "AND c2.relname = '%s'" % table.lower()

        cursor.execute(sel)
        index_names = []
        rs = cursor.fetchone()
        while rs != None:
            index_names += [rs[1]]
            rs = cursor.fetchone()

        return index_names

    def __get_index_columns(self, index_name, cursor):
        # Adapted from the pgsql command "\d indexname", PostgreSQL 8.
        # (Invoking the pgsql command from -E shows the issued SQL.)

        sel = "SELECT a.attname, " \
              "pg_catalog.format_type(a.atttypid, a.atttypmod), " \
              "a.attnotnull " \
              "FROM pg_catalog.pg_attribute a, pg_catalog.pg_index i " \
              "WHERE a.attrelid in " \
              " (SELECT c.oid FROM pg_catalog.pg_class c " \
              "LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace " \
              " WHERE pg_catalog.pg_table_is_visible(c.oid) " \
              "AND c.relname ~ '^(%s)$') " \
              "AND a.attnum > 0 AND NOT a.attisdropped " \
              "AND a.attrelid = i.indexrelid " \
              "ORDER BY a.attnum" % index_name
        cursor.execute(sel)
        columns = []
        rs = cursor.fetchone()
        while rs != None:
            columns += [rs[0]]
            rs = cursor.fetchone()

        return columns

    def __get_index_description(self, index_name, cursor):
        sel = "SELECT i.indisunique, i.indisprimary, i.indisclustered, " \
              "a.amname, c2.relname, " \
              "pg_catalog.pg_get_expr(i.indpred, i.indrelid, true) " \
              "FROM pg_catalog.pg_index i, pg_catalog.pg_class c, " \
              "pg_catalog.pg_class c2, pg_catalog.pg_am a " \
              "WHERE i.indexrelid = c.oid AND c.relname ~ '^(%s)$' " \
              "AND c.relam = a.oid AND i.indrelid = c2.oid" % index_name
        cursor.execute(sel)
        desc = ''
        rs = cursor.fetchone()
        if rs != None:
            if str(rs[1]) == "True":
                desc += "(PRIMARY) "

            if str(rs[0]) == "True":
                desc += "Unique"
            else:
                desc += "Non-unique"

            if str(rs[2]) == "True":
                desc += ", clustered"
            else:
                desc += ", non-clustered"

            if rs[3] != None:
                desc += " %s" % rs[3]

            desc += ' index'

        if desc == '':
            desc = None

        return desc

class OracleWrapper(Wrapper):
    def get_import(self):
        import cx_Oracle
        return cx_Oracle

    def connect(self,
                host="localhost",
                port=None,
                user="sa",
                password="",
                database="default"):
        dbi = self.get_import()
        try:
            self.__db = dbi.connect("%s/%s@%s" % (user, password, database))
            return DB(self.__db, self)
        except dbi.Warning, val:
            raise Warning(val)
        except dbi.Error, val:
            raise Error(val)

class DB2Wrapper(Wrapper):
    def get_import(self):
        import DB2
        return DB2

    def connect(self,
                host="localhost",
                port=None,
                user="sa",
                password="",
                database="default"):
        return None # unsupported

class DummyWrapper(Wrapper):
    def get_import(self):
        import dummydb
        return dummydb

    def connect(self,
                host="localhost",
                port=None,
                user="sa",
                password="",
                database="default"):
        self.__db = dummydb.DummyDB()
        return DB(self.__db, self)

# This must be at the bottom so it "sees" the classes it references

TYPE_TO_CONS = { DUMMY      : DummyWrapper,
                 MYSQL      : MySQLWrapper,
                 POSTGRESQL : PostgreSQLWrapper,
                 SQL_SERVER : SQLServerWrapper,
                 ORACLE     : OracleWrapper,
                 DB2        : DB2Wrapper }
