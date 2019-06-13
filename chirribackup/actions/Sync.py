#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/Info.py
#
#   Get info
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
from chirribackup.StringFormat import format_num_bytes
from chirribackup.exceptions import ChirriException
import chirribackup.actions.BaseAction
import chirribackup.LocalDatabase
import chirribackup.syncer
import sys

class Sync(chirribackup.actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Sync remote data",
        "description": None,
        "args": None,
    }

 
    def parse_args(self, argv):
        return {}


    def go(self):
        logger.debug("Opening local database")
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        logger.debug("Creating syncer")
        syncer = chirribackup.syncer.Syncer(self.ldb)
        syncer.run()
        print "Finished succesfully:"
        print "  - Uploaded %d snapshots" % syncer.counters["snapshots"]
        print "  - Uploaded %d chunks"    % syncer.counters["chunks"]
        print "  - Uploaded %s" % format_num_bytes(syncer.counters["bytes"])
        print "  - Uploaded %d files" % syncer.counters["files"]


