# $Id$

"""
Wrapper for command-line history capability. Hides direct access to
GNU Readline, and provides a simple fallback history mechanism in case
GNU Readline is unavailable.

Stick to the methods in the History class.

$Id$
"""
# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import re
import sys
import logging
import copy

from grizzled.decorators import abstract

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = ['getHistory', 'History', 'DEFAULT_MAXLENGTH']

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAXLENGTH = 512

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

log = logging.getLogger('history')
_have_readline = False
_have_pyreadline = False

try:
    import readline
    _have_readline = True
    
    # Is it pyreadline? If so, it's not quite the same.
    
    try:
        _have_pyreadline = readline.rl.__module__.startswith('pyreadline.')
    except AttributeError:
        pass
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def get_history(using_raw_input=True, verbose=True):
    """
    Factory method to create an appropriate History object.

    @type using_raw_input:  boolean
    @param using_raw_input: C{True} if the caller is using the raw inputter
                          (which automatically uses GNU Readline under
                          the covers, if Readline is available). C{False}
                          otherwise.

    @type verbose:  boolean
    @param verbose: Whether to display the name of the underlying C{History}
                    object
    """
    global _have_readline
    global _have_pyreadline
    result = None
    if _have_pyreadline:
        if verbose:
            print 'Using pyreadline for history management.'
        result = PyReadlineHistory(using_raw_input)

    elif _have_readline:
        if verbose:
            print 'Using readline for history management.'
        result = ReadlineHistory(using_raw_input)

    else:
        if verbose:
            print 'Using simple history package for history management.'
        result = SimpleHistory()

    result.max_length = DEFAULT_MAXLENGTH
    return result

# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class History(object):

    def __init__(self):
        self.set_max_length(DEFAULT_MAXLENGTH)

    def show(self):
        for i in range(1, self.total + 1):
            print '%4d: %s' % (i, self.get_item(i))

    def get_last_matching_item(self, command_name):
        result = None
        for i in range(self.get_total(), 0, -1):
            s = self.get_item(i)
            tokens = s.split(None, 1)
            if len(command_name) <= len(s):
                if s[0:len(command_name)] == command_name:
                    result = s
                    break
        return result

    def get_last_item(self):
        return self.get_item(self.get_total() - 1)

    def get_item(self, index):
        return None

    def set_completer_delims(self, s):
        pass
    
    def get_completer_delims(self):
        return ''

    @property
    def total(self):
        """The total size of the history"""
        return self.get_total()

    def get_total(self):
        return 0

    def __set_max_length(self, n):
        return self.set_max_length(n)

    def __get_max_length(self):
        return self.get_max_length()

    maxLength = property(__get_max_length, __set_max_length,
                         doc="The maximum length of the history")

    @abstract
    def get_max_length(self):
        pass

    @abstract
    def set_max_length(self, n):
        pass

    @abstract
    def add_item(self, line):
        pass

    @abstract
    def remove_item(self, i):
        pass

    def use_raw_input(self):
        return True

    @abstract
    def clear_history(self):
        pass

    def get_history_list(self):
        result = []
        for i in range(1, self.total + 1):
            result += [self.get_item(i)]

        return result

    def remove_matches(self, regexp_string):
        pat = re.compile(regexp_string)
        buf = []

        for i in range(1, self.total + 1):
            s = self.get_item(i)
            if not pat.match(s):
                buf += [s]

        self.replace_history(buf)

    def cut_back_to(self, index):
        if (index > 0) and (index <= self.total):
            buf = []
            for i in range(1, index):
                buf += [self.get_item(i)]

        self.replace_history(buf)

    def replace_history(self, buf):
        self.clear_history()
        for s in buf:
            self.add_item(s, force=True)

    def save_history_file(self, file):
        log.debug('Writing history file "%s"' % file)
        f = open(file, "w")
        for i in range(1, self.total + 1):
            f.write(self.get_item(i) + '\n')
        f.close()

    def load_history_file(self, file):
        log.debug('Loading history file "%s"' % file)
        f = open(file)
        buf = []
        for line in f:
            buf += [line.strip()]
        f.close()

        max = self.get_max_length()
        if len(buf) > max:
            buf = buf[max]
        self.replace_history(buf)

class ReadlineHistory(History):

    def __init__(self, using_raw_input=True):
        global _have_readline
        assert(_have_readline)
        History.__init__(self)
        self.__usingRaw = using_raw_input

    def get_item(self, index):
        return readline.get_history_item(index)

    def get_total(self):
        return readline.get_current_history_length()

    def set_completer_delims(self, s):
        readline.set_completer_delims(s)
    
    def get_completer_delims(self,):
        return readline.get_completer_delims()

    def remove_item(self, index):
        # readline.remove_history_item() doesn't seem to work. Do it the
        # hard way.

        #try:
        #    readline.remove_history_item(i)
        #except ValueError:
        #    pass

        buf = []
        for i in range(1, self.total + 1):
            if i != index:
                buf += self.get_item(i)

        self.clear_history()
        for s in buf:
            readline.add_history(s)

    def clear_history(self):
        try:
            readline.clear_history()
        except AttributeError:
            len = self.get_max_length()
            readline.set_history_length(0)
            readline.set_history_length(len)

    def get_max_length(self):
        return readline.get_history_length()

    def set_max_length(self, n):
        readline.set_history_length(n)

    def add_item(self, line, force=False):
        # If using the raw inputter, then readline has already been
        # called. Otherwise, do it ourselves.
        if force or (not self.__usingRaw):
            readline.add_history(line)

    def use_raw_input(self):
        return self.__usingRaw


class PyReadlineHistory(ReadlineHistory):
    def __init__(self, using_raw_input=True):
        global _have_pyreadline
        assert(_have_pyreadline)
        ReadlineHistory.__init__(self, using_raw_input)

    def get_item(self, index):
        return self.__get_buf()[index - 1].get_line_text()

    def get_total(self):
        return len(self.__get_buf())

    def set_completer_delims(self, s):
        readline.set_completer_delims(s)
    
    def get_completer_delims(self):
        return readline.get_completer_delims()

    def remove_item(self, index):
        buf = copy.deepcopy(self.__get_buf())
        self.clear_history()
        for s in buf:
            readline.add_history(s)

    def clear_history(self):
        readline.clear_history()

    def get_max_length(self):
        return readline.get_history_length()

    def set_max_length(self, n):
        readline.set_history_length(n)

    def add_item(self, line, force=False):
        if force or (not self.use_raw_input()):
            # Kludge. pyreadline is a pain in the ass.
            from pyreadline import lineobj
            from pyreadline.unicode_helper import ensure_unicode

            line = ensure_unicode(line.rstrip())
            readline.add_history(lineobj.ReadLineTextBuffer(line))

    def __get_buf(self):
        return readline.rl._history.history

class SimpleHistory(History):

    def __init__(self):
        History.__init__(self)
        self.__buf = []
        self.__maxLength = sys.maxint
        pass

    def remove_item(self, i):
        try:
            del self.__buf[i - 1]
        except IndexError:
            pass

    def get_item(self, index):
        index -= 1
        try:
            return self.__buf[index]
        except IndexError:
            return None

    def get_history_list(self):
        return copy.deepcopy(self.__buf)

    def get_total(self):
        return len(self.__buf)

    def get_max_length(self):
        return self.__maxLength

    def set_max_length(self, n):
        self.__maxLength = n

    def clear_history(self):
        self.__buf = []

    def add_item(self, line, force=False):
        if len(self.__buf) >= self.__maxLength:
            self.__buf[self.__maxLength - 2:] = []
        self.__buf += [line]
        pass

    def use_raw_input(self):
        return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    h = getHistory()
