#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Id$
"""
sqlcmd - a simple SQL command interpreter

Requires:

- The Grizzled Python API (http://www.clapper.org/software/python/grizzled/)
- One or more Python DB API drivers. See the Grizzled "db" package.
- The enum package, from http://cheeseshop.python.org/pypi/enum/
- Python 2.5 or better

COPYRIGHT AND LICENSE

Copyright © 2008 Brian M. Clapper

This is free software, released under the following BSD-like license:

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. The end-user documentation included with the redistribution, if any,
   must include the following acknowlegement:

      This product includes software developed by Brian M. Clapper
      (bmc@clapper.org, http://www.clapper.org/bmc/). That software is
      copyright © 2008 Brian M. Clapper.

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
import cPickle
import tempfile
import time
import textwrap
import traceback
import logging
import glob
import textwrap
from StringIO import StringIO

from grizzled import db, system
from grizzled.cmdline import CommandLineParser
from grizzled.config import Configuration

# enum is available from http://cheeseshop.python.org/pypi/enum/

from enum import Enum

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

# Info about the module
__version__   = '0.2'
__author__    = 'Brian Clapper'
__email__     = 'bmc@clapper.org'
__url__       = 'http://www.clapper.org/software/python/sqlcmd/'
__copyright__ = '© 1989-2008 Brian M. Clapper'
__license__   = 'BSD-style license'

__all__ = ['SQLCmd', 'main']

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

DEFAULT_CONFIG_DIR = os.path.join(os.environ.get('HOME', os.getcwd()),
                                  '.sqlcmd')

RC_FILE = os.path.join(DEFAULT_CONFIG_DIR, 'config')
HISTORY_FILE_FORMAT = os.path.join(DEFAULT_CONFIG_DIR, '%s.hist')

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

log = None

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def main():
    rc = 0
    try:
        Main().run(sys.argv)

    except KeyboardInterrupt:
        pass

    except:
        rc = 1
        if log:
            log.exception('Error')
        else:
            traceback.print_exc()

    return rc

def str2bool(s):
    """Convert a string to a boolean"""
    s = s.lower()
    try:
        return BOOL_STRS[s]
    except KeyError:
        raise ValueError, 'Bad value "%s" for boolean string' % s

def die(s):
    """Like Perl's die()"""
    log.error(s)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class WrappingLogFormatter(logging.Formatter):
    """
    A log formatter that writes each message and wraps it on line boundaries.
    """
    def __init__(self, format=None, date_format=None, max_width=79):
        """
        Initialize a new ``WrappingLogFormatter``.

        :Parameters:
            format : str
                The format to use, or ``None`` for the logging default

            date_format : str
                Date format

            max_width : int
                Maximum line width
        """
        self.wrapper = textwrap.TextWrapper(width=max_width,
                                            subsequent_indent='    ')
        logging.Formatter.__init__(self, format, date_format)

    def format(self, record):
        s = logging.Formatter.format(self, record)
        result = []
        for line in s.split('\n'):
            result += [self.wrapper.fill(line)]

        return '\n'.join(result)

class DBInstanceConfigItem(object):
    """
    Captures information about a database configuration item read from the
    .sqlcmd file in the user's home directory.
    """
    def __init__(self,
                 section,
                 aliases,
                 host,
                 database,
                 user,
                 password,
                 type,
                 port):
        self.section = section
        self.aliases = aliases
        self.primary_alias = aliases[0]
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.db_type = type

    @property
    def db_key(self):
        port = self.port if self.port else ''
        return '%s|%s|%s|%s' %\
               (self.host, self.db_type, self.port, self.database)

    def __hash__(self):
        return self.primary_alias.__hash__()

    def __str__(self):
        return 'host=%s, db=%s, type=%s' %\
               (self.host, self.database, self.db_type)

    def __repr__(self):
        return self.__str__()

class SQLCmdConfig(object):
    """ Data from the .sqlcmd file in the user's home directory"""

    def __init__(self):
        self.__config = {}

    def total_databases(self):
        return len(self.__config.keys())

    def load_file(self, file):
        if os.access(file, os.R_OK|os.F_OK):
            cfg = Configuration()
            cfg.read(file)

            for section in cfg.sections:
                if section.startswith('db.'):
                    # This is a database configuration.
                    self.__config_db(cfg, section)

                elif section.startswith('driver.'):
                    # Database driver configuration
                    self.__config_driver(cfg, section)

    def __config_db(self, cfg, section):
        primary_name = section[3:] # assumes it starts with 'db.'
        if len(primary_name) == 0:
            raise ConfigurationError, 'Bad database section name "%s"' % section

        aliases = cfg.getlist(section, 'aliases', sep=',', optional=True)
        if aliases:
            aliases = [primary_name] + [a.strip() for a in aliases]
        else:
            aliases = []

        host = cfg.get(section, 'host', optional=True)
        port = cfg.get(section, 'port', optional=True)
        db_name = cfg.get(section, 'database')
        user = cfg.get(section, 'user', optional=True)
        password = cfg.get(section, 'password', optional=True)
        db_type = cfg.get(section, 'type')

        aliases += [db_name]

        try:
            cfg_item = DBInstanceConfigItem(section,
                                            aliases,
                                            host,
                                            db_name,
                                            user,
                                            password,
                                            db_type,
                                            port)
        except ValueError, msg:
            raise ConfigurationError, \
                  'Configuration section [%s]: %s' % (section, msg)

        for alias in aliases:
            self.__config[alias] = cfg_item

    def __config_driver(self, cfg, section):
        class_name = cfg.get(section, 'class')
        cls = system.class_for_name(class_name)
        name = cfg.get(section, 'name')
        db.add_driver(name, cls)

    def add(self, section, alias, host, port, database, type, user, password):
        try:
            self.__config[alias]
            raise ConfigurationError, \
                  'Alias "%s" is already in the configuration' % alias

        except KeyError:
            try:
                cfg = DBInstanceConfigItem(section,
                                           [alias],
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

    def get_aliases(self):
        aliases = self.__config.keys()
        aliases.sort()
        return aliases

    def find_match(self, alias):
        try:
            config_item = self.__config[alias]
            # Exact match. Use that one.
        except KeyError:
            # No match. Try to find one or more that come close.
            matches = {}
            for a in self.__config.keys():
                if a.startswith(alias):
                    config_item = self.__config[a]
                    matches[config_item.db_key] = config_item

            total_matches = len(matches)
            if total_matches == 0:
                raise ConfigurationError, \
                      'No configuration item for database "%s"' % alias
            if total_matches > 1:
                raise ConfigurationError, \
                      '%d databases match partial alias "%s": %s' %\
                      (total_matches, alias, \
                       ', '.join([cfg.section for cfg in matches.values()]))
            config_item = matches.values()[0]

        return config_item

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
    META_COMMAND_PREFIX = '.'
    BINARY_VALUE_MARKER = "<binary>"
    BINARY_FILTER = ''.join([(len(repr(chr(x)))==3) and chr(x) or '?'
                             for x in range(256)])

    NO_SEMI_NEEDED = set()
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
        self.__partial_command = None
        self.__partial_cmd_history_start = None
        self.__db_config = None
        self.__history_file = None
        self.__VARS = {}
        self.__interactive = True
        self.__in_multiline_command = False
        self.save_history = True
        self.identchars = Cmd.identchars + '.'

        def autocommitChanged(var):
            if var.value == True:
                # Autocommit changed
                db = self.__db
                if db != None:
                    print "Autocommit enabled. Committing current transaction."
                    db.commit()

        vars = [
            Variable('echo',       SQLCmd.VAR_TYPES.boolean, False,
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

    def run_file(self, file):
        self.__load_file(file)
        self.cmdqueue += ["EOF"]
        self.__interactive = False
        self.__prompt = ""
        self.cmdloop()

    def preloop(self):
        # Would use Cmd.intro to put out the introduction, except that
        # preloop() gets called first, and the intro should come out BEFORE
        # the 'Connecting...' message. The other solution would be to override
        # cmdloop(), but putting out the intro manually is simpler.

        print INTRO

        if self.__db_config != None:
            self.__connect_to(self.__db_config)
        else:
            self.__init_history()

    def onecmd(self, line):
        stop = False
        try:
            stop = Cmd.onecmd(self, line)
        except NonFatalError, ex:
            log.error('%s' % str(ex))
            if self.__flag_is_set('stacktrace'):
                traceback.print_exc()
        except db.Warning, ex:
            log.warning('%s' % str(ex))
        except db.Error, ex:
            log.error('%s' % str(ex))
            if self.__flag_is_set('stacktrace'):
                traceback.print_exc()
            if self.__db != None: # mostly a hack for PostgreSQL
                try:
                    self.__db.rollback()
                except db.Error:
                    pass
        except:
            raise
        return stop

    def set_database(self, database_alias):
        assert self.__config != None
        config_item = self.__config.find_match(database_alias)
        assert(config_item != None)
        self.__db_config = config_item

    def precmd(self, s):
        s = s.strip()
        tokens = s.split(None, 1)
        if len(tokens) == 0:
            return s

        if len(tokens) == 1:
            first = s
            args = []

        else:
            first = tokens[0]
            args = tokens[1:]

        if not self.__in_multiline_command:
            first = first.lower()

        # Done here to simulate what raw inputter does. (That is, if
        # the raw inputter is in use and readline is available, the
        # item will already be in the history by the time the handler
        # is called.)
        self.__history.add_item(s)

        # Now, scrub non-structured comments from the history.

        self.__scrub_history()

        need_semi = not first in SQLCmd.NO_SEMI_NEEDED;
        if first.startswith(SQLCmd.COMMENT_PREFIX):
            # Comments are handled specially. Rather than transform them
            # into something that'll invoke a "do" method, we handle them
            # directly here, then return an empty string. That way, the
            # Cmd class's help functions don't notice and expose to view
            # special comment methods.
            need_semi = False
            s = ''

        elif first.startswith(SQLCmd.META_COMMAND_PREFIX):
            s = ' '.join(['dot_' + first[1:]] + args)
            need_semi = False

        elif s == "EOF":
            skip_history = True
            need_semi = False

        else:
            s = ' '.join([first] + args)

        if s == "":
            pass

        elif need_semi and (s[-1] != ';'):
            if self.__partial_command == None:
                self.__partial_command = s
                self.__partial_cmd_history_start = self.__history.get_total()
            else:
                self.__partial_command = self.__partial_command + ' ' + s
            s = ""
            self.prompt = "> "
            self.__in_multiline_command = True

        else:
            self.__in_multiline_command = False
            if self.__partial_command != None:
                s = self.__partial_command + ' ' + s
                self.__partial_command = None
                self.__history.cut_back_to(self.__partial_cmd_history_start)
                self.__partial_cmd_history_start = None
                self.__history.add_item(s, force=True)

            # Strip the trailing ';'
            if s[-1] == ';':
                s = s[:-1]

            self.prompt = "? "

        return s

    def completenames(self, text, *ignored):
        """
        Get list of commands, for completion. This version just edits the
        base class's results.
        """
        if text.startswith('.'):
            text = 'dot_' + text[1:]

        commands = Cmd.completenames(self, text, ignored)

        result = []
        for command in commands:
            if command.startswith('dot_'):
                result.append('.' + command[4:])
            else:
                result.append(command)

        return result

    def parseline(self, line):
        """
        Parse the line into a command name and a string containing
        the arguments.  Returns a tuple containing (command, args, line).
        'command' and 'args' may be None if the line couldn't be parsed.

        Overrides the parent class's version of this method, to handle
        dot commands.
        """
        cmd, arg, line = Cmd.parseline(self, line)
        if cmd and cmd.startswith('.'):
            s = 'dot'
            if len(cmd) > 1:
                s += '_%s' % cmd[1:]
            cmd = s

        return cmd, arg, line

    def complete_dot(self, text, line, start_index, end_index):
        return [n for n in self.completenames('') if n.startswith('.')]

    def do_help(self, arg):
        """
        Swiped from the base class and modified.
        """
        if arg:
            # XXX check arg syntax
            if arg.startswith('.'):
                arg = 'dot_' + arg[1:]

            try:
                func = getattr(self, 'help_' + arg)
            except AttributeError:
                try:
                    doc=getattr(self, 'do_' + arg).__doc__
                    if doc:
                        self.stdout.write("%s\n"%str(doc))
                        return
                except AttributeError:
                    pass
                self.stdout.write("%s\n"%str(self.nohelp % (arg,)))
                return
            func()
        else:
            names = self.get_names()
            cmds_doc = []
            cmds_undoc = []
            help = {}
            for name in names:
                if name[:5] == 'help_':
                    help[name[5:]]=1
            names.sort()
            # There can be duplicates if routines overridden
            prevname = ''
            for name in names:
                if name[:3] == 'do_':
                    if name == prevname:
                        continue
                    prevname = name
                    cmd=name[3:]
                    if cmd.startswith('dot_'):
                        cmd = '.' + cmd[4:]
                    if cmd.lower() == 'eof':
                        continue
                    if cmd in help:
                        cmds_doc.append(cmd)
                        del help[cmd]
                    elif getattr(self, name).__doc__:
                        cmds_doc.append(cmd)
                    else:
                        cmds_undoc.append(cmd)
            self.stdout.write("%s\n"%str(self.doc_leader))
            self.print_topics(self.doc_header,   cmds_doc,   15,80)
            self.print_topics(self.misc_header,  help.keys(),15,80)
            self.print_topics(self.undoc_header, cmds_undoc, 15,80)

    def do_redo(self, args):
        """
        Re-run a command.

        Usage: r [num|string]
               redo [num|string]

        where 'num' is the number of the command to re-run, as shown in the
        'history' display. 'string' is a substring to match against the
        command history; for instance, 'r select' attempts to run the
        last command starting with 'select'. If called with no arguments,
        just re-run the last command.
        """
        do_r(args)

    def do_r(self, args):
        """
        Re-run a command.

        Usage: r [num]
               redo [num]

        where 'num' is the number of the command to re-run, as shown in the
        'history' display. 'string' is a substring to match against the
        command history; for instance, 'r select' attempts to run the
        last command starting with 'select'. If called with no arguments,
        just re-run the last command.
        """
        a = args.split()
        if len(a) > 1:
            raise BadCommandError, 'Too many parameters'

        if len(a) == 0:
            # Redo last command.
            line = self.__history.get_last_item()
        else:
            try:
                line = self.__history.get_item(int(a[0]))
            except ValueError:
                line = self.__history.get_last_matching_item(a[0])

        if line == None:
            print "No match."
        else:
            print line

            # Temporarily turn off SQL echo. If this is a SQL command,
            # we just echoed it, and we don't want it to be echoed twice.

            echo = self.__flag_is_set('echo')
            self.__set_variable('echo', False)
            self.cmdqueue += [line]
            self.__set_variable('echo', echo)

    def complete_r(self, text, line, start_index, end_index):
        h = self.__history.get_history_list()
        h.reverse()
        matches = set()
        i = 0
        for command in h:
            i+=1
            if len(command.strip()) == 0:
                continue

            tokens = command.split()
            if len(text) == 0:
                matches.add(tokens[0])
            elif tokens[0].startswith(text):
                matches.add(tokens[0])

        return list(matches)

    def do_select(self, args):
        """
        Run a SQL 'SELECT' statement.
        """
        self.__ensure_connected()
        cursor = self.__db.cursor()
        try:
            self.__handle_select(args, cursor)
        finally:
            cursor.close()
        if self.__flag_is_set('autocommit'):
            self.__db.commit()

    def complete_select(self, text, line, start_index, end_index):
        return self.__complete_tables(text)

    def do_insert(self, args):
        """
        Run a SQL 'INSERT' statement.
        """
        self.__handle_update('insert', args)

    def complete_insert(self, text, line, start_index, end_index):
        return self.__complete_tables(text)

    def do_update(self, args):
        """
        Run a SQL 'UPDATE' statement.
        """
        self.__handle_update('update', args)

    def complete_update(self, text, line, start_index, end_index):
        return self.__complete_tables(text)

    def do_delete(self, args):
        """
        Run a SQL 'DELETE' statement.
        """
        self.__handle_update('delete', args)

    def complete_delete(self, text, line, start_index, end_index):
        return self.__complete_tables(text)

    def do_create(self, args):
        """
        Run a SQL 'CREATE' statement (e.g., 'CREATE TABLE', 'CREATE INDEX')
        """
        self.__handle_update('create', args)

    def complete_create(self, text, line, start_index, end_index):
        return self.__complete_tables(text)

    def do_drop(self, args):
        """
        Run a SQL 'DROP' statement (e.g., 'DROP TABLE', 'DROP INDEX')
        """
        self.__handle_update('drop', args)

    def complete_drop(self, text, line, start_index, end_index):
        return self.__complete_tables(text)

    def do_begin(self, args):
        """
        Begin a SQL transaction. This command is essentially a no-op: It's
        ignored in autocommit mode, and irrelevant when autocommit mode is
        off. It's there primarily for SQL scripts.
        """
        self.__ensure_connected()
        if self.__flag_is_set('autocommit'):
            log.warning('Autocommit is enabled. "begin" ignored')
 
    def do_commit(self, args):
        """
        Commit the current transaction. Ignored if 'autocommit' is enabled.
        (Autocommit is enabled by default.)
        """
        self.__ensure_connected()
        if self.__flag_is_set('autocommit'):
            log.warning('Autocommit is enabled. "commit" ignored')
        else:
            assert self.__db != None
            self.__db.commit()

    def do_rollback(self, args):
        """
        Roll the current transaction back. Ignored if 'autocommit' is enabled.
        (Autocommit is enabled by default.)
        """
        self.__ensure_connected()
        if self.__flag_is_set('autocommit'):
            log.warning('Autocommit is enabled. "rollback" ignored')
        else:
            assert self.__db != None
            self.__db.rollback()

    def do_EOF(self, args):
        """
        Handles an end-of-file on input.
        """
        if self.__interactive:
            print "\nBye."
            self.__save_history()

        if self.__db != None:
            try:
                self.__db.close()
            except db.Warning, ex:
                log.warning('%s' % str(ex))
            except db.Error, ex:
                log.error('%s' % str(ex))
        return True

    def do_set(self, args):
        """
        Handles a 'set' command. This command does nothing. It exists
        solely to allow sqlcmd to process SQL scripts for other SQL
        interpreters (e.g., Oracle's SQL*Plus) which do have a 'set'
        command.
        """
        pass

    def do_dot_set(self, args):
        """
        Handles a 'sset' command, to set a sqlcmd variable. With no arguments,
        this command displays all sqlcmd variables and values.

        Usage: .set [variable value]
        """
        self.__echo('.set', args, add_semi=False)
        set_args = args.split()
        total_args = len(set_args)
        if total_args == 0:
            self.__show_vars()
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

    def complete_dot_set(self, text, line, start_index, end_index):
        tokens = line.split()
        total_tokens = len(tokens)
        if (total_tokens == 1) or ((total_tokens == 2) and (line[-1] != ' ')):
            # .set _
            # or
            # .set v_
            #
            # Complete the things that can be set

            names = self.__VARS.keys()
            names.sort()
            if len(text) == 0:
                matches = names
            else:
                matches = [name for name in names if name.startswith(text)]

        elif (total_tokens == 2) or (total_tokens == 3):
            # .set variable _
            #
            # or
            #
            # .set variable v_
            #
            # So, complete the legal values.

            varname = tokens[1]
            try:
                var = self.__VARS[varname]
                if var.type == SQLCmd.VAR_TYPES.boolean:
                    matches = ['true', 'false']

                elif var.type == SQLCmd.VAR_TYPES.integer:
                    sys.stdout.write('\nEnter a number\n%s' % line)
                    sys.stdout.flush()

                elif var.type == SQLCmd.VAR_TYPES.string:
                    sys.stdout.write('\nEnter a string\n%s' % line)
                    sys.stdout.flush()

                if len(tokens) == 3:
                    matches = [m for m in matches if m.startswith(tokens[2])]
            except KeyError:
                matches = []

        return matches


    def do_dot_h(self, args):
        """
        Show the current command history. Identical to the 'hist' and
        'history' commands.

        Usage: .h
        """
        self.__show_history()

    def do_dot_hist(self, args):
        """
        Show the current command history. Identical to the 'h' command and
        'history' commands.

        Usage: .hist
        """
        self.__show_history()

    def do_dot_history(self, args):
        """
        Show the current command history. Identical to the 'h' command and
        'hist' commands.

        Usage: .history
        """
        self.__show_history()

    def do_dot_show(self, args):
        """
        Run the ".show" command. General form:

            .show arg

        'arg' can be:

        - "tables" to show the list of tables in the database
        """
        if args.lower() == 'tables':
            self.__echo('.show', args, add_semi=False)
            for table in self.__get_tables():
                print table

        else:
            raise BadCommandError, \
                  'Unknown argument(s) to command ".show": %s' % args

    def complete_dot_show(self, text, line, start_index, end_index):
        matches = []
        if len(text) == 0:
            matches = ['tables']
        elif 'tables'.startswith(text):
            matches = ['tables']

        return matches

    def do_dot_desc(self, args):
        """
        Describe a table. Identical to the 'describe' command.

        Usage: .desc tablename [full]

        If 'full' is specified, then the tables indexes are displayed
        as well (assuming the underlying DB driver supports retrieving
        index metadata).
        """
        self.do_dot_describe(args, cmd='.desc')

    def do_dot_describe(self, args, cmd='.describe'):
        """
        Describe a table. Identical to the 'desc' command.

        Usage: .describe tablename [full]

        If 'full' is specified, then the tables indexes are displayed
        as well (assuming the underlying DB driver supports retrieving
        index metadata).
        """
        self.__ensure_connected()
        cursor = self.__db.cursor()
        try:
            self.__handle_describe(cmd, args, cursor)
        finally:
            cursor.close()

    def complete_dot_desc(self, text, line, start_index, end_index):
        return self.__complete_tables(text)

    def complete_dot_describe(self, text, line, start_index, end_index):
        return self.__complete_tables(text)

    def do_dot_load(self, args):
        """
        Load and run a file full of commands without exiting the command
        shell.

        Usage: .load file
        """
        tokens = args.split(None, 1)
        if len(tokens) > 1:
            raise BadCommandError, 'Too many arguments to ".load"'

        try:
            self.__load_file(os.path.expanduser(tokens[0]))
        except IOError, (ex, msg):
            log.error('Unable to load file "%s": %s' % (tokens[0], msg))

    def complete_dot_load(self, text, line, start_index, end_index):
        matches = []
        if text == None:
            text == ''
        text = text.strip()

        if text.startswith('~'):
            text = os.path.expanduser(text)

        if len(text) == 0:
            directory = '.'
            filename = None
            include_directory = False

        elif not (os.path.sep in text):
            directory = '.'
            filename = text
            include_directory = False

        else:
            if os.path.isdir(text) or text[-1] == os.path.sep:
                directory = text
                filename = None
            else:
                directory = os.path.dirname(text)
                filename = os.path.basename(text)
            include_directory = True

        if directory:
            files = os.listdir(directory)
            if filename:
                if filename in files:
                    matches = [filename]
                else:
                    matches = [f for f in files if f.startswith(filename)]

            else:
                matches = files

            if matches:
                matches = [f for f in matches if f[0] != '.']
                if include_directory:
                    matches = [os.path.join(directory, f) for f in matches]

        return matches

    def do_dot_connect(self, args):
        """
        Close the current database connection, and connect to another
        database.

        Usage: .connect database_alias

        where 'database_alias' is a valid database alias from the .sqlcmd
        startup file.
        """
        tokens = args.split(None, 1)
        if len(tokens) > 1:
            raise BadCommandError, 'Too many arguments to "connect"'

        if len(tokens) == 0:
            raise BadCommandError, 'Usage: .connect databasename'

        if self.__db != None:
            try:
                self.__db.close()
            except db.Error:
                pass
            self.set_database(tokens[0])
            assert(self.__db_config != None)
            self.__connect_to(self.__db_config)

    def complete_dot_connect(self, text, line, start_index, end_index):
        aliases = self.__config.get_aliases()
        if len(text.strip()) > 0:
            aliases = [a for a in aliases if a.startswith(text)]

        return aliases

    def help_variables(self):
        print """
        There are various variables that control the behavior of sqlcmd.
        These variables are set via a special structured comment syntax;
        that way, SQL scripts that set sqlcmd variables can still be used
        with other SQL interpreters without causing problems.

        Usage: .set var value

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
        # Pass through to database engine, as if it were a SELECT.
        args = s.split(None, 1)
        command = args[0]
        if len(args) == 1:
            args = ''
        else:
            args = args[1]

        self.__ensure_connected()
        cursor = self.__db.cursor()
        try:
            self.__handle_select(args, cursor, command=command)
        finally:
            cursor.close()
        if self.__flag_is_set('autocommit'):
            self.__db.commit()

    def emptyline(self):
        pass

    def __complete_tables(self, text):
        tables = self.__get_tables()
        if len(text.strip()) > 0:
            tables = [t for t in tables if t.startswith(text)]

        return tables

    def __get_tables(self):
        self.__ensure_connected()
        cursor = self.__db.cursor()

        try:
            tables = cursor.get_tables()
            tables.sort()
            return tables

        finally:
            cursor.close()


    def __show_vars(self):
        width = 0
        for name in self.__VARS.keys():
            width = max(width, len(name))

        vars = [name for name in self.__VARS.keys()]
        vars.sort()
        for name in vars:
            v = self.__VARS[name]
            print '%-*s = %s' % (width, v.name, v.strValue())

    def __set_variable(self, varname, value):
        var = self.__VARS[varname]
        var.value = value

    def __handle_update(self, command, args):
        try:
            cursor = self.__db.cursor()
            self.__exec_SQL(cursor, command, args)
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
            if self.__flag_is_set('autocommit'):
                self.__db.commit()

    def __handle_select(self, args, cursor, command="select"):
        fd, temp = tempfile.mkstemp(".dat", "sqlcmd")
        os.close(fd)

        self.__exec_SQL(cursor, command, args)

        # Don't rely on the row count from the cursor. It isn't always
        # reliable.
        rows, col_names, col_sizes = self.__calculate_column_sizes(cursor, temp)

        pl = ""
        if rows != 1:
            pl = "s"
        print "%d row%s\n" % (rows, pl)

        if rows > 0:
            self.__dump_result_set(rows, col_names, col_sizes, temp, cursor)

    def __dump_result_set(self, rows, col_names, col_sizes, temp, cursor):

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
                    if self.__flag_is_set('showbinary'):
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

    def __calculate_column_sizes(self, cursor, temp_file):
        col_names = []
        col_sizes = []
        rows = 0
        if cursor.description:
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

            if cursor.rowcount > 1000:
                print "Processing result set..."

            max_binary = self.__VARS['binarymax'].value
            if max_binary < 0:
                max_binary = sys.maxint

            f = open(temp_file, "w")
            rs = cursor.fetchone()
            while rs != None:
                cPickle.dump(rs, f)
                i = 0
                rows += 1
                for col_value in rs:
                    col_info = cursor.description[i]
                    type = col_info[1]
                    if type == self.__db.BINARY:
                        if self.__flag_is_set('showbinary'):
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

        return (rows, col_names, col_sizes)

    def __handle_describe(self, cmd, args, cursor):
        self.__echo(cmd, args)
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
        results = cursor.get_table_metadata(table)
        width = 0
        for col in results:
            name = col[0]
            width = max(width, len(name))

        header = 'Table %s:' % table
        dashes = '-' * len(header)
        print '%s' % dashes
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
            indexes = cursor.get_index_metadata(table)
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

    def __exec_SQL(self, cursor, sql_command, args):
        self.__echo(sql_command, args)
        start_elapsed = time.time()
        cursor.execute(' '.join([sql_command, args]))
        end_elapsed = time.time()
        if self.__flag_is_set('timings'):
            total_elapsed = end_elapsed - start_elapsed
            print 'Execution time: %5.3f seconds'  % total_elapsed

    def __init_history(self):
        self.__history = history.get_history()
        self.__history.max_length = SQLCmd.DEFAULT_HISTORY_MAX
        self.use_rawinput = self.__history.use_raw_input()

        completer_delims = self.__history.get_completer_delims()
        new_delims = ''
        for c in completer_delims:
            if c not in ['~', '/']:
                new_delims += c

        self.__history.set_completer_delims(new_delims)

        if self.__history_file != None:
            try:
                print 'Loading history file "%s"' % self.__history_file
                self.__history.load_history_file(self.__history_file)
            except IOError:
                pass

    def __echo(self, *args, **kw):
        if self.__flag_is_set('echo'):
            semi = ''
            if kw.get('add_semi', True):
                semi = ';'

            cmd = ' '.join([a for a in args]).strip()
            print '\n%s%s\n' % (cmd, semi)

    def __flag_is_set(self, varname):
        return self.__VARS[varname].value

    def __save_history(self):
        if (self.__history_file != None) and (self.save_history):
            try:
                print 'Saving history file "%s"' % self.__history_file
                self.__history.save_history_file(self.__history_file)
            except IOError, (errno, message):
                sys.stderr.write('Unable to save history file "%s": %s\n' % \
                                 (HISTORY_FILE, message))

    def __show_history(self):
        self.__history.show()

    def __scrub_history(self):
        self.__history.remove_matches('^' + SQLCmd.COMMENT_PREFIX + r'\s')

    def __load_file(self, file):
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

    def __connect_to(self, db_config):
        if self.__db != None:
            self.__save_history()

        driver = db.get_driver(db_config.db_type)
        print 'Connecting to %s database "%s" on host %s.' %\
              (driver.display_name, db_config.database, db_config.host)
        self.__db = driver.connect(host=db_config.host,
                                   port=db_config.port,
                                   user=db_config.user,
                                   password=db_config.password,
                                   database=db_config.database)

        history_file = HISTORY_FILE_FORMAT % db_config.primary_alias
        self.__history_file = os.path.expanduser(history_file)
        self.__init_history()

    def __ensure_connected(self):
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
        self.__parse_params(argv)

        # Initialize logging

        self.__init_logging(self.__log_level, self.__log_file)

        # Load the configuration

        cfg = SQLCmdConfig()
        try:
            cfg.load_file(self.__config_file)
        except IOError, ex:
            log.warning(str(ex))
        except ConfigurationError, ex:
            die(str(ex))

        # Load the history

        try:
            save_history = True
            if self.__db_connect_info:
                (db, dbType, hp, user, pw) = self.__db_connect_info
                host = hp
                port = None
                if ':' in hp:
                    (host, port) = hp.split(':', 2)

                cfg.add("__cmdline__", # dummy section name
                        "__cmdline__", # alias
                        host,
                        port,
                        db,
                        dbType,
                        user,
                        pw)
                self.__alias = "__cmdline__"
                save_history = False

            assert(self.__alias)

            cmd = SQLCmd(cfg)
            cmd.save_history = save_history
            cmd.set_database(self.__alias)
        except ConfigurationError, ex:
            die(str(ex))

        if self.__input_file:
            try:
                cmd.run_file(self.__input_file)
            except IOError, (ex, errormsg):
                die('Failed to load file "%s": %s' %\
                    (self.__input_file, errormsg))
        else:
            cmd.cmdloop()

    def __parse_params(self, argv):
        USAGE = 'Usage: %prog [OPTIONS] [alias] [@file]'
        opt_parser = CommandLineParser(usage=USAGE)
        opt_parser.add_option('-c', '--config', action='store', dest='config',
                              default=RC_FILE,
                              help='Specifies the configuration file to use. '
                                   'Defaults to "%default".')
        opt_parser.add_option('-d', '--db', action='store', dest='database',
                              help='Database to use. Format: '
                                    'database,dbtype,host[:port],user,password')
        opt_parser.add_option('-l', '--loglevel', action='store',
                              dest='loglevel',
                              help='Enable log messages as level "n", where ' \
                                   '"n" is one of: %s' % ', '.join(LOG_LEVELS),
                              default='info')
        opt_parser.add_option('-L', '--logfile', action='store', dest='logfile',
                              help='Dump log messages to LOGFILE, instead of ' \
                                   'standard output')
        options, args = opt_parser.parse_args(argv)

        args = args[1:]
        if not len(args) in (0, 1, 2):
            opt_parser.show_usage('Incorrect number of parameters')

        if options.loglevel:
            if not (options.loglevel in LOG_LEVELS):
                opt_parser.showUsage('Bad value "%s" for log level.' %\
                                    options.loglevel)

        self.__input_file = None
        self.__alias = None
        self.__db_connect_info = None
        self.__log_level = LOG_LEVELS[options.loglevel]
        self.__log_file = options.logfile
        self.__config_file = options.config

        if len(args) == 0:
            pass # handled below

        elif len(args) == 1:
            if args[0].startswith('@'):
                self.__input_file = args[0][1:]
            else:
                self.__alias = args[0]
        else:
            self.__alias = args[0]
            if not args[1].startswith('@'):
                opt_parser.show_usage('File parameter must start with "@"')
            self.__input_file = args[1][1:]

        if options.database:
            self.__db_connect_info = options.database.split(',')
            if len(self.__db_connect_info) != 5:
                opt_parser.show_usage('Bad argument "%s" to -d option' %\
                                     options.database)

        if not (self.__db_connect_info or self.__alias):
            opt_parser.show_usage('You must specify either an alias or a '
                                 'valid argument to "-d"')

        if self.__db_connect_info and self.__alias:
            opt_parser.show_usage('You cannot specify both an alias and "-d"')

    def __init_logging(self, level, filename):
        """Initialize logging subsystem"""
        date_format = '%H:%M:%S'

        stderr_handler = logging.StreamHandler(sys.stderr)
        formatter = WrappingLogFormatter(format='%(levelname)s: %(message)s')
        stderr_handler.setLevel(logging.WARNING)
        stderr_handler.setFormatter(formatter)
        handlers = [stderr_handler]

        if filename:
            file_handler = logging.FileHandler(filename)
            handlers.append(file_handler)

            msg_format  = '%(asctime)s %(levelname)s (%(name)s) %(message)s'
            formatter = WrappingLogFormatter(format=msg_format,
                                             date_format=date_format)
            if level == None:
                level = logging.WARNING

            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)

        global log
        log = logging.getLogger('sqlcmd')

        root_logger = logging.getLogger('')
        root_logger.handlers = handlers

if __name__ == '__main__':
    sys.exit(main())
