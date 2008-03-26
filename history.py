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
haveReadline = False

try:
    import readline
    haveReadline = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def getHistory(usingRawInput=True, verbose=True):
    """
    Factory method to create an appropriate History object.

    @type usingRawInput:  boolean
    @param usingRawInput: C{True} if the caller is using the raw inputter
                          (which automatically uses GNU Readline under
                          the covers, if Readline is available). C{False}
                          otherwise.

    @type verbose:  boolean
    @param verbose: Whether to display the name of the underlying C{History}
                    object
    """
    global haveReadline
    result = None
    if haveReadline:
        if verbose:
            print 'Using readline for history management.'
        result = ReadlineHistory(usingRawInput)
    else:
        if verbose:
            print 'Using simple history package for history management.'
        result = SimpleHistory()

    result.maxLength = DEFAULT_MAXLENGTH
    return result

# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class History(object):

    def show(self):
	for i in range(1, self.total + 1):
	    print '%4d: %s' % (i, self.getItem(i))

    def saveHistoryFile(self, file):
	pass

    def loadHistoryFile(self, file):
	pass

    def getLastMatchingItem(self, command_name):
	result = None
	for i in range(self.get_total(), 0, -1):
	    s = self.get_item(i)
	    tokens = s.split(None, 1)
	    if len(command_name) <= len(s):
		if s[0:len(command_name)] == command_name:
		    result = s
		    break
	return result

    def getLastItem(self):
	return self.getItem(self.get_total() - 1)

    def getItem(self, index):
	return None

    @property
    def total(self):
        """The total size of the history"""
        return self.getTotal()

    def getTotal(self):
	return 0

    def __setMaxLength(self, n):
        return self.setMaxLength(n)

    def __getMaxLength(self):
        return self.getMaxLength()

    maxLength = property(__getMaxLength, __setMaxLength,
                          doc="The maximum length of the history")

    @abstract
    def getMaxLength(self):
	pass

    @abstract
    def setMaxLength(self, n):
	pass

    @abstract
    def addItem(self, line):
        pass

    @abstract
    def removeItem(self, i):
        pass

    def useRawInput(self):
	return True

    @abstract
    def clearHistory(self):
        pass

    def removeMatches(self, regexp_string):
	pat = re.compile(regexp_string)
	buf = []

	for i in range(1, self.total + 1):
	    s = self.getItem(i)
	    if not pat.match(s):
		buf += [s]

	self.replaceHistory(buf)

    def cutBackTo(self, index):
	if (index > 0) and (index <= self.total):
	    buf = []
	    for i in range(1, index):
		buf += [self.getItem(i)]

	self.replaceHistory(buf)

    def replaceHistory(self, buf):
	self.clearHistory()
	for s in buf:
	    self.addItem(s, force=True)

    def saveHistoryFile(self, file):
        log.debug('Writing history file "%s"' % file)
	f = open(file, "w")
	for i in range(1, self.total + 1):
	    f.write(self.getItem(i) + '\n')
	f.close()

    def loadHistoryFile(self, file):
        log.debug('Loading history file "%s"' % file)
	f = open(file)
        buf = []
	for line in f:
            buf += [line.strip()]
	f.close()

        if len(buf) > self.maxLength:
            buf = buf[-self.maxLength:]
        self.replaceHistory(buf)

class ReadlineHistory(History):

    def __init__(self, usingRawInput=True):
	global haveReadline
	assert(haveReadline)
	History.__init__(self)
	self.__usingRaw = usingRawInput

    def getItem(self, index):
	return readline.get_history_item(index)

    def getTotal(self):
	return readline.get_current_history_length()

    def removeItem(self, index):
	# readline.remove_history_item() doesn't seem to work. Do it the
	# hard way.

	#try:
	#    readline.remove_history_item(i)
	#except ValueError:
	#    pass

	buf = []
	for i in range(1, self.total + 1):
	    if i != index:
		buf += self.getItem(i)

	readline.clearHistory()
	for s in buf:
	    readline.add_history(s)

    def clearHistory(self):
	readline.clear_history()

    def getMaxLength(self):
	return readline.get_history_length()

    def setMaxLength(self, n):
	readline.set_history_length(n)

    def addItem(self, line, force=False):
	# If using the raw inputter, then readline has already been
	# called. Otherwise, do it ourselves.
	if force or (not self.__usingRaw):
	    readline.add_history(line)

    def useRawInput(self):
	return self.__usingRaw


class SimpleHistory(History):

    def __init__(self):
	History.__init__(self)
	self.__buf = []
	self.__maxLength = sys.maxint
	pass

    def removeItem(self, i):
	try:
	    del self.__buf[i - 1]
	except IndexError:
	    pass

    def getItem(self, index):
	index -= 1
	try:
	    return self.__buf[index]
	except IndexError:
	    return None

    def getTotal(self):
	return len(self.__buf)

    def getMaxLength(self):
	return self.__maxLength

    def setMaxLength(self, n):
	self.__maxLength = n

    def clearHistory(self):
	self.__buf = []

    def addItem(self, line, force=False):
	if len(self.__buf) >= self.__maxLength:
	    self.__buf[self.__maxLength - 2:] = []
	self.__buf += [line]
	pass

    def useRawInput(self):
	return False

if __name__ == "__main__":
    h = getHistory()
