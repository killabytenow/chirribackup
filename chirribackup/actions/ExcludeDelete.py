#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/ExcludeDelete.py
#
#   Delete a exclude rule
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

from chirribackup.exceptions import ChirriException
from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
import chirribackup.actions.BaseAction
import chirribackup.exclude
import chirribackup.LocalDatabase
import os
import sys

class ExcludeDelete(chirribackup.actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "Delete a exclude rule",
        "description": None,
        "args": [
            [ "{exclude_id}",
                "The exclude rule that will be removed."
            ],
        ]
    }

 
    def parse_args(self, argv):
        return {
            "exclude_id": argv.pop(0),
        }


    def go(self, exclude_id):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        chirribackup.exclude.Exclude(self.ldb, exclude_id).delete()


