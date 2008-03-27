#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
sqlcmd - a simple SQL command interpreter

Requires:

- One or more Python DB API drivers. See 'db.py'
- The enum package, from http://cheeseshop.python.org/pypi/enum/
- Python 2.3 or better

COPYRIGHT AND LICENSE

Copyright � 2008 Brian M. Clapper

This is free software, released under the following BSD-like license:

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. The end-user documentation included with the redistribution, if any,
   must include the following acknowlegement:

      This product includes software developed by Brian M. Clapper
      (bmc@clapper.org, http://www.clapper.org/bmc/). That software is
      copyright � 2008 Brian M. Clapper.

    Alternately, this acknowlegement may appear in the software itself, if
    and wherever such third-party acknowlegements normally appear.

THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL BRIAN M. CLAPPER BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 

$Id$
"""
# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from cmd import Cmd
import sys
import os.path
import os
import history
from grizzled import db
import cPickle
import tempfile
import time
import textwrap
import traceback
import logging
from grizzled.optparser import CommandLineParser

# enum is available from http://cheeseshop.python.org/pypi/enum/

from enum import Enum

# use the built-in 'set' type if using Python 2.4 or better. Otherwise, use
# the old sets module.
try:
    set
except NameError:
    from sets import Set as set, ImmutableSet as frozenset

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

# Info about the module
__version__   = '0.1'
__author__    = 'Brian Clapper'
__email__     = 'bmc@clapper.org'
__url__       = 'http://www.clapper.org/software/python/paragrep/'
__copyright__ = '� 1989-2008 Brian M. Clapper'
__license__   = 'BSD-style license'

__all__ = ['SQLCmd', 'main']

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RC_FILE = os.path.expanduser("~/.sqlcmd")
INTRO = '''SQLCmd, version %s ($Revision$)
Copyright 2008 Brian M. Clapper.

Type "help" or "?" for help.
''' % __version__

BOOL_STRS = { "on"    : True,
              "off"   : False,
              "yes"   : True,
              "no"    : False,
              "1"     : True,
              "0"     : False,
              "true"  : True,
              "false" : False }

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

log = None

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def main():
    Main().run(sys.argv)

def traced(func):
    def wrapper(*__args,**__kw):
        log.debug("entering %s" % (func))
        try:
            return func(*__args,**__kw)
        finally:
            log.debug("exit %s" % (func))

    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper

def str2bool(s):
    """Convert a string to a boolean"""
    s = s.lower()
    try:
        return BOOL_STRS[s]
    except KeyError:
        raise ValueError, 'Bad value "%s" for boolean string' % s

def die(s):
    """Like Perl's die()"""
    error(s)
    sys.exit(1)

def error(s):
    """Print an error message"""
    print '\n'.join(textwrap.TextWrapper(width=79).wrap('ERROR: %s' % s))

def warning(s):
    """Print a warning message"""
    print '\n'.join(textwrap.TextWrapper(width=79).wrap('WARNING: %s' % s))

# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class DBInstanceConfigItem(object):
    """
    Captures information about a database configuration item read from the
    .sqlcmd file in the user's home directory.
    """
    def __init__(self, aliases, host, database, user, password, type, port):
        self.aliases = aliases
        self.primaryAlias = aliases[0]
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.db_type = type

    def __hash__(self):
        return self.alias.__hash__()

    def __str__(self):
        return 'host=%s, db=%s, type=%s' %\
               (self.host, self.database, self.db_type)

    def __repr__(self):
        return self.__str__()

class Configuration(object):
    """ Data from the .sqlcmd file in the user's home directory"""

    def __init__(self):
        self.__config = {}

    def totalDatabases(self):
        return len(self.__config.keys())

    def loadFile(self, file):
        f = open(file)
        i = 0
        for line in f:
            i += 1
            line = line.strip()
            if (len(line) == 0) or line.startswith('#'):
                continue

            tokens = line.split()
            total = len(tokens)
            if (total != 6) and (total != 7):
                raise ConfigurationError, \
                      'File "%s", line %d: Wrong number of tokens. ' \
                      'Expected 6 or 7, found %d.' %\
                      (file, i, total)

            aliases = tokens[0].split(',')
            if total == 7:
                port = tokens[6]
            else:
                port = None

            try:
                cfg = DBInstanceConfigItem(aliases,
                                           tokens[1],
                                           tokens[2],
                                           tokens[3],
                                           tokens[4],
                                           tokens[5],
                                           port);
            except ValueError, msg:
                raise ConfigurationError, 'File "%s", line %d: %s' %\
                      (file, i, msg)

            for alias in aliases:
                self.__config[alias] = cfg

        f.close()

    def add(self, alias, host, port, database, type, user, password):
        try:
            self.__config[alias]
            raise ValueError, \
                  'Alias "%s" is already in the configuration' % alias
        except KeyError:
            pass

            try:
                cfg = DBInstanceConfigItem([alias],
                                           host,
                                           database,
                                           user,
                                           password,
                                           type,
                                           port)
            except ValueError, msg:
                raise ConfigurationError, \
                      'Error in configuration for alias "%s": %s' % (alias, msg)
            self.__config[alias] = cfg

    def get(self, alias):
        return self.__config[alias]

    def findMatch(self, alias):
        try:
            configItem = self.__config[alias]
            # Exact match. Use that one.
        except KeyError:
            # No match. Try to find one or more that come close.
            matches = 0
            for a in self.__config.keys():
                if a.startswith(alias):
                    configItem = self.__config[a]
                    matches += 1

            if matches == 0:
                raise ConfigurationError, \
                      'No configuration item for database "%s"' % alias
            if matches > 1:
                raise ConfigurationError, \
                      '%d databases match partial alias "%s"' % (matches, alias)

        return configItem

class NonFatalError(Exception):
    """
    Exception indicating a non-fatal error. Intended to be a base class.
    Non-fatal errors are trapped and displayed as error messages within the
    command interpreter.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class NotConnectedError(NonFatalError):
    """
    Thrown to indicate that a SQL operation is attempted when there's no
    active connection to a database.
    """
    def __init__(self, value):
        NonFatalError.__init__(self, value)

class ConfigurationError(NonFatalError):
    """Thrown when bad configuration data is found."""
    def __init__(self, value):
        NonFatalError.__init__(self, value)

class BadCommandError(NonFatalError):
    """Thrown to indicate bad input from the user."""
    def __init__(self, value):
        NonFatalError.__init__(self, value)


class Variable(object):
    """Captures information about a sqlcmd variable."""
    def __init__(self,
                 name,
                 type,
                 initialValue,
                 docstring,
                 onChangeFunc=None):
        self.name = name
        self.type = type
        self.defaultValue = initialValue
        self.value = initialValue
        self.onChange = onChangeFunc
        self.docstring = docstring

    def setValueFromString(self, s):
        new_value = None
        if self.type == SQLCmd.VAR_TYPES.boolean:
            new_value = str2bool(s)

        elif self.type == SQLCmd.VAR_TYPES.string:
            new_value = s

        elif self.type == SQLCmd.VAR_TYPES.integer:
            new_value = int(s)

        else:
            assert(false)

        if new_value != self.value:
            self.value = new_value
            if self.onChange != None:
                self.onChange(self)

    def strValue(self):
        if self.type == SQLCmd.VAR_TYPES.boolean:
            if self.value:
                return "true"
            else:
                return "false"

        if self.type == SQLCmd.VAR_TYPES.string:
            return self.value

        if self.type == SQLCmd.VAR_TYPES.integer:
            return str(self.value)

    def __str__(self):
        return '%s %s = %s' % (self.type, self.name, self.strValue())

    def __hash__(self):
        return self.name.__hash__()


class SQLCmd(Cmd):
    """The SQLCmd command interpreter."""

    DEFAULT_HISTORY_MAX = 512
    COMMENT_PREFIX = '--'
    BINARY_VALUE_MARKER = "<binary>"
    BINARY_FILTER = ''.join([(len(repr(chr(x)))==3) and chr(x) or '?'
                             for x in range(256)])

    NO_SEMI_NEEDED = set()
    NO_SEMI_NEEDED.add('load')
    NO_SEMI_NEEDED.add('connect')
    NO_SEMI_NEEDED.add('h')
    NO_SEMI_NEEDED.add('history')
    NO_SEMI_NEEDED.add('hist')
    NO_SEMI_NEEDED.add('help')
    NO_SEMI_NEEDED.add('?')
    NO_SEMI_NEEDED.add('r')
    NO_SEMI_NEEDED.add('begin')
    NO_SEMI_NEEDED.add('commit')
    NO_SEMI_NEEDED.add('rollback')
    NO_SEMI_NEEDED.add('eof')

    VAR_TYPES = Enum('boolean', 'string', 'integer')

    def __init__(self, cfg):
        Cmd.__init__(self)
        self.prompt = "? "
        self.__config = cfg
        self.__db = None
        self.__partialCommand = None
        self.__partialCmdHistoryStart = None
        self.__dbConfig = None
        self.__historyFile = None
        self.__echoSQL = True
        self.__VARS = {}
        self.__interactive = True
        self.__inMultilineCommand = False
        self.saveHistory = True

        def autocommitChanged(var):
            if var.value == True:
                # Autocommit changed
                db = self.__db
                if db != None:
                    print "Autocommit enabled. Committing current transaction."
                    db.commit()

        vars = [
            Variable('echo',       SQLCmd.VAR_TYPES.boolean, True,
                     'Whether or not SQL statements are echoed.'),
            Variable('timings',    SQLCmd.VAR_TYPES.boolean, True,
                     'Whether or not to show how SQL statements take.'),
            Variable('autocommit', SQLCmd.VAR_TYPES.boolean, True,
                     'Whether SQL statements are auto-committed or not.',
                     autocommitChanged),
            Variable('stacktrace', SQLCmd.VAR_TYPES.boolean, False,
                     'Whether or not to show a stack trace on error.'),
            Variable('showbinary', SQLCmd.VAR_TYPES.boolean, False,
                     'Whether or not to try to display BINARY column values.'),
            Variable('binarymax', SQLCmd.VAR_TYPES.integer, 20,
                     'Number of characters to show in a BINARY column, if '
                     '"showbinary" is "true".'),
               ]
        for v in vars:
            self.__VARS[v.name] = v

    def runFile(self, file):
        self.__loadFile(file)
        self.cmdqueue += ["eof"]
        self.__interactive = False
        self.__prompt = ""
        self.cmdloop()

    def preloop(self):
        # Would use Cmd.intro to put out the introduction, except that
        # preloop() gets called first, and the intro should come out BEFORE
        # the 'Connecting...' message. The other solution would be to override
        # cmdloop(), but putting out the intro manually is simpler.

        print INTRO

        if self.__dbConfig != None:
            self.__connectTo(self.__dbConfig)
        else:
            self.__initHistory()

    def onecmd(self, line):
        stop = False
        try:
            stop = Cmd.onecmd(self, line)
        except NonFatalError, ex:
            error('%s' % str(ex))
            if self.__flagIsSet('stacktrace'):
                traceback.print_exc()
        except db.Warning, ex:
            warning('%s' % str(ex))
        except db.Error, ex:
            error('%s' % str(ex))
            if self.__flagIsSet('stacktrace'):
                traceback.print_exc()
            if self.__db != None: # mostly a hack for PostgreSQL
                try:
                    self.__db.rollback()
                except db.Error:
                    pass
        return stop
        
    def setDatabase(self, databaseAlias):
        assert self.__config != None
        configItem = self.__config.findMatch(databaseAlias)
        assert(configItem != None)
        self.__dbConfig = configItem

    @traced
    def precmd(self, s):
        s = s.strip()
        tokens = s.split(None, 1)
        if len(tokens) == 0:
            return s

        if len(tokens) == 1:
            first = s
        else:
            first = tokens[0]

        if not self.__inMultilineCommand:
            first = first.lower()

        # Done here to simulate what raw inputter does. (That is, if
        # the raw inputter is in use and readline is available, the
        # item will already be in the history by the time the handler
        # is called.)
        self.__history.addItem(s)

        # Now, scrub non-structured comments from the history.

        self.__scrubHistory()

        need_semi = not first in SQLCmd.NO_SEMI_NEEDED;
        if first.startswith(SQLCmd.COMMENT_PREFIX):
            # Comments are handled specially. Rather than transform them
            # into something that'll invoke a "do" method, we handle them
            # directly here, then return an empty string. That way, the
            # Cmd class's help functions don't notice and expose to view
            # special comment methods.

            if len(first) > 2:
                # Structured comment.
                s = ' '.join([first[2:]] + tokens[1:])
                try:
                    self.__handleStructuredComment(s)
                except NonFatalError, ex:
                    error('%s' % str(ex))
                    if self.__flagIsSet('stacktrace'):
                        traceback.print_exc()

            s = ""
            need_semi = False
        elif s == "EOF":
            skip_history = True
            need_semi = False
        else:
            s = ' '.join([first] + tokens[1:])

        if first.startswith('@'):
            if len(first) > 1:
                first = 'load ' + first[1:]
            else:
                first = 'load'
            s = ' '.join([first] + tokens[1:])

        if s == "":
            pass
        elif need_semi and (s[-1] != ';'):
            if self.__partialCommand == None:
                self.__partialCommand = s
                self.__partialCmdHistoryStart = self.__history.getTotal()
            else:
                self.__partialCommand = self.__partialCommand + ' ' + s
            s = ""
            self.prompt = "> "
            self.__inMultilineCommand = True

        else:
            self.__inMultilineCommand = False
            if self.__partialCommand != None:
                s = self.__partialCommand + ' ' + s
                self.__partialCommand = None
                self.__history.cutBack_to(self.__partialCmdHistoryStart)
                self.__partialCmdHistoryStart = None
                self.__history.addItem(s, force=True)

            # Strip the trailing ';'
            if s[-1] == ';':
                s = s[:-1]

            self.prompt = "? "

        return s

    def do_load(self, args):
        """
        Load and run a file full of commands without exiting the command
        shell.

        Usage: load file
               @ file
               @file
        """
        tokens = args.split(None, 1)
        if len(tokens) > 1:
            raise BadCommandError, 'Too many arguments to "load" ("@")'

        try:
            self.__loadFile(tokens[0])
        except IOError, (ex, msg):
            error('Unable to load file "%s": %s' % (tokens[0], msg))

    def do_connect(self, args):
        """
        Close the current database connection, and connect to another
        database.

        Usage: connect database_alias

        where 'database_alias' is a valid database alias from the .sqlcmd
        startup file.
        """
        tokens = args.split(None, 1)
        if len(tokens) > 1:
            raise BadCommandError, 'Too many arguments to "connect"'

        if self.__db != None:
            try:
                self.__db.close()
            except db.Error:
                pass
            self.setDatabase(tokens[0])
            assert(self.__dbConfig != None)
            self.__connectTo(self.__dbConfig)

    def do_h(self, args):
        """
        Show the current command history. Identical to the 'hist' and
        'history' commands.

        Usage: h
        """
        self.__showHistory()

    def do_hist(self, args):
        """
        Show the current command history. Identical to the 'h' command and
        'history' commands.

        Usage: hist
        """
        self.__showHistory()

    def do_history(self, args):
        """
        Show the current command history. Identical to the 'h' command and
        'hist' commands.

        Usage: history
        """
        self.__showHistory()

    def do_r(self, args):
        """
        Re-run a command.

        Usage: r [num]

        where 'num' is the number of the command to re-run, as shown in the
        'history' display. If 'num' is omitted, re-run the most previously
        run command.
        """
        a = args.split()
        if len(a) > 1:
            raise BadCommandError, 'Too many parameters to "r" command.'

        if len(a) == 0:
            # Redo last command.
            line = self.__history.getLastItem()
        else:
            try:
                line = self.__history.getItem(int(a[0]))
            except ValueError:
                line = self.__history.getLastMatchingItem(a[0])

        if line == None:
            print "No match."
        else:
            print line
            # Temporarily turn off SQL echo. If this is a SQL command,
            # we just echoed it, and we don't want it to be echoed twice.

            echo = self.__flagIsSet('echo')
            self.__setVariable('echo', False)
            self.cmdqueue += [line]
            self.__setVariable('echo', echo)

    def do_select(self, args):
        """
        Run a SQL 'SELECT' statement.
        """
        self.__ensureConnected()
        cursor = self.__db.cursor()
        try:
            self.__handleSelect(args, cursor)
        finally:
            cursor.close()
        if self.__flagIsSet('autocommit'):
            self.__db.commit()

    def do_show(self, args):
        """
        Run a SQL 'SELECT' statement.
        """
        self.__ensureConnected()
        cursor = self.__db.cursor()
        try:
            self.__handleSelect(args, cursor, command='show')
        finally:
            cursor.close()
        if self.__flagIsSet('autocommit'):
            self.__db.commit()

    def do_insert(self, args):
        """
        Run a SQL 'INSERT' statement.
        """
        self.__handleUpdate('insert', args)

    def do_update(self, args):
        """
        Run a SQL 'UPDATE' statement.
        """
        self.__handleUpdate('update', args)

    def do_delete(self, args):
        """
        Run a SQL 'DELETE' statement.
        """
        self.__handleUpdate('update', args)

    def do_create(self, args):
        """
        Run a SQL 'CREATE' statement (e.g., 'CREATE TABLE', 'CREATE INDEX')
        """
        self.__handleUpdate('create', args)

    def do_drop(self, args):
        """
        Run a SQL 'DROP' statement (e.g., 'DROP TABLE', 'DROP INDEX')
        """
        self.__handleUpdate('drop', args)

    def do_begin(self, args):
        """
        Begin a SQL transaction. This command is essentially a no-op: It's
        ignored in autocommit mode, and irrelevant when autocommit mode is
        off. It's there primarily for SQL scripts.
        """
        self.__ensureConnected()

    def do_commit(self, args):
        """
        Commit the current transaction. Ignored if 'autocommit' is enabled.
        (Autocommit is enabled by default.)
        """
        self.__ensureConnected()
        if self.__flagIsSet('autocommit'):
            warning('Autocommit is enabled. "commit" ignored')
        else:
            assert self.__db != None
            self.__db.commit()

    def do_rollback(self, args):
        """
        Roll the current transaction back. Ignored if 'autocommit' is enabled.
        (Autocommit is enabled by default.)
        """
        self.__ensureConnected()
        if self.__flagIsSet('autocommit'):
            warning('Autocommit is enabled. "rollback" ignored')
        else:
            assert self.__db != None
            self.__db.rollback()

    def do_desc(self, args):
        """
        Describe a table. Identical to the 'describe' command.

        Usage: desc tablename [full]

        If 'full' is specified, then the tables indexes are displayed
        as well (assuming the underlying DB driver supports retrieving
        index metadata).
        """
        self.do_describe(args)

    def do_describe(self, args):
        """
        Describe a table. Identical to the 'desc' command.

        Usage: describe tablename [full]

        If 'full' is specified, then the tables indexes are displayed
        as well (assuming the underlying DB driver supports retrieving
        index metadata).
        """
        self.__ensureConnected()
        cursor = self.__db.cursor()
        try:
            self.__handleDescribe(args, cursor)
        finally:
            cursor.close()

    def do_EOF(self, args):
        """
        Handles an end-of-file on input.
        """
        if self.__interactive:
            print "\nBye."
            self.__saveHistory()

        if self.__db != None:
            try:
                self.__db.close()
            except db.Warning, ex:
                warning('%s' % str(ex))
            except db.Error, ex:
                error('%s' % str(ex))
        return True

    def do_set(self, args):
        """
        Handles a 'set' command. This command does nothing. It exists
        solely to allow sqlcmd to process SQL scripts for other SQL
        interpreters (e.g., Oracle's SQL*Plus) which do have a 'set'
        command.
        """

    def help_variables(self):
        print """
        There are various variables that control the behavior of sqlcmd.
        These variables are set via a special structured comment syntax;
        that way, SQL scripts that set sqlcmd variables can still be used
        with other SQL interpreters without causing problems.

        Usage: --set var value

        Boolean variables can take the values 'on', 'off', 'true', 'false',
        'yes', 'no', '0' or '1'.

        The list of variables, their types, and their meaning follow:
        """

        name_width = 0
        for v in self.__VARS.values():
            name_width = max(name_width, len(v.name))

        names = self.__VARS.keys()
        names.sort()
        prefix = '        '
        desc_width = 79 - name_width - len(prefix) - 2
        wrapper = textwrap.TextWrapper(width=desc_width)
        for name in names:
            v = self.__VARS[name]
            desc = '(%s) %s Default: %s' %\
                   (v.type, v.docstring, v.defaultValue)
            desc = wrapper.wrap(desc)
            print '%s%-*s  %s' % (prefix, name_width, v.name, desc[0])
            for s in desc[1:]:
                print '%s%-*s  %s' % (prefix, name_width, ' ', s)


    def default(self, s):
        print 'Unknown command: "%s"' % s

    def emptyline(self):
        pass

    def __handleStructuredComment(self, args):
        tokens = args.split()
        if tokens[0] == 'set':
            self.__handleSet(tokens[1:])
        pass

    def __showVars(self):
        width = 0
        for name in self.__VARS.keys():
            width = max(width, len(name))

        vars = [name for name in self.__VARS.keys()]
        vars.sort()
        for name in vars:
            v = self.__VARS[name]
            print '%-*s = %s' % (width, v.name, v.strValue())

    def __handleSet(self, set_args):
        total_args = len(set_args)
        if total_args == 0:
            self.__showVars()
            return

        if total_args != 2:
            raise BadCommandError, 'Incorrect number of arguments'

        varname = set_args[0]
        try:
            var = self.__VARS[varname]
            var.setValueFromString(set_args[1])

        except KeyError:
            raise BadCommandError, 'No such variable: "%s"' % varname

        except ValueError:
                raise BadCommandError, 'Bad argument to "set %s"' % varname

    def __setVariable(self, varname, value):
        var = self.__VARS[varname]
        var.value = value

    def __handleUpdate(self, command, args):
        try:
            cursor = self.__db.cursor()
            self.__execSQL(cursor, '%s %s' % (command, args))
            rows = cursor.rowcount
            if rows == None:
                print "No row count available."
            else:
                pl = ''
                if rows < 0:
                    rows = 0
                if rows != 1:
                    pl = 's'
                print '%d row%s' % (rows, pl)
        except db.Error:
            raise
        else:
            cursor.close()
            if self.__flagIsSet('autocommit'):
                self.__db.commit()

    def __handleSelect(self, args, cursor, command="select"):
        fd, temp = tempfile.mkstemp(".dat", "sqlcmd")
        self.__execSQL(cursor, '%s %s' % (command, args))
        rows = cursor.rowcount
        pl = ""
        if rows != 1:
            pl = "s"
        print "%d row%s\n" % (rows, pl)
        if rows == 0:
            return

        col_names = []
        col_sizes = []
        for col in cursor.description:
            col_names += [col[0]]
            name_size = len(col[0])
            if col[1] == self.__db.BINARY:
                col_sizes += [max(name_size, len(SQLCmd.BINARY_VALUE_MARKER))]
            else:
                col_sizes += [name_size]

        # Write the results (pickled) to a temporary file. We'll iterate
        # through them twice: Once to calculate the column sizes, the
        # second time to display them.

        if rows > 1000:
            print "Processing result set..."

        max_binary = self.__VARS['binarymax'].value
        if max_binary < 0:
            max_binary = sys.maxint

        f = open(temp, "w")
        rs = cursor.fetchone()
        while rs != None:
            cPickle.dump(rs, f)
            i = 0
            for col_value in rs:
                col_info = cursor.description[i]
                type = col_info[1]
                if type == self.__db.BINARY:
                    if self.__flagIsSet('showbinary'):
                        size = len(col_value.translate(SQLCmd.BINARY_FILTER))
                        size = min(size, max_binary)
                    else:
                        size = len(SQLCmd.BINARY_VALUE_MARKER)
                else:
                    size = len(str(col_value))

                col_sizes[i] = max(col_sizes[i], size)
                i += 1

            rs = cursor.fetchone()

        f.close()

        # Now, dump the header with the column names, being sure to
        # honor the padding sizes.

        headers = []
        rules = []
        for i in range(0, len(col_names)):
            headers += ['%-*s' % (col_sizes[i], col_names[i])]
            rules += ['-' * col_sizes[i]]

        print ' '.join(headers)
        print ' '.join(rules)

        # Finally, read back the data and dump it.

        f = open(temp)
        eof = False
        while not eof:
            try:
                rs = cPickle.load(f)
            except EOFError:
                break

            data = []
            i = 0
            for col_value in rs:
                if col_value == None:
                    col_value = "NULL"
                col_info = cursor.description[i]
                type = col_info[1]
                strValue = ""
                format = '%-*s' # left justify
                if type == self.__db.BINARY:
                    if self.__flagIsSet('showbinary'):
                        strValue = col_value.translate(SQLCmd.BINARY_FILTER)
                        if len(strValue) > max_binary:
                            strValue = strValue[:max_binary]
                    else:
                        strValue = SQLCmd.BINARY_VALUE_MARKER

                elif type == self.__db.NUMBER:
                    format = '%*s' # right justify
                    if col_value == "NULL":
                        pass
                    elif (col_value - int(col_value)) == 0:
                        strValue = int(col_value)
                    else:
                        strValue = str(col_value)
                else:
                    strValue = str(col_value)

                data += [format % (col_sizes[i], strValue)]
                i += 1

            print ' '.join(data)

        print ''
        f.close()

        try:
            os.remove(temp)
            os.close(fd)
        except:
            pass

    def __handleDescribe(self, args, cursor):
        a = args.split()
        if not len(a) in (1, 2):
            raise BadCommandError, 'Usage: describe table [full]'

        full = False
        if (len(a) == 2):
            if a[1].lower() != 'full':
                raise BadCommandError, 'Usage: describe table [full]'
            else:
                full = True

        table = a[0]
        results = cursor.getTableMetadata(table)
        width = 0
        for col in results:
            name = col[0]
            width = max(width, len(name))

        header = 'Table %s:' % table
        dashes = '-' * len(header)
        print '\n%s' % dashes
        print '%s' % header
        print '%s\n' % dashes

        for col in results:
            name = col[0]
            type = col[1]
            char_size = col[2]
            precision = col[3]
            scale = col[4]
            nullable = col[5]

            stype = type
            if (char_size != None) and (char_size > 0):
                stype = '%s(%s)' % (type, char_size)
            elif precision != None:
                stype = type
                sep = '('
                if (precision != None) and (precision > 0):
                    stype = stype + sep + str(precision)
                    sep = ', '
                if (scale != None) and (scale > 0):
                    stype = stype + sep + str(scale)
                if sep != '(':
                    stype = stype + ')'

            if nullable == None:
                snull = ''
            elif nullable:
                snull = 'NULL'
            else:
                snull = 'NOT NULL'
            print '%-*s  %s %s' % (width, name, stype, snull)

        if full:
            print '\n--------\nIndexes:\n--------\n'
            indexes = cursor.getIndexMetadata(table)
            if indexes == None:
                print 'No indexes.'
            else:
                width = 0
                for index_data in indexes:
                    width = max(width, len(index_data[0]))

                wrapper = textwrap.TextWrapper(width=79)
                wrapper.subsequent_indent = ' ' * (width + 14)
                sep = None
                for index_data in indexes:
                    name = index_data[0]
                    columns = index_data[1]
                    desc = index_data[2]
                    if sep != None:
                        print sep
                    s = '%-*s Columns:     (%s)' % \
                        (width, name, ', '.join(columns))
                    print '\n'.join(wrapper.wrap(s))
                    if desc:
                        s = '%*s Description: %s' % \
                            (width, ' ', desc)
                        print '\n'.join(wrapper.wrap(s))
                    sep = '---------------------------------------' \
                          '---------------------------------------'
        print ''

    def __execSQL(self, cursor, s):
        if self.__flagIsSet('echo'):
            print s
        start_elapsed = time.time()
        cursor.execute(s)
        end_elapsed = time.time()
        if self.__flagIsSet('timings'):
            total_elapsed = end_elapsed - start_elapsed
            print '\nExecution time: %5.3f seconds'  % total_elapsed

    def __initHistory(self):
        self.__history = history.getHistory()
        self.__history.maxLength = SQLCmd.DEFAULT_HISTORY_MAX
        self.use_rawinput = self.__history.useRawInput()

        if self.__historyFile != None:
            try:
                self.__history.loadHistoryFile(self.__historyFile)
            except IOError:
                pass

    def __flagIsSet(self, varname):
        return self.__VARS[varname].value

    def __saveHistory(self):
        if (self.__historyFile != None) and (self.saveHistory):
            try:
                print 'Saving history file "%s"' % self.__historyFile
                self.__history.saveHistoryFile(self.__historyFile)
            except IOError, (errno, message):
                sys.stderr.write('Unable to save history file "%s": %s\n' % \
                                 (HISTORY_FILE, message))

    def __showHistory(self):
        self.__history.show()

    def __scrubHistory(self):
        self.__history.removeMatches('^' + SQLCmd.COMMENT_PREFIX + r'\s')

    def __loadFile(self, file):
        f = None
        try:
            f = open(file)
            for line in f.readlines():
                if line[-1] == '\n':
                    line = line[:-1] # chop \n
                self.cmdqueue += [line]
        finally:
            if f != None:
                f.close()

    def __connectTo(self, dbConfig):
        if self.__db != None:
            self.__saveHistory()

        driver = db.getDriver(dbConfig.db_type)
        print 'Connecting to %s database "%s" on host %s.' %\
              (driver.displayName, dbConfig.database, dbConfig.host)
        self.__db = driver.connect(host=dbConfig.host,
                                   port=dbConfig.port,
                                   user=dbConfig.user,
                                   password=dbConfig.password,
                                   database=dbConfig.database)

        historyFile = '~/.sqlcmd_%s' % dbConfig.primaryAlias
        self.__historyFile = os.path.expanduser(historyFile)
        self.__initHistory()

    def __ensureConnected(self):
        if self.__db == None:
            raise NotConnectedError, 'Not connected to a database.'

LOG_LEVELS = { 'debug'    : logging.DEBUG,
               'info'     : logging.INFO,
               'warning'  : logging.WARNING,
               'error'    : logging.ERROR,
               'critical' : logging.CRITICAL }

class Main(object):

    def __init__(self):
        pass

    def run(self, argv):
        self.__parseParams(argv)

        # Initialize logging

        self.__initLogging(self.__logLevel, self.__logFile)

        # Load the configuration

        cfg = Configuration()
        try:
            cfg.loadFile(RC_FILE)
        except IOError, ex:
            warning(str(ex))
        except ConfigurationError, ex:
            die(str(ex))

        # Load the history

        try:
            saveHistory = True
            if self.__dbConnectInfo:
                (db, dbType, hp, user, pw) = self.__dbConnectInfo
                host = hp
                port = None
                if ':' in hp:
                    (host, port) = hp.split(':', 2)

                cfg.add("__cmdline__", # alias
                        host,
                        port,
                        db,
                        dbType,
                        user,
                        pw)
                self.__alias = "__cmdline__"
                saveHistory = False

            assert(self.__alias)

            cmd = SQLCmd(cfg)
            cmd.saveHistory = saveHistory
            cmd.setDatabase(self.__alias)
        except ConfigurationError, ex:
            die(str(ex))

        if self.__inputFile:
            try:
                cmd.runFile(self.__inputFile)
            except IOError, (ex, errormsg):
                die('Failed to load file "%s": %s' %\
                    (self.__inputFile, errormsg))
        else:
            cmd.cmdloop()

    def __parseParams(self, argv):
        USAGE = 'Usage: %s [OPTIONS] [alias] [@file]'
        optParser = CommandLineParser(usage=USAGE)
        optParser.addOption('-d', '--db', action='store', dest='database',
                            help='database,dbtype,host[:port],user,password')
        optParser.addOption('-l', '--loglevel', action='store',
                            dest='loglevel',
                            help='Enable log messages as level "n", where ' \
                                 '"n" is one of: %s' % ', '.join(LOG_LEVELS))
        optParser.addOption('-L', '--logfile', action='store', dest='logfile',
                            help='Dump log messages to LOGFILE, instead of ' \
                                 'standard output')
        options, args = optParser.parseArgs(argv)

        args = args[1:]
        if not len(args) in [0, 1]:
            optParser.showUsage('Incorrect number of parameters')

        if options.loglevel:
            if not (options.loglevel in LOG_LEVELS):
                optParser.showUsage('Bad value "%s" for log level.' %\
                                    options.loglevel)

        self.__inputFile = None
        self.__alias = None
        self.__dbConnectInfo = None
        self.__logLevel = options.loglevel
        self.__logFile = options.logfile

        if len(args) == 0:
            pass # handled below
        elif len(args) == 1:
            if args[0].startswith('@'):
                self.__inputFile = args[0][1:]
            else:
                self.__alias = args[0]
        else:
            alias = args[0]
            if not args[1].startswith('@'):
                optParser.showUsage('File parameter must start with "@"')
            self.__inputFile = args[1][1:]

        if options.database:
            self.__dbConnectInfo = options.database.split(',')
            if len(self.__dbConnectInfo) != 5:
                optParser.showUsage('Bad argument "%s" to -d option' %\
                                    options.database)

        if not (self.__dbConnectInfo or self.__alias):
            optParser.showUsage('You must specify either an alias or a '
                                'valid argument to "-d"')

        if self.__dbConnectInfo and self.__alias:
            optParser.showUsage('You cannot specify both an alias and "-d"')

    def __initLogging(self, level, file):
        """Initialize logging subsystem"""
        global log
        log = logging.getLogger('sqlcmd')
        if file == None:
            hdlr = logging.StreamHandler(sys.stdout)
        else:
            hdlr = logging.FileHandler(file)

        if level != None:
            formatter = logging.Formatter('%(asctime)s %(levelname)s '
                                          '(%(name)s) %(message)s', '%T')
            hdlr.setFormatter(formatter)
            root_logger = logging.getLogger(None)
            root_logger.addHandler(hdlr)
            root_logger.setLevel(level)


if __name__ == '__main__':
    main()
    sys.exit(0)