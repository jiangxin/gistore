# -*- coding: utf-8 -*-
#
# gistore -- Backup files using DVCS, such as git.
# Copyright (C) 2010 Jiang Xin <jiangxin@ossxp.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#

import os
from signal import SIGINT
from gistore.config import *
from gistore.errors import *

def warn_if_error(proc, cmdline="", stdout=None):
    if isinstance(cmdline, (list,tuple)):
        cmdline = " ".join(cmdline)
    if stdout is None:
        stdout = proc.stdout
    #Read stdout buffer before wait(), because if buffer overflow, process will hang!
    verbose(stdout.read().rstrip(), LOG_INFO)
    proc.wait()
    if proc.returncode != 0:
        verbose("Last command: %s\n\tgenerate warnings with returncode %d." % (cmdline, proc.returncode), LOG_WARNING)

def exception_if_error(proc, cmdline="", stdout=None):
    if isinstance(cmdline, (list,tuple)):
        cmdline = " ".join(cmdline)
    if stdout is None:
        stdout = proc.stdout
    #Read stdout buffer before wait(), because if buffer overflow, process will hang!
    verbose(stdout.read().rstrip(), LOG_INFO)
    proc.wait()
    if proc.returncode != 0:
        raise CommandError("Last command: %s\n\tgenerate ERRORS with returncode %d!" % (cmdline, proc.returncode))

def exception_if_error2(proc, cmdline="", stdout=None, test=None):
    if isinstance(cmdline, (list,tuple)):
        cmdline = " ".join(cmdline)
    if stdout is None:
        stdout = proc.stdout
    #Read stdout buffer before wait(), because if buffer overflow, process will hang!
    success = False
    for line in stdout:
        if not success and test and test(line):
            success = True
            verbose("match line: %s" % line, LOG_DEBUG)
        verbose(line, LOG_INFO)

    proc.wait()

    if not success and proc.returncode != 0:
        raise CommandError("Last command: %s\n\tgenerate ERRORS with returncode %d!" % (cmdline, proc.returncode))

def show_exception(e):
    traceback = True
    if '__module__' in dir(e) and e.__module__.startswith("gistore"):
        traceback = False
    print >> sys.stderr, ("Exception caught abort: %s" %
                          exception_to_unicode(e, traceback=traceback))

def verbose(args, level=LOG_INFO, show_prompt=True):
    if level <= cfg.log_level and args:
        firstline = True
        for line in args.splitlines():
            if line:
                if level == LOG_ERR:
                    prompt = "error>"
                elif level == LOG_WARNING:
                    prompt = "warning>"
                elif level == LOG_NOTICE:
                    prompt = "notice>"
                elif level == LOG_INFO:
                    prompt = "info>"
                elif level == LOG_DEBUG:
                    prompt = "debug>"
                if show_prompt:
                    if firstline:
                        firstline = False
                        print >> sys.stderr, prompt,
                    else:
                        print >> sys.stderr, " " * len(prompt),
                print >> sys.stderr, line
            else:
                print >> sys.stderr, ""


# exception_to_unicode and to_unicode is borrowed from Trac.
def exception_to_unicode(e, traceback=""):
    message = '%s: %s' % (e.__class__.__name__, to_unicode(e))
    if traceback:
        import traceback
        from StringIO import StringIO
        tb = StringIO()
        traceback.print_exc(file=tb)
        traceback_only = tb.getvalue().split('\n')[:-2]
        message = '\n%s\n%s' % (to_unicode('\n'.join(traceback_only)), message)
    return message

def to_unicode(text, charset=None):
    """Convert a `str` object to an `unicode` object.

    If `charset` is given, we simply assume that encoding for the text,
    but we'll use the "replace" mode so that the decoding will always
    succeed.
    If `charset` is ''not'' specified, we'll make some guesses, first
    trying the UTF-8 encoding, then trying the locale preferred encoding,
    in "replace" mode. This differs from the `unicode` builtin, which
    by default uses the locale preferred encoding, in 'strict' mode,
    and is therefore prompt to raise `UnicodeDecodeError`s.

    Because of the "replace" mode, the original content might be altered.
    If this is not what is wanted, one could map the original byte content
    by using an encoding which maps each byte of the input to an unicode
    character, e.g. by doing `unicode(text, 'iso-8859-1')`.
    """
    if not isinstance(text, str):
        if isinstance(text, Exception):
            # two possibilities for storing unicode strings in exception data:
            try:
                # custom __str__ method on the exception (e.g. PermissionError)
                return unicode(text)
            except UnicodeError:
                # unicode arguments given to the exception (e.g. parse_date)
                return ' '.join([to_unicode(arg) for arg in text.args])
        return unicode(text)
    if charset:
        return unicode(text, charset, 'replace')
    else:
        try:
            return unicode(text, 'utf-8')
        except UnicodeError:
            return unicode(text, locale.getpreferredencoding(), 'replace')

# vim: et ts=4 sw=4
