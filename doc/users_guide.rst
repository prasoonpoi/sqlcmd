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
                                  See `Configuration File`_, below, for
                                  more information on the format of this file.

    -d database, --db=database    Database to use. Format:
                                  ``dbname,dbtype,host[:port],user,password``
                                  Overrides any specified *alias*. See
                                  `Specifying a Database`_, below, for a
                                  complete explanation of this parameter.

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
  
Specifying a Database
~~~~~~~~~~~~~~~~~~~~~

The ``--db`` (or ``-d``) parameter is somewhat complicated. It takes five
comma-separated parameters, in order:

``dbname``:
    The name of the database. (For SQLite, this is the path to the file.)
    
``dbtype``:
    The database type, as defined by the `Grizzled Utility Library`_'s `db`_
    package, ``oracle``,``sqlserver``, ``mysql``, ``postgresql`` and
    ``sqlite``. Additional database types can be added, however; see 
    below_.
    
.. _below: `Configuration File`_

``host:port``:
    The host name and port number on which the database server is listening for 
    connections. This field is ignored, and may be empty, for SQLite. The port
    number may be omitted (i.e., with only the host name specified), and the
    database driver will use the default port for the database type.
    
``user``:
    The user to use when authenticating to the database. Ignored for SQLite.
    
``password``:
    The password to use when authenticating to the database. Ignored for SQLite.

Examples:
+++++++++

Connect to a SQLite database residing in file ``/tmp/test.db``::

    sqlcmd -d /tmp/test.db,sqlite,,,
    
Connect to an Oracle database named "customers" on host ``db.example.com``,
using user "scott" and password "tiger"::

    sqlcmd -d customers,oracle,db.example.com,scott,tiger
    
Connect to a PostgreSQL database named "mydb" on the current host, using user
"psql" and password "foo.bar"::

    sqlcmd -d mydb,postgresql,localhost,psql,foo.bar


Configuration File
==================

Specify the database connection parameters on the command line is both tedious
and error prone, even with a good shell history mechanism. So, *sqlcmd*
permits you to store your database connection information in a configuration
file.

A Brief Overview of the Configuration File
------------------------------------------

Things will be a little clearer if we look at a sample configuration file.
The following file specifies the same databases as in the examples, above:

.. code-block:: ini

    # sqlcmd initialization file

    [db.testdb]
    names=sqlite, test
    database=/tmp/test.db
    type=sqlite

    [db.customers]
    names=oracle
    database=customers
    type=oracle
    host=db.example.com
    user=scott
    password=tiger

    [db.mydb]
    names=postgres
    database=mydb
    type=postgresql
    host=localhost
    user=psql
    password=foo.bar

Now, if you store that file in ``$HOME/.sqlcmd/config`` (the default place 
*sqlcmd* searches for it), connecting to each of the databases is much simpler::

    sqlcmd testdb
    sqlcmd customers
    sqlcmd mydb
    
You can store the file somewhere else, of course; you just have to tell
*sqlcmd* where it is::

    sqlcmd -c /usr/local/etc/sqlcmd.cfg testdb
    sqlcmd -c /usr/local/etc/sqlcmd.cfg customers
    sqlcmd -c /usr/local/etc/sqlcmd.cfg mydb

See the next section for details on the specific sections and options in the
*sqlcmd* configuration file.

Configuration File in Depth
---------------------------

The ``db.`` Sections
~~~~~~~~~~~~~~~~~~~~

The ``driver.`` Sections
~~~~~~~~~~~~~~~~~~~~~~~~

Other Sections
~~~~~~~~~~~~~~


The *sqlcmd* Command Line Interface
===================================

SQL
---

*sqlcmd*-specific Commands
--------------------------