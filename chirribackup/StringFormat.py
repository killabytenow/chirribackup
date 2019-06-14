#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/StringFormat.py
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
import pprint
import sys
from struct import unpack


def escape_string(s, escape_nl=True):
    s = str(s)
    r = []
    for c in s:
        x = ord(c)
        if x < 32:
            if not escape_nl and x == 10:
                r.append(c)
            else:
                r.append("%" + format(x, "02x"))
        else:
            r.append(c)

    return ''.join(r)


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


def format_num_bytes(value):
    if   value > (1024.0 ** 3): r = "%.2f Gb" % (value / (1024.0 ** 3))
    elif value > (1024.0 ** 2): r = "%.2f Mb" % (value / (1024.0 ** 2))
    elif value > 1024.0:        r = "%.2f Kb" % (value / 1024.0)
    elif value == 1:            r = "1 byte"
    else:                       r = "%d bytes" % value

    return r


def dump(name, var):
    return "Dump of %s(%s):" % (name, var.__class__.__name__) \
         + ((" %s" % var.__str__()) if hasattr(var, "__str__") else "") \
         + "\n" \
         + pprint.pformat(vars(var) if hasattr(var, "__dict__") else var, indent = 4)


