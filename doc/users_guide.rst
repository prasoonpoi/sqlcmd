===================
sqlcmd User's Guide
===================

------------
User's Guide
------------

:Author: Brian M. Clapper
:Contact: bmc@clapper.org
:Date: $Date: 2008-06-01 22:59:33 -0400 (Sun, 01 Jun 2008) $
:Web site: http://www.clapper.org/software/python/snake/
:Copyright: Copyright © 2008 Brian M. Clapper

.. contents::

Introduction
============

*sqlcmd* is a SQL command line tool, similar in concept to tools like Oracle's
`SQL*Plus`_, the PostgreSQL_ ``psql`` command, and MySQL_'s ``mysql`` tool.

.. _SQL*Plus: http://www.oracle.com/technology/docs/tech/sql_plus/index.html
.. _PostgreSQL: http://www.postgresql.org/
.. _MySQL: http://www.mysql.org/

Some features at a glance
--------------------------

- Connection parameters for individual databases are kept in a ``.sqlcmd``
  file in your home directory.
- Databases can be assigned multiple logical names.
- GNU Readline support, with history management. History files are saved
  per database.
- Ability to get a list of tables, examine a table's columns, and get a list of
  the indexes and foreign keys for a table.
- A ``.set`` command that displays and controls *sqlcmd* settings.
- Uses the enhanced database drivers in the `Grizzled API`_'s ``db``
  module. (Those drivers are, in turn, built on top of standard Python
  DB API drivers like ``psycopg2`` and ``MySQLdb``.)

  .. _Grizzled API: http://www.clapper.org/software/python/grizzled/

In short, *sqlcmd* is a SQL command tool that attempts to provide the same
interface for all supported databases.
