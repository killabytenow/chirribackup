#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Input.py
#
#   Input data.
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

import re

def ask(valdesc, defval = None, regex = None):
    val = None
    if regex is not None:
        regex = re.compile(regex)

    while val is None:
        if defval is not None:
            val = raw_input("%s [%s]? " % (valdesc, defval))
        else:
            val = raw_input("%s? " % valdesc)
        if val == "":
            val = None
        if val is None:
            val = defval
        if regex is not None \
        and val is not None  \
        and not regex.match(str(val)):
            val = None

    return val

