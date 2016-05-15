#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/ChirriException.py
#
#   The Only and Real Chirri Exception
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

import exceptions
import sys

class ChirriException(exceptions.Exception):

    __desc = None
    __callers_file = None
    __callers_lino = None
    __callers_name = None

    def __init__(self, desc):
        self.__callers_file = sys._getframe(1).f_code.co_filename
        self.__callers_lino = sys._getframe(1).f_lineno
        self.__callers_name = sys._getframe(1).f_code.co_name
        self.__desc = self.__class__.__name__ + ": " + desc;
        #if self.__desc is not None:
        #    self.__desc = self.__gen_desc + ": " + desc;
        #else:
        #    self.__desc = desc;

    def __str__(self):
        return "%s:%d:%s(): %s" \
               % (self.__callers_file,
                  self.__callers_lino,
                  self.__callers_name,
                  self.__desc)

class BadParameterException(ChirriException):
    """Bad parameter"""

class BadValueException(ChirriException):
    """Bad value"""

class ConfigNotFoundException(ChirriException):
    """Saved config not found"""

class ChunkNotFoundException(ChirriException):
    """Chunk not found"""

class ChunkBadFilenameException(ChirriException):
    """Chunk not found"""

class BadCompressionException(ChirriException):
    """Bad compression algorithm"""


