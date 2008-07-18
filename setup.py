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

# Now the setup stuff.

setup (name          = 'sqlcmd',
       version       = info['__version__'],
       description   = 'A cross-platform, cross-database SQL command line tool',
       packages      = find_packages(),
       url           = info['__url__'],
       license       = info['__license__'],
       author        = info['__author__'],
       author_email  = info['__email__'],
       entry_points  = {'console_scripts' : 'sqlcmd=sqlcmd:main'},
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
                           'Topic :: Utilities']
)
