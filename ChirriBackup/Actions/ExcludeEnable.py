#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Actions/ExcludeEnable.py
#
#   Enable a exclude rule
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

from ChirriBackup.ChirriException import ChirriException
from ChirriBackup.Config import CONFIG
from ChirriBackup.Logger import logger
import ChirriBackup.Actions.BaseAction
import ChirriBackup.Exclude
import ChirriBackup.LocalDatabase
import os
import sys

class ExcludeEnable(ChirriBackup.Actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "Enable a exclude rule",
        "description": None,
        "args": [
            [ "{exclude}",
                "The exclude rule that will be enabled.",
            ]
        ]
    }


    def go(self, args):
        if len(args) != 1:
            raise ChirriException("Need exclude expression.")

        self.ldb = ChirriBackup.LocalDatabase.LocalDatabase(CONFIG.path)
        ChirriBackup.Exclude.Exclude(self.ldb, args[0]).enable()


