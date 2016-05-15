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


    def parse_args(self, argv):
        r = {
            "config_file": None,
            "wizard": True,
        }
        if len(argv) > 0:
            r["config_file"] = argv.pop(0)
            if len(argv) > 0:
                p = argv.pop(0)
                if p == "wizard":
                    r["wizard"]
                else:
                    raise BadParameterException("Unknown flag '%s'." % p)
        return r


    def go(self, config_file, wizard):
        config = None
        excludes = None

        if config_file is not None:
            # read config file
            with open(config_file, "rb") as f:
                config_data = ChirriBackup.LocalDatabase.LocalDatabase.config_parse(f.read())
                config = {}
                for k,v in config_data["status"].iteritems():
                    config[k] = str(v["value"])
                excludes = config_data["excludes"]
        else:
            if not wizard:
                raise ChirriException("wizard must be enabled if config_file is not provided.")
            excludes = None

        if wizard:
            config = self.get_config(config)

        if config is not None:
            self.create_db(config, excludes)
        else:
            sys.exit(1)


