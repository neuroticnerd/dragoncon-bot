from __future__ import absolute_import, unicode_literals

import logging


class LogAndForget(object):
    """ Log encountered exceptions without letting them propagate. """
    def __init__(self, message=None, log=None):
        self.message = message
        if message is None:
            self.message = ''
        if not self.message.endswith('\n'):
            self.message = self.message + '\n'
        self.log = log
        if self.log is None:
            self.log = logging.getLogger(__name__)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is not None:
            import traceback
            output = self.message + ''.join(traceback.format_exception(
                exc_type, exc_value, exc_traceback
            ))
            self.log.error(output)
        return True
