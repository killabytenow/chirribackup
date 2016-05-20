#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/ExcludeAdd.py
#
#   Add a new exclude rule
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

import chirribackup.LocalDatabase
import chirribackup.actions.BaseAction
import chirribackup.exclude
from chirribackup.Config import CONFIG
from chirribackup.exceptions import ChirriException


class ExcludeAdd(chirribackup.actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "Add a new exclude rule",
        "description": None,
        "args": [
            [ "(literal|wildcard|re)",
                "It is the expression type. You must choose one of them:",
                "  literal",
                "    Value of parameter {exclude} is literally compared",
                "    with each file's relative path. This mode is useful",
                "    for excluding exactly only one file per exclude rule.",
                "    For instance, choosing \"etc/passwd\" will exclude the",
                "    file \"$BACKUPDIR/etc/passwd of being copied.",
                "  wildcard",
                "    Files matching wildcard {exclude} will be excluded.",
                "    Wildcard syntax provides support for Unix shell-style",
                "    wildcards. The special characters used in wildcards",
                "    are:",
                "      Pattern     Meaning",
                "      ----------- -------------------------------",
                "         *        matches everything",
                "         ?        matches any single character",
                "         [seq]    matches any character in seq",
                "         [!seq]   matches any character not in seq",
                "  re",
                "    Relative paths will be matched against the regular",
                "    expression contained in the parameter {exclude}.",
                "    Regex syntax supported is documented by the Python's re",
                "    module (see https://docs.python.org/library/re.html).",
            ],
            [ "?ignorecase",
                "If this flag is present, case is ignored.",
            ],
            [ "{exclude}",
                "A relative path, a wildcard or a regular expression.",
            ]
        ]
    }

 
    def parse_args(self, argv):
        r = { } 
        r["expr_type"] = argv.pop(0)
        if len(argv) > 1:
            if argv[0] != "ignorecase" and argv[0] != "ignore_case":
                raise ChirriException("Unknown flag '%s'." % argv[0])
            argv.pop(0)
            r["ignore_case"] = 1
        r["exclude"] = argv.pop(0)
        return r


    def go(self, exclude, expr_type, ignore_case = 0, disabled = 0):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        chirribackup.exclude.Exclude(self.ldb).new(
                    exclude     = exclude,
                    expr_type   = expr_type,
                    ignore_case = ignore_case,
                    disabled    = disabled)

