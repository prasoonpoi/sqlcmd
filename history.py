"""
Wrapper for command-line history capability. Hides direct access to
GNU Readline, and provides a simple fallback history mechanism in case
GNU Readline is unavailable.

Stick to the methods in the History class.

$Id$
"""
import re
import sys
import logging

__all__ = ['get_history', 'History', 'DEFAULT_MAX_LENGTH', 'logger']

logger = logging.getLogger('history')
DEFAULT_MAX_LENGTH = 512

have_readline = False
try:
    import readline
    have_readline = True
except ImportError:
    pass

def get_history(using_raw_inputter=True, verbose=True):
    """
    Factory method to create an appropriate History object.

    Parameters:

        using_raw_inputter - True if the caller is using the raw inputter
                             (which automatically uses GNU Readline under
                             the covers, if Readline is available). False
                             otherwise.
        verbose            - Whether to display which underlying History
                             object is being used.
    """
    global have_readline
    result = None
    if have_readline:
        if verbose:
            print 'Using readline for history management.'
        result = ReadlineHistory(using_raw_inputter)
    else:
        if verbose:
            print 'Using simple history package for history management.'
        result = SimpleHistory()

    result.max_length = DEFAULT_MAX_LENGTH
    return result

class History(object):

    def show(self):
	for i in range(1, self.get_total() + 1):
	    print '%4d: %s' % (i, self.get_item(i))

    def save_history_file(self, file):
	pass

    def load_history_file(self, file):
	pass

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

    def __get_total(self):
        return self.get_total()

    total = property(__get_total, doc="Get the total size of the history")

    def get_total(self):
	return 0

    def __set_max_length(self, n):
        return self.set_max_length(n)

    def __get_max_length(self):
        return self.get_max_length()

    max_length = property(__get_max_length, __set_max_length,
                          doc="The maximum length of the history")

    def get_max_length(self):
	raise NotImplementedError

    def set_max_length(self, n):
	raise NotImplementedError

    def add_item(self, line):
	raise NotImplementedError

    def remove_item(self, i):
	raise NotImplementedError

    def use_raw_input(self):
	return True

    def clear_history(self):
	raise NotImplementedError

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
        logger.debug('Writing history file "%s"' % file)
	f = open(file, "w")
	for i in range(1, self.total + 1):
	    f.write(self.get_item(i) + '\n')
	f.close()

    def load_history_file(self, file):
        logger.debug('Loading history file "%s"' % file)
	f = open(file)
        buf = []
	for line in f:
            buf += [line.strip()]
	f.close()

        if len(buf) > self.max_length:
            buf = buf[-self.max_length:]
        self.replace_history(buf)

class ReadlineHistory(History):

    def __init__(self, using_raw_inputter=True):
	global have_readline
	assert(have_readline)
	History.__init__(self)
	self.__using_raw = using_raw_inputter

    def get_item(self, index):
	return readline.get_history_item(index)

    def get_total(self):
	return readline.get_current_history_length()

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

	readline.clear_history()
	for s in buf:
	    readline.add_history(s)

    def clear_history(self):
	readline.clear_history()

    def get_max_length(self):
	return readline.get_history_length()

    def set_max_length(self, n):
	readline.set_history_length(n)

    def add_item(self, line, force=False):
	# If using the raw inputter, then readline has already been
	# called. Otherwise, do it ourselves.
	if force or (not self.__using_raw):
	    readline.add_history(line)

    def use_raw_input(self):
	return self.__using_raw


class SimpleHistory(History):

    def __init__(self):
	History.__init__(self)
	self.__buf = []
	self.__max_length = sys.maxint
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

    def get_total(self):
	return len(self.__buf)

    def get_max_length(self):
	return self.__max_length

    def set_max_length(self, n):
	self.__max_length = n

    def clear_history(self):
	self.__buf = []

    def add_item(self, line, force=False):
	if len(self.__buf) >= self.__max_length:
	    self.__buf[self.__max_length - 2:] = []
	self.__buf += [line]
	pass

    def use_raw_input(self):
	return False

if __name__ == "__main__":
    h = History.create()
