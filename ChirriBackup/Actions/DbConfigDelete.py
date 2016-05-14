#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Actions/DbConfigDelete.py
#
#   Delete stored config
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

from ChirriBackup.ChirriException import *
from ChirriBackup.Config import CONFIG
from ChirriBackup.Logger import logger
import ChirriBackup.Actions.BaseAction
import ChirriBackup.Crypto
import ChirriBackup.Input
import ChirriBackup.LocalDatabase
import os
import json
import sys


class DbConfigDelete(ChirriBackup.Actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "Delete an stored configuration",
        "description": None,
        "args": [
            [ "config_id",
                "Id of the stored config selected."
            ]
        ]
    }


    def go(self, args):
        if len(args) != 1:
            raise ChirriException("Need a config_id")

        self.ldb = ChirriBackup.LocalDatabase.LocalDatabase(CONFIG.path)
        c = self.ldb.config_delete(args[0])


