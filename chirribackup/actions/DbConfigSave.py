#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbConfigSave.py
#
#   Save config to file for later use in commands:
#       - db init
#       - db rebuild
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
import chirribackup.Crypto
import chirribackup.Input
import chirribackup.LocalDatabase
import os
import json
import sys


class DbConfigSave(chirribackup.actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "Keep a copy of current database configuration in backup",
        "description": [
            "This command pushes an snapshot of the current database",
            "configuration (including exclude list too) to the remote",
            "storage. This information may be used later for feeding other",
            "commands like 'db init' or 'db rebuild'.",
        ],
        "args": None,
    }


    def parse_args(self, argv):
        return {}


    def go(self):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        self.ldb.config_save()


