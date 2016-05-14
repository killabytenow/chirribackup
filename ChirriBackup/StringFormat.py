#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/StringFormat.py
#
#   Some string formatting helper subs
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

import logging
import logging.handlers
import sys
from struct import *

def EscapeString(s, escape_nl = True):
    s = str(s)
    r = ""
    i = 0
    while i < len(s):
        x = unpack("B", s[i])
        if x[0] < 32:
            if not escape_nl and x[0] == 10:
                r = r + s[i]
            else:
                r = "%s\%02x" % (r, x[0])
        else:
            r = r + s[i]
        i = i + 1

    return r

def IndentString(s, indent = "  ", indent_first_line = True):
    s = str(s)

    if indent == None or indent == "":
        return s

    r = ""
    if indent_first_line: r = indent

    i = 0
    while i < len(s):
        r = r + s[i]
        x = unpack("B", s[i])
        if x[0] == 10:
            r = r + indent
        i = i + 1

    return r

