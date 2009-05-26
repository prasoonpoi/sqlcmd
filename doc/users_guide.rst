==============================================================
sqlcmd: A Cross-platform, Cross-database SQL Command Line Tool
==============================================================

------------
User's Guide
------------

:Author: Brian M. Clapper
:Contact: bmc@clapper.org
:Date: 4 November, 2008
:Web site: http://www.clapper.org/software/python/sqlcmd/
:Copyright: Copyright (c) 2008 Brian M. Clapper

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

- Connection parameters for individual databases are kept in a configuration
  file in your home directory.
- Multiple logical names for each database.
- Command history management, with `GNU Readline`_ support. Each database
  has its own history file.
- Supports retrieving database metadata (getting a list of tables, querying
  the table's columns and their data types, listing the indexes and foreign
  keys for a table, etc.).
- Unix shell-style variable substitution.
- Standard interface that works the same no matter what database you're using.
- Uses the enhanced database drivers in the `Grizzled API`_'s ``db``
  module. (Those drivers are, in turn, built on top of standard Python
  DB API drivers like ``psycopg2`` and ``MySQLdb``.)
- Supports `MySQL`_, `Oracle`_, `PostgreSQL`_, `SQL Server`_ `SQLite 3`_ and
  Gadfly_ without customization (though you will have to install Python DB API
  drivers for all but SQLite 3).
- Written entirely in `Python`_, which makes it very portable (though the
  Python DB API database drivers are often written in C and may not be available
  on all platforms).

.. _Grizzled API: http://www.clapper.org/software/python/grizzled/
.. _GNU Readline: http://cnswww.cns.cwru.edu/php/chet/readline/rluserman.html
.. _Python: http://www.python.org/
.. _Oracle: http://www.oracle.com/
.. _SQL Server: http://www.microsoft.com/sqlserver/
.. _SQLite 3: http://www.sqlite.org/
.. _Gadfly: http://gadfly.sourceforge.net/

In short, *sqlcmd* is a SQL command tool that attempts to provide the same
interface for all supported databases and across all platforms.

Prerequisites
=============

*sqlcmd* requires the following:

- Python_ 2.5 or better
- The `Grizzled API`_ (automatically installed if you use ``easy_install``
  to install *sqlcmd*)
- The `enum`_ package (automatically installed if you use ``easy_install``)
- Appropriate Python DB API drivers for the database(s) you want to use.
  (See `Database Types`_, below.)
- **Windows only**: You'll also want the *ipython* ``pyreadline`` package,
  available via ``easy_install`` or from http://ipython.scipy.org/dist

.. _enum: http://pypi.python.org/pypi/enum/0.4.3

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

    -h, --help                     Show a usage message and exit.

    -c config, --config=config     Specifies the configuration file to use.
                                   Defaults to ``$HOME/.sqlcmd/config``.
                                   Ignored if ``-d`` is specified.
                                   See `Configuration File`_, below, for
                                   more information on the format of this file.

    -d database, --db=database     Database to use. Format:
                                   ``dbname,dbtype,host[:port],user,password``
                                   Overrides any specified *alias*. See
                                   `Specifying a Database`_, below, for a
                                   complete explanation of this parameter.

    -l level, --loglevel=level     Enable log messages as level *n*, where *n*
                                   is one of: ``debug``, ``info``, ``warning``,
                                   ``critical``, ``error``.

    -L logfile, --logfile=logfile  Dump log messages to *logfile*, instead of
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
    The name of the database. (For SQLite and Gadfly, this is the path to the
    file.)

``dbtype``:
    The database type, as defined by the `Grizzled Utility Library`_'s `db`_
    package, ``oracle``,``sqlserver``, ``mysql``, ``postgresql`` and
    ``sqlite``. Additional database types can be added, however; see
    below_.

.. _below: `Configuration File`_

``host:port``:
    The host name and port number on which the database server is listening for
    connections. This field is ignored, and may be empty, for SQLite and
    Gadfly. The port number may be omitted (i.e., with only the host name
    specified), and the database driver will use the default port for the
    database type.

``user``:
    The user to use when authenticating to the database. Ignored for SQLite
    and Gadfly.

``password``:
    The password to use when authenticating to the database. Ignored for SQLite
    and Gadfly.

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

Specifying the database connection parameters on the command line is both
tedious and error prone, even with a good shell history mechanism. So,
*sqlcmd* permits you to store your database connection information in a
configuration file.

A Brief Overview of the Configuration File
------------------------------------------

Things will be a little clearer if we look at a sample configuration file.
The following file specifies the same databases as in the examples, above:

.. code-block:: ini

    # sqlcmd initialization file

    [settings]
    colspacing: 2

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
*sqlcmd* searches for it), connecting to each of the databases is much simpler:

.. code-block:: bash

    $ sqlcmd testdb
    $ sqlcmd customers
    $ sqlcmd mydb

You can store the file somewhere else, of course; you just have to tell
*sqlcmd* where it is:

.. code-block:: bash

    $ sqlcmd -c /usr/local/etc/sqlcmd.cfg testdb
    $ sqlcmd -c /usr/local/etc/sqlcmd.cfg customers
    $ sqlcmd -c /usr/local/etc/sqlcmd.cfg mydb

See the next section for details on the specific sections and options in the
*sqlcmd* configuration file.

Configuration File in Depth
---------------------------

A *sqlcmd* configuration file, typically stored in ``$HOME/.sqlcmd/config``,
is an INI-style file divided into logical sections. Each of those sections
is described below. All section names must be unique within the file.

Blank lines and comment lines are ignored; comment lines start with a "#"
character.

*sqlcmd* uses the `Grizzled API`_'s `grizzled.config.Configuration`_
class to parse the file; that class is, in turn, an enhancement of the standard
Python `ConfigParser`_ class.

.. _grizzled.config.Configuration: http://www.clapper.org/software/python/grizzled/epydoc/grizzled.config.Configuration-class.html
.. _ConfigParser: http://docs.python.org/lib/module-ConfigParser.html

Because *sqlcmd* uses the Grizzled API's ``Configuration`` class, you can use
include directives and variable substitution in the configuration file, if
you with. See the `grizzled.config.Configuration`_ documentation for more
details.

The ``settings`` Section
~~~~~~~~~~~~~~~~~~~~~~~~

This optional section can contain initial values for any of the settings
that are understood by the `.set`_ command. See `.set`_ for a full explanation
of each setting.

The ``db.`` Sections
~~~~~~~~~~~~~~~~~~~~

A ``db.`` section contains the connection definition for a particular database.
The ``db.`` prefix must be followed by the primary name of the database.
Multiple ``db.`` sections can exist in the configuration file; each section
supports the following parameters.

    +------------------+---------------------------------+---------------------+
    | Parameter Name   | Description                     | Required/Optional   |
    +==================+=================================+=====================+
    + ``database``     | The name of the database, as    | required            |
    |                  | known by the RDBMS engine.      |                     |
    +------------------+---------------------------------+---------------------+
    | ``type``         | The type of the database. This  | required            |
    |                  | value must be recognized by the |                     |
    |                  | Grizzled API's ``db`` module.   |                     |
    |                  | That means it must identify a   |                     |
    |                  | database driver that is part of |                     |
    |                  | the ``grizzled.db`` package, or |                     |
    |                  | it must be a driver you specify |                     |
    |                  | yourself, in a ``driver.``      |                     |
    |                  | section. (See `below`_.)        |                     |
    +------------------+---------------------------------+---------------------+
    | ``host``         | The host on which the database  | required (but       |
    |                  | resides. The RDBMS server on    | ignored for SQLite  |
    |                  | that host must be configured to | and Gadfly)         |
    |                  | accept incoming database client |                     |
    |                  | connections.                    |                     |
    |                  |                                 |                     |
    |                  | This parameter is ignored for   |                     |
    |                  | SQLite databases.               |                     |
    +------------------+---------------------------------+---------------------+
    | ``port``         | The port on which the database  | optional (but       |
    |                  | server is listening. If not     | ignored for SQLite  |
    |                  | specified, *sqlcmd* uses the    | and Gadfly)         |
    |                  | default port for the RDBMS      |                     |
    |                  | server (e.g, 1521 for Oracle,   |                     |
    |                  | 1433 for SQL Server, 3306 for   |                     |
    |                  | MYSQL, 5432 for PostgreSQL,     |                     |
    |                  | etc.).                          |                     |
    |                  |                                 |                     |
    |                  | This parameter is ignored for   |                     |
    |                  | SQLite databases.               |                     |
    +------------------+---------------------------------+---------------------+
    | ``user``         | The user to use when            | required (but       |
    |                  | authenticating to the database. | ignored for SQLite  |
    |                  |                                 | and Gadfly)         |
    |                  | This parameter is ignored for   |                     |
    |                  | SQLite databases.               |                     |
    +------------------+---------------------------------+---------------------+
    | ``password``     | The password to use when        | required (but       |
    |                  | authenticating to the database. | ignored for SQLite  |
    |                  |                                 | and Gadfly)         |
    |                  | This parameter is ignored for   |                     |
    |                  | SQLite databases.               |                     |
    +------------------+---------------------------------+---------------------+
    | ``aliases``      | A comma-separated list of alias | optional            |
    |                  | names for the database. This    |                     |
    |                  | list allows you to refer to the |                     |
    |                  | database by multiple names      |                     |
    +------------------+---------------------------------+---------------------+
    | ``onconnect``    | Path to a script of commands to | optional            |
    |                  | run just after connecting to    |                     |
    |                  | database. The file can contain  |                     |
    |                  | any valid *sqlcmd* command      |                     |
    |                  | (including, obviously, SQL).    |                     |
    |                  |                                 |                     |
    |                  | Any leading "~" in the path is  |                     |
    |                  | expanding to the home directory |                     |
    |                  | of the user running *sqlcmd*.   |                     |
    |                  | Relative paths are assumed to   |                     |
    |                  | be relative to the directory    |                     |
    |                  | containing the configuration    |                     |
    |                  | file.                           |                     |
    |                  |                                 |                     |
    |                  | *Hint*: Specify the path using  |                     |
    |                  | Unix-style forward slashes,     |                     |
    |                  | even on Windows, to avoid       |                     |
    |                  | problems with backslashes.      |                     |
    +------------------+---------------------------------+---------------------+

Database Types
++++++++++++++

The following database types are supported automatically, provided you have
the right underlying Python database drivers installed. As noted above, you
can extend *sqlcmd* to support additional database. See the section on
`.driver`_, below, for details.

.. _.driver: `dot_driver`_

    +----------------+--------------+-------------------+
    | Type name used |              | Python DB API     |
    | with *sqlcmd*  | Database     | module            |
    +================+==============+===================+
    | ``mysql``      | MySQL_       | `MySQLdb`_        |
    +----------------+--------------+-------------------+
    | ``oracle``     | Oracle_      | `cx_Oracle`_      |
    +----------------+--------------+-------------------+
    | ``postgresql`` | PostgreSQL_  | `psycopg2`_       |
    +----------------+--------------+-------------------+
    | ``sqlserver``  | Microsoft    | `pymssql`_        |
    |                | `SQL Server`_|                   |
    +----------------+--------------+-------------------+
    | ``sqlite``     | `SQLite 3`_  | sqlite3 (comes    |
    |                |              | with Python 2.5)  |
    +----------------+--------------+-------------------+
    | ``gadfly``     | Gadfly_      | Gadly itself      |
    +----------------+--------------+-------------------+

.. _psycopg2: http://pypi.python.org/pypi/psycopg2/2.0.4
.. _MySQLdb: http://sourceforge.net/projects/mysql-python
.. _cx_Oracle: http://python.net/crew/atuining/cx_Oracle/
.. _pymssql: http://pymssql.sourceforge.net/

A Note about Database Names
+++++++++++++++++++++++++++

When you specify the name of a database on the *sqlcmd* command line,
*sqlcmd* attempts to match that name against the names of all databases in
the configuration file. *sqlcmd* compares the name you specify against the
following values from each ``db.`` configuration section:

- The section name, minus the ``db.`` prefix. This is the primary name of
  the database, from *sqlcmd*'s perspective.
- The value of the ``database`` option.
- The value or values of the ``aliases`` option.

You only need to specify as many characters as are
necessary to uniquely identify the database.

Thus, given this configuration file:

.. code-block:: ini


    [db.testdb]
    names=sqlite, test
    database=/tmp/test.db
    type=sqlite

    [db.customers]
    names=oracle, custdb
    database=cust001
    type=oracle
    host=db.example.com
    user=scott
    password=tiger


You can connect to the ``customers`` database using any of the following
names:

- ``customers``: the section name, minus ``db.``.
- ``custdb``: one of the aliases
- ``oracle``: the other alias
- ``cust001``: the actual database name, from the ``database`` option
- ``cust``: a unique abbreviation of ``customers`` or ``cust001``

.. _dot_driver:

The ``driver.`` Sections
~~~~~~~~~~~~~~~~~~~~~~~~

The ``driver.`` section allows you to install additional enhanced database
drivers, beyond those that are built into the `Grizzled API`_'s ``db``
package.

An enhanced driver must extend the ``grizzled.db.DBDriver`` class and provide
the appropriate methods. See the `appropriate Grizzled documentation`_ for
details. If you want to write your own driver, the Grizzled source code is
invaluable.

.. _appropriate Grizzled documentation: http://www.clapper.org/software/python/grizzled/epydoc/grizzled.db-module.html

The ``driver.`` section supports the following options:

    +------------------+---------------------------------+---------------------+
    | Parameter Name   | Description                     | Required/Optional   |
    +==================+=================================+=====================+
    + ``class``        | The fully-qualified name of the | required            |
    |                  | driver class, including any     |                     |
    |                  | package and/or module name.     |                     |
    +------------------+---------------------------------+---------------------+
    | ``name``         | The logical name to use for the | required            |
    |                  | driver.                         |                     |
    +------------------+---------------------------------+---------------------+

For example, suppose you wrote a driver to connect to the `Apache Derby`_
database (perhaps using `JPype`_). Let's further suppose that the driver is
implemented by a Python class called ``DerbyDriver`` (which extends the
Grizzled ``DBDriver`` class) and resides in module ``mycode.db``. You could
use the following *sqlcmd* configuration section to make *sqlcmd* aware of
that driver:

.. code-block:: ini

    [driver.derby]
    class=mycode.db.DerbyDriver
    name=derby

With that section in the configuration file, you can now use the value ``derby``
for the ``type`` parameter in any ``db.`` section.

Obviously, the appropriate supporting Python (and other) code must be available
to *sqlcmd*, by setting ``PYTHONPATH``, ``LD_LIBRARY_PATH``, and/or ``PATH``,
as appropriate for your operating system.

.. _Apache Derby: http://db.apache.org/derby/
.. _JPype: http://jpype.sourceforge.net/


Other Sections
~~~~~~~~~~~~~~

*sqlcmd* quietly ignores any other sections in the configuration file. One
possible use for other sections is as holders for common variable definitions
that are substituted in other places in the file. For instance, suppose all
your database engine happen to be on the same host and happen to use the same
user name and password. To share that common configuration information, you
might do something like the following:

.. code-block:: ini

    [defs]
    # Shared definitions
    dbhost=db.example.com
    admin_user=admin
    admin_password=foo.bar

    [db.testdb]
    names=sqlite, test
    database=/tmp/test.db
    type=sqlite

    [db.customers]
    names=oracle
    database=customers
    type=oracle
    host=${dbhost}
    user=${admin_user}
    password=${admin_password}

    [db.mydb]
    names=postgres
    database=mydb
    type=postgresql
    host=${dbhost}
    user=${admin_user}
    password=${admin_password}


Using *sqlcmd*
==============

When run in interactive mode (i.e., without an *@file* parameter_), *sqlcmd*
prompts on standard input with a "?" and waits for commands to be entered,
executing each one as it's entered. It continues to prompt for commands until
either:

- it encounters an end-of-file condition (Ctrl-D on Unix systems, Ctrl-Z
  on Windows), or
- you type the ``.exit`` command.

.. _parameter: `Parameters`_

Some commands (e.g., all SQL commands, and some others) are not executed until
a final ";" character is seen on the input; this permits multi-line commands.
Other commands, such as internal commands like ``.set``, are single-line
commands and do not require a semi-colon.

Before going into each specific type of command, here's a brief *sqlcmd*
transcript, to whet your appetite:

.. code-block:: text

    $ sqlcmd mydb
    SQLCmd, version 0.3 ($Revision$)
    Copyright 2008 Brian M. Clapper.

    Type "help" or "?" for help.

    Connecting to MySQL database "mydb" on host localhost.
    Using readline for history management.
    Loading history file "/home/bmc/.sqlcmd/mydb.hist"
    ? .set
    autocommit = true
    binarymax  = 20
    colspacing = 1
    echo       = false
    showbinary = false
    stacktrace = false
    timings    = true
    ? .show tables;
    users
    customers
    ? .desc users
    -----------
    Table users
    -----------
    id             bigint NOT NULL
    companyid      bigint NOT NULL
    lastname       character varying(254) NOT NULL
    firstname      character varying(254) NOT NULL
    middleinitial  character(1) NULL
    username       character varying(30) NOT NULL
    password       character varying(64) NOT NULL
    email          character varying(254) NOT NULL
    telephone      character varying(30) NULL
    department     character varying(254) NULL
    isenabled      character(1) NOT NULL
    ? select id, companyid, lastname, firstname, middleinitial, username, email from etuser;
    Execution time: 0.092 seconds
    2 rows

    id companyid lastname firstname middleinitial username email
    -- --------- -------- --------- ------------- -------- ---------------
     1         1 Clapper  Brian     M             bmc      bmc@clapper.org
     2         1 User     Joe       NULL          joe      joe@example.org


SQL
---

*sqlcmd* will issue any valid SQL command. It does not interpret the SQL
command at all, beyond recognizing the initial ``SELECT``, ``INSERT``,
``UPDATE``, etc., statement. Thus, RDBMS-specific SQL is perfectly permissable.

For SQL commands that produce results, such as ``SELECT``, *sqlcmd* displays
the result in a tabular form, using as little horizontal real estate as possible.
It does **not** wrap its output, however.

*sqlcmd* has explicit support for the following kinds of SQL statements.
Note that "explicit support" means *sqlcmd* can do table-name completion
for those commands (see `Command Completion`_), not that *sqlcmd* understands
the SQL syntax.

- ``ALTER`` (e.g., ``ALTER TABLE``, ``ALTER INDEX``)
- ``CREATE`` (e.g., ``CREATE TABLE``, ``CREATE INDEX``)
- ``DELETE``
- ``DROP`` (e.g., ``DROP TABLE``, ``DROP INDEX``)
- ``INSERT``
- ``UPDATE``

Timings
~~~~~~~

By default, *sqlcmd* times how long it takes to execute a SQL statement
and prints the resulting times on the screen. To suppress this behavior,
set the ``timings`` setting to ``false``:

.. code-block:: text

    .set timings false


SQL Echo
~~~~~~~~

By default, *sqlcmd* does *not* echo commands to the screen. That's a
reasonable behavior when you're using *sqlcmd* interactively. However, when
you're loading a file full of *sqlcmd* statements, you might want each
statement to be echoed before it is run. To enable command echo, set the
``echo`` setting to ``true``:

.. code-block:: text

    .set echo true

Comments
~~~~~~~~

*sqlcmd* honors (and ignores) SQL comments, as long as each comment is on a
line by itself. A SQL comment begins with "--".

Example of support syntax:

.. code-block:: text

    -- This is a SQL comment.
    -- And so is this.

Example of *unsupported* syntax:

.. code-block:: sql

    INSERT INTO foo VALUES (1); -- initialize foo

*sqlcmd*-specific Commands
--------------------------

These internal *sqlcmd* commands are one-line commands that do not require
a trailing semi-colon and cannot be on multiple lines. Most (but not all)
of these commands start with a dot (".") character, to distinguish them
from commands that are processed by the connected database engine.

``.about``
~~~~~~~~~~

Displays information about *sqlcmd*.


``begin``
~~~~~~~~~

Start a new transaction. This command is not permitted unless ``autocommit``
is ``true``. (See `.set`_) ``begin`` is essentially a no-op: It's ignored in
autocommit mode, and irrelevant when autocommit mode is off. It's there
primarily for SQL scripts.

Example of use:

.. code-block:: sql

    begin
    update foo set bar = 1;
    commit

For compatibility with SQL scripts, this command does not begin with a ".".

See also:

- `.set`_
- `commit`_
- `rollback`_

``commit``
~~~~~~~~~~

Commit the current transaction. Ignored if ``autocommit`` is enabled. For
compatibility with SQL scripts, this command does not begin with a ".".

See also:

- `.set`_
- `begin`_
- `rollback`_


``.connect``
~~~~~~~~~~~~

The ``.connect`` command closes the current database connection and opens
a new one to a (possibly) different database. The general form of the command
is:

.. code-block:: text

    .connect dbname

*dbname* is a database name from the configuration file. When it first starts
running, *sqlcmd* issues an implicit ``.connect`` to the database specified
on the command line.


``.describe``
~~~~~~~~~~~~~

The ``.describe`` command, which can be abbreviated ``.desc``, is used to
describe a table. The general form of the command is:

.. code-block:: text

    .describe tablename [full]

If "full" is not specified, then *sqlcmd* prints a simple description of the
table and its columns. For instance:

.. code-block:: text

    ? .desc users
    -----------
    Table users
    -----------
    id             bigint NOT NULL
    companyid      bigint NOT NULL
    lastname       character varying(254) NOT NULL
    firstname      character varying(254) NOT NULL
    middleinitial  character(1) NULL
    username       character varying(30) NOT NULL
    password       character varying(64) NOT NULL
    email          character varying(254) NOT NULL
    telephone      character varying(30) NULL
    department     character varying(254) NULL
    isenabled      character(1) NOT NULL

If "full" is specified, *sqlcmd* also gathers and displays information about
the table's indexes. For example:

.. code-block:: text

    ? .desc users
    -----------
    Table users
    -----------
    id             bigint NOT NULL
    companyid      bigint NOT NULL
    lastname       character varying(254) NOT NULL
    firstname      character varying(254) NOT NULL
    middleinitial  character(1) NULL
    username       character varying(30) NOT NULL
    password       character varying(64) NOT NULL
    email          character varying(254) NOT NULL
    telephone      character varying(30) NULL
    department     character varying(254) NULL
    isenabled      character(1) NOT NULL

    --------
    Indexes:
    --------

    userpk1 Columns:     (id)
            Description: (PRIMARY) Unique, non-clustered btree index
    ----------------------------------------------------------------------------
    userak1 Columns:     (companyid, username)
            Description: Unique, non-clustered btree index


``.echo``
~~~~~~~~~

Echoes all remaining arguments to standard output. This command is useful
primarily in scripts.

Example:

.. code-block:: text

    .echo Don't look now, but I'm about to run SELECT

``.exit``
~~~~~~~~~

Exit *sqlcmd*. ``.exit`` is equivalent to typing the key sequence corresponding
to an end-of-file condition (Ctrl-D on Unix systems, Ctrl-Z on Windows).

``.history``
~~~~~~~~~~~~

``.history`` displays the command history. See `Command History`_ for a
complete explanation of *sqlcmd*'s command history capabilities.

``r`` or ``redo``
~~~~~~~~~~~~~~~~~

Re-issue a command from the history. General usage:

.. code-block:: text

    r [num|str]
    redo [num|str]

If *num* is present, it is the number of the command to re-run. If *str*
is specified, the most recent command that *str* (using a substring match)
is re-run.

For example, consider this history:

.. code-block:: text

    ? .history
       1: .show tables;
       2: select * from foo;
       3: .desc foo;
       4: .desc foobar;

Here are various ``redo`` invocations:

.. code-block:: text

    ? r 1  <--- re-runs command 1, ".show tables"
    ? r s  <--- re-runs the most recent command that starts with "s", which is "select * from foo"
    ? r    <--- re-runs the last command, ".desc foobar"

``rollback``
~~~~~~~~~~~~

Roll the current transaction back. Ignored if ``autocommit`` is enabled. For
compatibility with SQL scripts, this command does not begin with a ".".

See also:

- `.set`_
- `begin`_
- `commit`_

``.run``
~~~~~~~~~

Loads an external file of commands (typically SQL) and runs those commands in
the current session *without exiting*. After the commands are run, *sqlcmd*
returns to its interactive prompt. ``.run`` can also be invoked as ``.load``.

.. code-block:: text

    .run path
    .load path

Both commands do exactly the same thing.

``.set``
~~~~~~~~~

The ``.set`` command displays or alters internal *sqlcmd* settings. Without
any parameters, ``.set`` displays all internal settings and their values:

.. code-block:: text

    ? .set
    autocommit = true
    binarymax  = 20
    colspacing = 1
    echo       = true
    showbinary = false
    stacktrace = false
    timings    = true

The supported settings are:

    +----------------+---------------------------------------------+----------+
    | Setting        | Meaning                                     | Default  |
    +================+=============================================+==========+
    | ``autocommit`` | Whether or not each SQL statement           | ``true`` |
    |                | automatically commits to the database. If   |          |
    |                | ``true``, then each SQL statement is        |          |
    |                | automatically committed to the database. If |          |
    |                | ``false``, then a new set of SQL statements |          |
    |                | starts a transaction, which must be         |          |
    |                | explicitly committed via the ``commit``     |          |
    |                | command. Also, if ``autocommit`` is         |          |
    |                | ``false``, the ``rollback`` command is      |          |
    |                | enabled.                                    |          |
    +----------------+---------------------------------------------+----------+
    | ``binarymax``  | How many bytes to display from binary (BLOB | 20       |
    |                | and CLOB) columns. Ignored unless           |          |
    |                | ``showbinary`` is ``true``.                 |          |
    +----------------+---------------------------------------------+----------+
    | ``colspacing`` | Number of spaces between each column of     | 1        |
    |                | result set (i.e., ``SELECT``) output.       |          |
    +----------------+---------------------------------------------+----------+
    | ``echo``       | Whether or not commands are echoed before   | ``false``|
    |                | they are executed.                          |          |
    +----------------+---------------------------------------------+----------+
    | ``showbinary`` | Whether or not to show data from binary     | ``false``|
    |                | (BLOB and CLOB) columns. If ``true``, the   |          |
    |                | value of ``binarymax`` dictates how many    |          |
    |                | bytes to display.                           |          |
    +----------------+---------------------------------------------+----------+
    | ``stacktrace`` | Whether to display a Python stack trace on  | ``false``|
    |                | normal (i.e., expected) errors, like SQL    |          |
    |                | syntax errors.                              |          |
    +----------------+---------------------------------------------+----------+
    | ``timings``    | Whether to display execution times for SQL  | ``true`` |
    |                | statements.                                 |          |
    +----------------+---------------------------------------------+----------+

``.show``
~~~~~~~~~

The ``.show`` command displays certain information about the currently
connected database. Currently, it supports two sub-commands:

``.show database``
++++++++++++++++++

Show information about the current connected database, including database
location, RDBMS vendor, and RDBMS version.

``.show tables``
++++++++++++++++

Show the list  of user-visible (i.e., non-system) tables in the current
database. This sub-command takes an additional, optional, filter parameter.
The filter is a regular expression; all tables not matching the filter are
not shown. For example:

.. code-block:: sql

    ? .show tables
    all_users
    foo
    fool
    tb_bar
    tb_foo
    userlocation
    ? .show tables ^tb
    tb_bar
    tb_foo
    ? .show tables tb
    tb_bar
    tb_foo
    ? .show tables ^.*foo
    foo
    fool
    tb_foo
    ? .show tables .*foo
    foo
    fool
    tb_foo
    ? .show tables .*foo$
    foo
    tb_foo
    ? .show tables foo$
    foo

As you can see from the example, the regular expression is implicitly anchored
to the beginning of the table name.

``.var``
~~~~~~~~

Set a shell-style variable that can be interpolated in subsequent input lines.
For example:

.. code-block:: sql

    ? .var table=mytable
    ? select * from $mytable
    
or:

.. code-block:: sql

    ? table=mytable
    ? select * from $mytable

See `Unix shell-style variables`_ for more information.

``.vars``
~~~~~~~~~

Show all variables current set by ``.var``.


Extended Commands
-----------------

If you type a command that *sqlcmd* doesn't recognize as a SQL command or one
of its internal commands, it passes the command straight through to the
database and treats the command as it would treate a SQL ``SELECT``. This
policy allows you to use certain RDBMS-specific commands without *sqlcmd*
having to support them explicitly. For instance, here's what happens if you've
connected *sqlcmd* to a SQLite database and you try to use the SQLite
``EXPLAIN`` command:

.. code-block:: text

    ? explain select distinct id from foo;
    Execution time: 0.000 seconds
    20 rows

    addr opcode        p1 p2 p3
    ---- ------------- -- -- -----------------
    0    OpenEphemeral 1  0  keyinfo(1,BINARY)
    1    Goto          0  16
    2    Integer       0  0
    3    OpenRead      0  2
    4    SetNumColumns 0  1
    5    Rewind        0  14
    6    Column        0  0
    7    MakeRecord    -1 0
    8    Distinct      1  11
    9    Pop           2  0
    10   Goto          0  13
    11   IdxInsert     1  0
    12   Callback      1  0
    13   Next          0  6
    14   Close         0  0
    15   Halt          0  0
    16   Transaction   0  0
    17   VerifyCookie  0  1
    18   Goto          0  2
    19   Noop          0  0

Similarly, here's what happens when you run the ``ANALYZE`` command on a
PostgreSQL database:

.. code-block:: text

    ? analyze verbose;
    Execution time: 0.054 seconds
    0 rows

Restrictions
~~~~~~~~~~~~

- Some extended commands don't work well through *sqlcmd*. Your mileage
  may vary.
- Since these extended commands are database-specific, they do not show
  up in command completion output, and they do not support command completion
  themselves.

Command History
---------------

*sqlcmd* supports a `bash`_-like command history mechanism. Every command
you type at the command prompt is saved in an internal memory buffer, accessible
via the ``.history`` command.

.. _bash: http://www.gnu.org/software/bash/manual/

Because *sqlcmd* also supports GNU Readline, you can use the standard GNU
Readline key bindings to scroll through your history list, edit previous
commands, and re-issue them.

Upon exit, *sqlcmd* saves its internal history buffer to a database-specific
file. The file's name is adapted from the primary name of the database (*i.e.*,
from the section name for the database in the configuration file). The
history files are stored in directory ``.sqlcmd`` under your home directory.
History files always end with ".hist".

For example, consider this configuration file:

.. code-block:: ini

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

The history file for the first database is ``$HOME/.sqlcmd/testdb.hist``, and
the history file for the second database is ``$HOME/.sqlcmd/customers.hist.``

Unix shell-style variables
--------------------------

To save typing, or for minor programming tasks, you can set variables
interactively or within a *sqlcmd* script. The syntax is reminiscent of
the *bash* shell, though with some differences:

.. code-block:: sql

    ? table=mytable
    ? select * from $table

The ``variable=value`` syntax is actually a convenient shorthand notation for::

    .var variable=value
    
A variable's value can be interpolated with either "${varname}" or "$varname".
Thus, these two lines are identical:

.. code-block:: sql

    ? select * from $table;
    ? select * from ${table};

Some Differences from Unix Shells
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are some differences from *bash*, however.

Single-line assignments
+++++++++++++++++++++++

Variable assigments cannot span multiple input lines.

Blanks are stripped
+++++++++++++++++++

Blanks are stripped from the beginning and end of both variable names and
variable values. Thus, the following assignments are equivalent. (The *sqlcmd*
prompt is shown, for clarity.)

.. code-block:: text

    ? table=mytable
    ? table = mytable
    ? table=          mytable
    ?   table   =  mytable

All four statements set variable "table" to the string "mytable".

If a value must contain leading or trailing blanks, enclose it in either
single or double quotes. For example:

    ? foo='       bar '

Embedded blanks don't require quotes
++++++++++++++++++++++++++++++++++++

If a variable value has no leading or trailing blanks, but *does* have
embedded blanks, no quotes are necessary (though they are permitted).
The following two variable assignments are identical:

.. code-block:: text

    ? fred=This variable has blanks
    ? fred="This variable has blanks"

Single and double quotes are semantically identical
+++++++++++++++++++++++++++++++++++++++++++++++++++

Like Python, and unlike *bash*, in *sqlcmd*, surrounding a value with
single quotes has the same meaning as surrounding it with double quotes.

.. code-block:: text

    ? foo='bar'
    ? .echo $foo
    bar
    ? foo="baz"
    ? .echo $foo
    baz

You can embed quotes inside of a variable value in one of two ways:
Use the other quote to surround the value (see below), or escape the quote
inside the value with a backslash. For example, the following assignments
all set ``foo`` to the same value.

.. code-block:: text

    ? var_with_quotes="'<-- That's a quote."
    ? var_with_quotes='\'<-- That\'s a quote.'

Variable names can have hyphens
+++++++++++++++++++++++++++++++

Variable names can consist of alphanumerics, underscores and hyphens, as
with only one restriction: Two leading hyphens is a comment. Thus, the
following variable settings are all legal:

.. code-block:: text

    ? -a=foo
    ? .echo $-a
    foo
    ? lispish-var=some value
    ? .echo ${lispish-var}
    some value
    
Unsetting a variable
++++++++++++++++++++

There is no ``unset`` command. To unset a variable, simply set it to nothing:

.. code-block:: text

    ? x=foobar
    ? .echo $x
    foobar
    ? x=
    ? .echo $x
    ?

Command Completion
-------------------

*sqlcmd* supports TAB-completion in various places, in the manner of the GNU
`bash`_ shell. TAB-completion is (mostly) context sensitive. For example:

``.<TAB>``
    Displays a list of all the "." commands

``.set <TAB>``
    Displays the variables you can set.

``.set v<TAB>``
    Completes the variable name that starts with "v". If multiple variables
    start with "v", then the common characters are completed, and a second
    TAB will display all the matching variables.

``.connect <TAB>``
    shows all the database names and aliases in the config file

``.connect a<TAB>``
    Completes the database name or alias that starts with "a". If multiple
    names start with "a", then the common characters are completed, and a second
    TAB will display all the matching names.

``select * from <TAB>``
    Shows the tables in the current database. (So does ``select ``\ *<TAB>*,
    actually.) This works for ``insert``, ``update``, ``delete``, ``drop``,
    and ``.desc``, as well. The completion in SQL commands *only* completes
    table names; it is not currently sensitive to SQL syntax.

``.history <TAB>``
    Shows the commands in the history.

``.history s<TAB>``
    Shows the names of all commands in the history beginning with "s".

``.load <TAB>``
    Lists all the files in the current directory

``.load f<TAB>``
    Lists all the files in the current directory that start with "s"

``.load ~/<TAB>``
    Lists all the files in your home directory

``.load ~/d<TAB>``
    Lists all the files in your home directory that start with "d"

etc.


License and Copyright
=====================

Copyright © 2008 Brian M. Clapper

This is free software, released under the following BSD-like license:

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. The end-user documentation included with the redistribution, if any,
   must include the following acknowledgement:

   This product includes software developed by Brian M. Clapper
   (bmc@clapper.org, http://www.clapper.org/bmc/). That software is
   copyright © 2008 Brian M. Clapper.

   Alternately, this acknowlegement may appear in the software itself, if
   and wherever such third-party acknowlegements normally appear.

THIS SOFTWARE IS PROVIDED **AS IS** AND ANY EXPRESSED OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL BRIAN M. CLAPPER BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
