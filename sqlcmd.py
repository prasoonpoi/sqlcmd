"""
sqlcmd - a simple SQL command interpreter
$Id$

Requires:

- One or more Python DB API drivers. See 'db.py'
- The enum package, from http://cheeseshop.python.org/pypi/enum/
- Python 2.3 or better
"""
from cmd import Cmd
import sys
import os.path
import os
import history
import db
import cPickle
import tempfile
import time
import textwrap
import traceback
from getopt import getopt, GetoptError

# enum is available from http://cheeseshop.python.org/pypi/enum/

from enum import Enum

__all__ = ['SQLCmd']

# Use the built-in 'set' type if using Python 2.4 or better. Otherwise, use
# the old sets module.
try:
    set
except NameError:
    from sets import Set as set, ImmutableSet as frozenset

# ---------------------------------------------------------------------------

RC_FILE = os.path.expanduser("~/.sqlcmd")
VERSION = "0.2"
INTRO = '''SQLCmd, version %s ($Revision$)
Copyright (c) 2008 Brian M. Clapper.

Type "help" or "?" for help.
''' % VERSION

# ---------------------------------------------------------------------------

BOOL_STRS = { "on"    : True,
              "off"   : False,
              "yes"   : True,
              "no"    : False,
              "1"     : True,
              "0"     : False,
              "true"  : True,
              "false" : False }

def traced(func):
    def wrapper(*__args,**__kw):
        print "[%s] entering %s" % (time.strftime('%H:%M:%S'), func)
        try:
            return func(*__args,**__kw)
        finally:
            print "[%s] exiting %s" % (time.strftime('%H:%M:%S'), func)

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

class DBInstanceConfigItem(object):
    """
    Captures information about a database configuration item read from the
    .sqlcmd file in the user's home directory.
    """
    def __init__(self, aliases, host, database, user, password, type, port):
	self.aliases = aliases
	self.primary_alias = aliases[0]
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

    def total_databases(self):
        return len(self.__config.keys())

    def load_file(self, file):
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

    def find_match(self, alias):
	try:
	    config_item = self.__config[alias]
            # Exact match. Use that one.
	except KeyError:
            # No match. Try to find one or more that come close.
            matches = 0
            for a in self.__config.keys():
                if a.startswith(alias):
                    config_item = self.__config[a]
                    matches += 1

            if matches == 0:
                raise ConfigurationError, \
                      'No configuration item for database "%s"' % alias
            if matches > 1:
                raise ConfigurationError, \
                      '%d databases match partial alias "%s"' % (matches, alias)

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
                 initial_value,
                 docstring,
                 on_change_func=None):
        self.name = name
        self.type = type
        self.default_value = initial_value
        self.value = initial_value
        self.on_change = on_change_func
        self.docstring = docstring

    def set_value_from_string(self, s):
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
            if self.on_change != None:
                self.on_change(self)
        
    def str_value(self):
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
        return '%s %s = %s' % (self.type, self.name, self.str_value())

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
	self.__partial_cmd = None
	self.__partial_cmd_history_start = None
        self.__db_config = None
        self.__history_file = None
        self.__echo_sql = True
        self.__VARS = {}
        self.__interactive = True
        self.__in_multiline_command = False
        self.save_history = True

        def autocommit_changed(var):
            if var.value == True:
                # Autocommit changed
                db = self.__db
                print db
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
                     autocommit_changed),
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

        if self.__db_config != None:
            self.__connect_to(self.__db_config)
        else:
            self.__init_history()

    def onecmd(self, line):
        stop = False
	try:
	    stop = Cmd.onecmd(self, line)
	except NonFatalError, ex:
	    error('%s' % str(ex))
            if self.__flag_is_set('stacktrace'):
                traceback.print_exc()
        except db.Warning, ex:
	    warning('%s' % str(ex))
        except db.Error, ex:
	    error('%s' % str(ex))
            if self.__flag_is_set('stacktrace'):
                traceback.print_exc()
            if self.__db != None: # mostly a hack for PostgreSQL
                try:
                    self.__db.rollback()
                except db.Error:
                    pass
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
        else:
            first = tokens[0]

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

            if len(first) > 2:
                # Structured comment.
                s = ' '.join([first[2:]] + tokens[1:])
                try:
                    self.__handle_structured_comment(s)
                except NonFatalError, ex:
                    error('%s' % str(ex))
                    if self.__flag_is_set('stacktrace'):
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
	    if self.__partial_cmd == None:
		self.__partial_cmd = s
		self.__partial_cmd_history_start = self.__history.get_total()
	    else:
		self.__partial_cmd = self.__partial_cmd + ' ' + s
	    s = ""
	    self.prompt = "> "
            self.__in_multiline_command = True

	else:
            self.__in_multiline_command = False
	    if self.__partial_cmd != None:
		s = self.__partial_cmd + ' ' + s
		self.__partial_cmd = None
		self.__history.cut_back_to(self.__partial_cmd_history_start)
		self.__partial_cmd_history_start = None
		self.__history.add_item(s, force=True)

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
            self.__load_file(tokens[0])
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
            self.set_database(tokens[0])
            assert(self.__db_config != None)
            self.__connect_to(self.__db_config)

    def do_h(self, args):
        """
        Show the current command history. Identical to the 'hist' and
        'history' commands.

        Usage: h
        """
	self.__show_history()

    def do_hist(self, args):
        """
        Show the current command history. Identical to the 'h' command and
        'history' commands.

        Usage: hist
        """
	self.__show_history()

    def do_history(self, args):
        """
        Show the current command history. Identical to the 'h' command and
        'hist' commands.

        Usage: history
        """
	self.__show_history()

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
            self.__set_var('echo', False)
	    self.cmdqueue += [line]
            self.__set_var('echo', echo)

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

    def do_show(self, args):
	"""
        Run a SQL 'SELECT' statement.
        """
        self.__ensure_connected()
	cursor = self.__db.cursor()
        try:
            self.__handle_select(args, cursor, command='show')
        finally:
            cursor.close()
        if self.__flag_is_set('autocommit'):
            self.__db.commit()

    def do_insert(self, args):
	"""
        Run a SQL 'INSERT' statement.
        """
        self.__handle_update('insert', args)

    def do_update(self, args):
	"""
        Run a SQL 'UPDATE' statement.
        """
        self.__handle_update('update', args)

    def do_delete(self, args):
	"""
        Run a SQL 'DELETE' statement.
        """
        self.__handle_update('update', args)

    def do_create(self, args):
	"""
        Run a SQL 'CREATE' statement (e.g., 'CREATE TABLE', 'CREATE INDEX')
        """
        self.__handle_update('create', args)

    def do_drop(self, args):
	"""
        Run a SQL 'DROP' statement (e.g., 'DROP TABLE', 'DROP INDEX')
        """
        self.__handle_update('drop', args)

    def do_begin(self, args):
	"""
        Begin a SQL transaction. This command is essentially a no-op: It's
        ignored in autocommit mode, and irrelevant when autocommit mode is
        off. It's there primarily for SQL scripts.
        """
        self.__ensure_connected()

    def do_commit(self, args):
        """
        Commit the current transaction. Ignored if 'autocommit' is enabled.
        (Autocommit is enabled by default.)
        """
        self.__ensure_connected()
        if self.__flag_is_set('autocommit'):
            warning('Autocommit is enabled. "commit" ignored')
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
        self.__ensure_connected()
        cursor = self.__db.cursor()
        try:
            self.__handle_describe(args, cursor)
        finally:
            cursor.close()

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
                   (v.type, v.docstring, v.default_value)
            desc = wrapper.wrap(desc)
            print '%s%-*s  %s' % (prefix, name_width, v.name, desc[0])
            for s in desc[1:]:
                print '%s%-*s  %s' % (prefix, name_width, ' ', s)
                

    def default(self, s):
	print 'Unknown command: "%s"' % s

    def emptyline(self):
	pass

    def __handle_structured_comment(self, args):
        tokens = args.split()
        if tokens[0] == 'set':
            self.__handle_set(tokens[1:])
	pass

    def __show_vars(self):
        width = 0
        for name in self.__VARS.keys():
            width = max(width, len(name))

        vars = [name for name in self.__VARS.keys()]
        vars.sort()
        for name in vars:
            v = self.__VARS[name]
            print '%-*s = %s' % (width, v.name, v.str_value())

    def __handle_set(self, set_args):
        total_args = len(set_args)
        if total_args == 0:
            self.__show_vars()
            return

        if total_args != 2:
            raise BadCommandError, 'Incorrect number of arguments'

        varname = set_args[0]
        try:
            var = self.__VARS[varname]
            var.set_value_from_string(set_args[1])

        except KeyError:
            raise BadCommandError, 'No such variable: "%s"' % varname

        except ValueError:
                raise BadCommandError, 'Bad argument to "set %s"' % varname

    def __set_var(self, varname, value):
        var = self.__VARS[varname]
        var.value = value

    def __handle_update(self, command, args):
        try:
            cursor = self.__db.cursor()
            self.__exec_sql(cursor, '%s %s' % (command, args))
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
        self.__exec_sql(cursor, '%s %s' % (command, args))
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
                str_value = ""
                format = '%-*s' # left justify
                if type == self.__db.BINARY:
                    if self.__flag_is_set('showbinary'):
                        str_value = col_value.translate(SQLCmd.BINARY_FILTER)
                        if len(str_value) > max_binary:
                            str_value = str_value[:max_binary]
                    else:
                        str_value = SQLCmd.BINARY_VALUE_MARKER

                elif type == self.__db.NUMBER:
                    format = '%*s' # right justify
                    if col_value == "NULL":
                        pass
                    elif (col_value - int(col_value)) == 0:
                        str_value = int(col_value)
                    else:
                        str_value = str(col_value)
                else:
                    str_value = str(col_value)

                data += [format % (col_sizes[i], str_value)]
                i += 1

            print ' '.join(data)

        print ''
        f.close()

	try:
	    os.remove(temp)
            os.close(fd)
	except:
	    pass

    def __handle_describe(self, args, cursor):
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

    def __exec_sql(self, cursor, s):
        if self.__flag_is_set('echo'):
            print s
        start_elapsed = time.time()
        cursor.execute(s)
        end_elapsed = time.time()
        if self.__flag_is_set('timings'):
            total_elapsed = end_elapsed - start_elapsed
            print '\nExecution time: %5.3f seconds'  % total_elapsed

    def __init_history(self):
	self.__history = history.get_history()
	self.__history.set_max_length(SQLCmd.DEFAULT_HISTORY_MAX)
	self.use_rawinput = self.__history.use_raw_input()

        if self.__history_file != None:
            try:
                self.__history.load_history_file(self.__history_file)
            except IOError:
                pass

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

	print 'Connecting to %s database "%s" on host %s.' %\
	      (db_config.db_type, db_config.database, db_config.host)
        driver = db.get_driver(db_config.db_type)
	self.__db = driver.connect(host=db_config.host,
                                   port=db_config.port,
                                   user=db_config.user,
                                   password=db_config.password,
                                   database=db_config.database)

	history_file = '~/.sqlcmd_%s' % db_config.primary_alias
	self.__history_file = os.path.expanduser(history_file)
	self.__init_history()

    def __ensure_connected(self):
        if self.__db == None:
            raise NotConnectedError, 'Not connected to a database.'

# ---------------------------------------------------------------------------

def usage(msg=None):
    if msg:
        sys.stderr.write(msg + '\n\n')

    sys.stderr.write \
    ('''Usage: %s [OPTIONS] [alias] [@file]

where "alias" is a database alias loaded from "%s/.sqlcmd"
"alias" must be omitted if -d is specified.
If "@file" is specified, it is assumed to contain SQL statements to be run.

OPTIONS

-d   database,dbtype,host[:port],user,password       -or-
--db database,dbtype,host[:port],user,password

''' % (os.path.basename(sys.argv[0]), os.environ["HOME"]))
    sys.exit(1)

class Args(object):
    pass

def parse_params(argv):
    try:
        opts, args = getopt(argv, 'd:', ['db=']);

    except GetoptError, ex:
        sys.stderr.write(`ex` + '\n')
        usage()

    if not len(args) in [0, 1, 2]:
        usage()

    result = Args()
    result.db_on_command_line = False
    arg_db = None
    for o, a in opts:
        if o in ("--db", "-d"):
            arg_db = a.split(',')
            if len(arg_db) != 5:
                usage("Not enough tokens in argument to -d option\n")
            
            result.db_on_command_line = True
            result.database = arg_db[0]
            result.database_type = arg_db[1]
            result.port = None
            h = arg_db[2].split(':')
            if len(h) > 1:
                result.port = h[1]
            result.host = h[0]
            result.user = arg_db[3]
            result.password = arg_db[4]
            continue

    result.alias = None
    result.file = None
    if len(args) == 0:
        pass # handled below
    elif len(args) == 1:
        if args[0].startswith('@'):
            result.file = args[0][1:]
        else:
            result.alias = args[0]
    else:
        result.alias = args[0]
        if not args[1].startswith('@'):
            usage('File parameter must start with "@"')
        result.file = args[1][1:]

    if not (result.db_on_command_line or result.alias):
        usage('You must specify either an alias or a valid argument to "-d"')

    if result.db_on_command_line and result.alias:
        usage('You cannot specify both an alias and "-d"')

    return result

if __name__ == "__main__":

    params = parse_params(sys.argv[1:])

    cfg = Configuration()
    try:
        cfg.load_file(RC_FILE)
    except IOError, ex:
        warning(str(ex))
    except ConfigurationError, ex:
        die(str(ex))

    try:
        save_history = True
        if params.db_on_command_line:
            cfg.add("__cmdline__", # alias
                    params.host,
                    params.port,
                    params.database,
                    params.database_type,
                    params.user,
                    params.password)
            params.alias = "__cmdline__"
            save_history = False

        assert(params.alias)

        cmd = SQLCmd(cfg)
        cmd.save_history = save_history
    except ConfigurationError, ex:
        die(str(ex))

    cmd.set_database(params.alias)
    if params.file:
        try:
            cmd.run_file(params.file)
        except IOError, (ex, errormsg):
            die('Failed to load file "%s": %s' % (params.file, errormsg))
    else:
        cmd.cmdloop()

    sys.exit(0)
