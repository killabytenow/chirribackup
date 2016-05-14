#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Actions/Snapshot.py
#
#   Create an snapshot and prepare it for uploading.
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
import ChirriBackup.Actions.DbCreator
import ChirriBackup.LocalDatabase
import os
import sys

class DbInit(ChirriBackup.Actions.DbCreator.DbCreator):

    help = {
        "synopsis": "Initialize directory for backups",
        "description": [
            "This command creates and initializes a `__chirri__.db` database",
            "the {db_dir} database directory. This database is used for",
            "keeping track of the status of both the local and remote",
            "storage, and it stores all the configuration parameters too."
        ],
        "args": [
            [ "?{config_file}",
                "Optionally you can import a previously saved configuration",
                "file, which may include a complete exclude list or detailed",
                "configuration of the remote storage. By default the",
                "configuration wizard will be disabled if you provide this",
                "option. If you want to enable it, add the 'wizard' flag",
                "argument."
            ],
            [ "?wizard",
                "This optional flag can be only set if the option",
                "{config_file} is present. It enables the wizard and allows",
                "to edit the configured values in the {config_file}",
                "configuration file."
            ],
        ],
    }

    def go(self, args):
        wizard = True
        config = None
        excludes = None

        if len(args) > 0:
            # read config file
            with open(args[0], "rb") as f:
                saved_config = ChirriBackup.LocalDatabase.LocalDatabase.config_parse(f.read())
                config = {}
                for k,v in saved_config["status"].iteritems():
                    config[k] = str(v["value"])
                excludes = saved_config["excludes"]

            # by default disable wizard
            if len(args) > 2:
                raise ChirriException("Too many parameters")
            elif len(args) > 1:
                if args[1] == "wizard":
                    wizard = True
                else:
                    raise ChirriException("Unknown parameter '%s'." % args[1])
            else:
                wizard = False
        else:
            wizard = True
            excludes = None

        if wizard:
            config = self.get_config(config)

        if config is not None:
            self.create_db(config, excludes)
        else:
            sys.exit(1)


