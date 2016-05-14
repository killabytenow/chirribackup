#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Logger.py
#
#   My lovely chirri logger
#
# -----------------------------------------------------------------------------
# Chirri Backup - Cheap and ugly backup tool
#   Copyright (C) 2016 Gerardo Garcia Peña <killabytenow@gmail.com>
#
#   This program is free software; you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free
#   Software Foundation, either version 3 of the License, or (at your option)
#   any later version.
#
#   This program is distributed in the hope that it will be useful, but WITHOUT
#   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#   FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
#   more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program. If not, see <http://www.gnu.org/licenses/>.
# 
###############################################################################

import errno
import logging
import logging.handlers
import os
import time
import ChirriBackup.ChirriException
from ChirriBackup.StringFormat import *

psyco_available = False
try:
    import psyco
    psyco_available = True
except ImportError, e:
    pass


class LoggerException(ChirriBackup.ChirriException.ChirriException):
    """Exception raised by the Logger methods."""


class Logger(object):

    # Internal Logger (real singleton instance)
    class internal_logger(object):

        __logger = None
        __level  = None
        __hooks  = { }

        LEVELS_STR = {
            "DEBUG2"   : -1,
            "DEBUG"    : logging.DEBUG,
            "INFO"     : logging.INFO,
            "WARNING"  : logging.WARNING,
            "ERROR"    : logging.ERROR,
            "CRITICAL" : logging.CRITICAL }

        LEVELS_ID = {
            -1               : "DEBUG2",
            logging.DEBUG    : "DEBUG",
            logging.INFO     : "INFO",
            logging.WARNING  : "WARNING",
            logging.ERROR    : "ERROR",
            logging.CRITICAL : "CRITICAL" }

        def __init__(self):
            # initialization and set formatting
            logging.basicConfig()
            self.__logger = logging.getLogger("CHIRRI")
            SysLogHandler = logging.handlers.SysLogHandler()
            SysLogHandler.formatter = logging.Formatter(fmt = "%(module)s[%(name)s] with %(levelname)s (%(asctime)s): %(message)s")
            self.__logger.addHandler(SysLogHandler)

            # Default lower level definition
            self.setLogLevel("INFO")

            # Handler Utilization
            #self.info("Log System Initialization at '%s'" % time.ctime())

            return None

        def normalize_log_level(self, ll):
            try:
                if isinstance(ll, basestring):
                    ln = ll.upper()
                    ll = self.LEVELS_STR[ln]
                else:
                    ll = self.LEVELS_ID[ll]
            except:
                raise LoggerException("Unknown log level '%s'." % ll)
            return ll

        ## Generic Log Method
        #
        def __log(self, n_log_level, log_string, escape_nl, escape):
            if escape:
                log_string = EscapeString(str(log_string), escape_nl)
            if self.__hooks.has_key(n_log_level):
                for h in self.__hooks[n_log_level]:
                    h(n_log_level, log_string)
            n_log_level = logging.DEBUG if n_log_level == -1 else n_log_level
            for l in str(log_string).split("\n"):
                self.__logger.log(n_log_level, l)


        def log(self, log_level, log_string, escape_nl, escape):
            n_log_level = self.normalize_log_level(log_level)
            return self.__log(n_log_level, log_string, escape_nl, escape)


        ## hooker
        # hook
        def hook(self, log_level, hook):
            n_log_level = self.normalize_log_level(log_level)
            if not self.__hooks.has_key(n_log_level):
                self.__hooks[n_log_level] = [ ]
            self.__hooks[n_log_level].append(hook)


        ## ToFile redirector
        #
        def to_file(self, filename):
            try:
                if os.path.dirname(filename) != "":
                    os.makedirs(os.path.dirname(filename))
            except os.error, err:
                if err.errno != errno.EEXIST:
                    raise FilesystemException("Cannot create directory '%s'." % os.path.dirname(filename));
            FileNameHandler = logging.FileHandler('%s' % filename)
            FileNameHandler.formatter = logging.Formatter(fmt = "%(module)s[%(name)s] with %(levelname)s (%(asctime)s): %(message)s")
            self.__logger.addHandler(FileNameHandler)
            self.info("File %s added to log system." % filename)
            return None

        ## LOG METHODS
        def critical(self, log_string, escape_nl = True, escape = True): return self.__log(logging.CRITICAL, log_string, escape_nl, escape)
        def error   (self, log_string, escape_nl = True, escape = True): return self.__log(logging.ERROR,    log_string, escape_nl, escape)
        def warning (self, log_string, escape_nl = True, escape = True): return self.__log(logging.WARNING,  log_string, escape_nl, escape)
        def info    (self, log_string, escape_nl = True, escape = True): return self.__log(logging.INFO,     log_string, escape_nl, escape)
        def debug   (self, log_string, escape_nl = True, escape = True): return self.__log(logging.DEBUG,    log_string, escape_nl, escape)
        def debug2  (self, log_string, escape_nl = True, escape = True): return self.__log(-1,               log_string, escape_nl, escape)
        def setLogLevel(self, log_level):
            self.__level = self.normalize_log_level(log_level)
            self.__logger.setLevel(logging.DEBUG if self.__level == -1 else self.__level)


        if psyco_available:
            psyco.bind(log)
            psyco.bind(to_file)
            psyco.bind(critical)
            psyco.bind(error)
            psyco.bind(warning)
            psyco.bind(info)
            psyco.bind(debug)
            psyco.bind(setLogLevel)

        ## Redefinition of id (ONLY TEST INTETION)
        #
    __instance = None

    def __init__(self):
        """ Create singleton instance """

        # Check whether we already have an instance
        if Logger.__instance is None:
            # Create and remember instance
            Logger.__instance = Logger.internal_logger()

        # Store instance reference as the only member in the handle
        self.__dict__['_Singleton__instance'] = Logger.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)

    if psyco_available:
        psyco.bind(__init__)
        psyco.bind(__getattr__)
        psyco.bind(__setattr__)

logger = Logger()
