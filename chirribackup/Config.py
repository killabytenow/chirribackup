#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# Config.py
#   ***this file contains magic***
#
#   Config class
#     1) reads config from command line
#     2) store global config
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
from chirribackup import ActionsManager
from chirribackup.Logger import logger
from optparse import OptionError
from optparse import OptionParser
import os
import re
import sys


class Config(object):

    class internal_Config(object):

        options = None

        def __init__(self):
            args = None
            parser = OptionParser(
                        prog="chirribackup",
                        description="%prog is a cheap and ugly backup tool written with love.",
                        version="%prog 1.0",
                        usage="%s [options] {directory} {action} [action args...]" % sys.argv[0],
                        epilog="Use 'help' action for more information. Other valid commands: %s" \
                                % " ".join(ActionsManager.action_handlers.keys())
                        )
            parser.add_option("-D", "--debug",
                                  dest="verbosity",
                                  action="store_const",
                                  const="DEBUG",
                                  help="Debug verbosity level.")
            parser.add_option("-l", "--log-file",
                                  dest="logfile",
                                  default=None,
                                  help="Log file")
            parser.add_option("-v", "--verbosity",
                                  type="str",
                                  dest="verbosity",
                                  default="INFO",
                                  help="The log verbosity level. Accepted values: CRITICAL, ERROR, WARNING, INFO (default), DEBUG, DEBUG2")

            try:
                (self.options, args) = parser.parse_args()

                if self.options.logfile is not None:
                    logger.to_file(self.options.logfile)
                if self.options.verbosity is not None:
                    logger.setLogLevel(self.options.verbosity)

                if len(args) < 1:
                        parser.error("Target {directory} not specified.")

                self.options.path = args[0]
                self.options.args = args[1:]

                if len(args) == 1 and args[0] == "help":
                    self.options.path = None
                    self.options.args = args
                elif len(args) == 2 and args[0] == "help" and args[1] == "help":
                    self.options.path = None
                    self.options.args = args
                else:
                    if not os.path.exists(self.options.path):
                            logger.warning("Target directory '%s' does not exist." % self.options.path)
                    elif not os.path.isdir(self.options.path):
                            parser.error("Target directory '%s' is not a directory." % self.options.path)

            except (OptionError, TypeError), e:
                parser.error(e)


    # Singleton container class
    __instance = None

    def __init__(self):
        """ Create singleton instance """
        if self.__class__.__instance is None:
            self.__class__.__instance = self.__class__.internal_Config()
        self.__dict__['_Singleton__instance'] = self.__class__.__instance


    def __getattr__(self, attr):
        return getattr(self.__instance.options, attr)


    def __setattr__(self, attr, value):
        return setattr(self.__instance.options, attr, value)

###############################################################################
# MAGIC: This parses command line and prepares runtime config.
###############################################################################

CONFIG = Config()

