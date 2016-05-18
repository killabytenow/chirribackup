#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbAttributeSet.py
#
#   Set a db parameter
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

from chirribackup.ChirriException import *
from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
import chirribackup.actions.BaseAction
import chirribackup.LocalDatabase
import os
import json
import sys


class DbAttributeSet(chirribackup.actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "Set a db parameter",
        "description": [
            "This command allows to change manually some database",
            "configuration parameter (like the configuration of the storage",
            "manager or tunning some other parameter).",
            "",
            "Please note that this command is intended only for advanced",
            "users and it is no recommended to alter the database",
            "configuration is this way.",
        ],
        "args": [
            [ "?new ?save {type}",
                "This optional parameters are used for creating a new status",
                "key.",
                "",
                "The optional flag 'save' tells the program that this status",
                "key must be serialized to the config snapshots done with",
                "'db config save' and 'db config print'.",
                "",
                "Finally, the last parameter {type} is used for determining",
                "the type of this field. Acceptable values are 'int' and",
                "'str'.",
            ],
            [ "?null",
                "If this flag is present, {value} cannot be present and this",
                "field will be set to null (unset)."
            ],
            [ "{config_key}",
                "Configuration key: the name of the parameter.",
            ],
            [ "?{value}",
                "New value asigned to this variable. Value can be only",
                "declared if the 'flag' null is not set, otherwise an error",
                "will occur.",
            ]
        ]
    }


    def parse_args(self, argv):
        r = { } 
        p = argv.pop(0)
        if p == "new":
            r["create"] = True
            p = argv.pop(0)
            if p == "save":
                r["save"] = True
                p = argv.pop(0)
            else:
                r["save"] = False

            if p == "int":
                r["type"] = "int"
            elif p == "str":
                r["type"] = "str"
            else:
                raise UnknownParameterException("Unknown config key type '%s'." % p)
            p = argv.pop(0)

        if p == "null":
            r["key"] = argv.pop(0)
            r["value"] = None
        else:
            r["key"] = p
            r["value"] = argv.pop(0)

        return r


    def go(self, key, value, create = False, save = None, type = None):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)

        if create:
            self.ldb.config_attrib_new(key, save, type, value)
        else:
            self.ldb.config_attrib_set(key, value)


