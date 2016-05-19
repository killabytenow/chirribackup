#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbAttributeDelete.py
#
#   Delete a db parameter
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

from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
import chirribackup.actions.BaseAction
import chirribackup.LocalDatabase
import os
import json
import sys


class DbAttributeDelete(chirribackup.actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "Delete a db parameter",
        "description": [
            "This command allows to get the value of a database attribute.",
            "",
            "Please note that this command is HIGHLY DESTRUCTIVE and it is no",
            "recommended to alter the database configuration in this way.",
        ],
        "args": [
            [ "{config_key}",
                "Configuration key: the name of the parameter.",
            ],
        ]
    }


    def parse_args(self, argv):
        return {
            "key": argv.pop(0),
        }


    def go(self, key):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        self.ldb.config_attrib_delete(key)


