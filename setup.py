#!/usr/bin/env python
#
# EasyInstall setup script for paragrep
#
# $Id$
# ---------------------------------------------------------------------------

import ez_setup
ez_setup.use_setuptools(download_delay=2)
from setuptools import setup, find_packages
import re
import sys
import os

def loadInfo():
    # Look for identifiers beginning with "__" at the beginning of the line.

    result = {}
    pattern = re.compile(r'^(__\w+__)\s*=\s*[\'"]([^\'"]*)[\'"]')
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    for line in open(os.path.join(here, 'sqlcmd', '__init__.py'), 'r'):
        match = pattern.match(line)
        if match:
            result[match.group(1)] = match.group(2)
    return result

info = loadInfo()

LONG_DESCRIPTION = \
'''*sqlcmd* is a SQL command line tool, similar in concept to tools like Oracle's
`SQL*Plus`_, the PostgreSQL_ ``psql`` command, and MySQL_'s ``mysql`` tool.

.. _SQL*Plus: http://www.oracle.com/technology/docs/tech/sql_plus/index.html
.. _PostgreSQL: http://www.postgresql.org/
.. _MySQL: http://www.mysql.org/

Some features at a glance
--------------------------

- Connection parameters for individual databases are kept in a configuration
  file in your home directory.
- Databases can be assigned multiple logical names.
- *sqlcmd* has command history management, with `GNU Readline`_ support.
  History files are saved per database.
- *sqlcmd* supports SQL, but also supports database metadata (getting a list
  of tables, querying the table's columns and their data types, listing the
  indexes and foreign keys for a table, etc.).
- *sqlcmd* command has a ``.set`` command that displays and controls *sqlcmd*
  settings.
- *sqlcmd* provides a standard interface that works the same no matter what
  database you're using.
- *sqlcmd* uses the enhanced database drivers in the `Grizzled API`_'s ``db``
  module. (Those drivers are, in turn, built on top of standard Python
  DB API drivers like ``psycopg2`` and ``MySQLdb``.)
- *sqlcmd* is written entirely in `Python`_, which makes it very portable
  (though the database drivers are often written in C and may not be available
  on all platforms).

.. _Grizzled API: http://www.clapper.org/software/python/grizzled/
.. _GNU Readline: http://cnswww.cns.cwru.edu/php/chet/readline/rluserman.html
.. _Python: http://www.python.org/

In short, *sqlcmd* is a SQL command tool that attempts to provide the same
interface for all supported databases and across all platforms.
'''

# Now the setup stuff.

setup(
    name             = 'sqlcmd',
    version          = info['__version__'],
    description      = 'A cross-platform, cross-database SQL command line tool',
    long_description = LONG_DESCRIPTION,
    packages         = find_packages(),
    url              = info['__url__'],
    license          = info['__license__'],
    author           = info['__author__'],
    author_email     = info['__email__'],
    entry_points     = {'console_scripts' : 'sqlcmd=sqlcmd:main'},
    install_requires = ['grizzled>=0.7.2', 
                        'enum>=0.4.3',],
    classifiers      = ['Environment :: Console',
                        'Intended Audience :: Developers',
                        'Intended Audience :: System Administrators',
                        'Intended Audience :: Science/Research',
                        'License :: OSI Approved :: BSD License',
                        'Operating System :: OS Independent',
                        'Programming Language :: SQL',
                        'Topic :: Database :: Front-Ends',
                        'Topic :: Utilities'],
)
