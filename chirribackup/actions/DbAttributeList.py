#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbAttributeList.py
#
#   List db parameters
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


class DbAttributeList(chirribackup.actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "List db parameters",
        "description": [
            "This command list all database attributes.",
        ],
        "args": None
    }


    def parse_args(self, argv):
        return {}


    def go(self):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)

        f = [ 32, 5, 5, 32 ]
        print ("%" + ("s %".join("-{0}".format(n) for n in f)) + "s") % (
                    "key",
                    "save",
                    "type",
                    "value")
        l = [ ]
        for i in f:
            l.append("-" * i)
        print " ".join(l)
        for k,a in sorted(self.ldb.config_attrib_list().iteritems()):
            print ("%" + ("s %".join("-{0}".format(n) for n in f)) + "s") % (
                    k,
                    "yes" if a["save"] != 0 else "no",
                    a["type"],
                    a["value"])


