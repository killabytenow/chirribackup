#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/Help.py
#
#   Print a lot of help
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
import chirribackup.ActionsManager
import chirribackup.actions.DbCreator
import chirribackup.LocalDatabase
import os
import sys

class Help(chirribackup.actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Prints help",
        "description": None,
        "args": None,
    }


    def import_action(self, action):
        modref = __import__("chirribackup.actions.%s" % action,
                    fromlist=["chirribackup.actions"])
        if modref is None:
            raise ChirriException("Cannot load chirribackup.actions.%s" % action)
        classref = getattr(modref, action)
        return classref()


    def __get_all_help_r(self, cah, c = ""):
        r = {}

        for k,action in cah.iteritems():
            ck = k if c == "" else c + " " + k
            if isinstance(action, dict):
                r.update(self.__get_all_help_r(action, ck))
            else:
                r[ck] = self.import_action(action).help["synopsis"]

        return r


    def parse_args(self, argv):
        return {}


    def go(self):
        print "Usage:"
        print ""
        print "    %s {database_directory} {command} [...command arguments...]" % sys.argv[0]
        print ""
        print "Available commands:"
        print ""
        all_help = self.__get_all_help_r(chirribackup.ActionsManager.action_handlers)
        max_length = max([len(x) for x in all_help.iterkeys()])
        f = "    %%-%ds   %%s" % max_length
        for command, synopsys in sorted(all_help.iteritems()):
            print f % (command, synopsys)
        print ""


