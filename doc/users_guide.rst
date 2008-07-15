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

Usage
=====

*sqlcmd* is invoked from the command line. You specify the database either
via the ``-d`` (``--database``) command line option or, more conveniently,
in a configuration file. The configuration file allows you to record the
connection information for multiple databases, then specify a single database
via a the least number of unique characters necessary to find it in the
configuration file.

Command Line
------------

**sqlcmd** [OPTIONS] [*alias*] [*@file*]

Options
~~~~~~~

    -h, --help                    Show a usage message and exit.

    -c config, --config=config    Specifies the configuration file to use.
                                  Defaults to ``$HOME/.sqlcmd/config``.
                                  Ignored if ``-d`` is specified.

    -d database, --db=database    Database to use. Format:
                                  ``dbname,dbtype,host[:port],user,password``
                                  Overrides any specified *alias*. Legal
                                  database types are defined by the
                                  `Grizzled Utility Library`_'s `db`_ package, 
                                  and currently include: ``oracle``,
                                  ``sqlserver``, ``mysql``, ``postgresql`` and
                                  ``sqlite``. Additional database types can be
                                  added, however; see below.

    -l level, --loglevel=level    Enable log messages as level *n*, where *n*
                                  is one of: ``debug, info, warning, critical,
                                  error``

    -L logfile, --logfile=logfile Dump log messages to *logfile*, instead of
                                  standard output

.. _Grizzled Utility Library: http://www.clapper.org/software/python/grizzled/
.. _db: http://www.clapper.org/software/python/grizzled/epydoc/grizzled.db-module.html

Parameters
~~~~~~~~~~

- The *alias* parameter identifies an alias for the database in the
  configuration file. It's ignored if the ``-d`` option is specified.

- The *@file* parameter specifies a file of SQL (and *sqlcmd*) commands to be
  run once *sqlcmd* has connected to the database. If this parameter is omitted,
  *sqlcmd* will enter command line mode, prompting on standard input for each
  command.

Configuration File
------------------

Things will be a little clearer if we look at a sample configuration file.

.. code-block:: ini

    # ---------------------------------------------------------------------------
    # sqlcmd initialization file

    [db.example_postgres]
    names=example-p, p-example, postgres
    database=example
    host=localhost
    #port=
    type=postgresql
    user=admin
    password=admin

    [db.example_sqlite3]
    names=example-p, p-example, postgres
    database=/tmp/test.db
    type=sqlite

This configuration file defines