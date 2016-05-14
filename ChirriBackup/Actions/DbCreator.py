#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Actions/DbCreator.py
#
#   Abstract class with a method for configuring a new database. This methods
#   makes a serie of questions, creates a void database and populates it with
#   the data given by the user.
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
import ChirriBackup.LocalDatabase
import ChirriBackup.Input
import ChirriBackup.Exclude
import os
import sys

class DbCreator(ChirriBackup.Actions.BaseAction.BaseAction):

    def get_config(self, config):
        if config is None:
            config = {
                "storage_type" : "local",
                "compression"  : "lzma",
            }

        # ask basic things
        print "Basic configuration"
        print "==================="
        print ""
        config["storage_type"] = ChirriBackup.Input.ask(
                                    "Storage type (local, gs)",
                                    config["storage_type"],
                                    "^(local|gs|Local|GoogleStorage)$")
        if config["storage_type"] == "local":
            config["storage_type"] = "Local"
        elif config["storage_type"] == "gs":
            config["storage_type"] = "GoogleStorage"

        config["compression"] = ChirriBackup.Input.ask(
                                    "Storage compression (none, lzma)",
                                    config["compression"],
                                    "^(none|lzma)$")
        if config["compression"] == "none":
            config["compression"] = None

        # Instantiate a config storage manager
        sm = ChirriBackup.Storage.BaseStorage.GetStorageManager(
                config["storage_type"],
                self.ldb,
                config=True)

        # configure storage module
        sm_title = "Backend '%s' configuration" % sm.name
        print ""
        print "%s" % sm_title
        print "=" * len(sm_title)
        print ""

        sm.ask_config(config)

        # print recollected data and ask for confirmation
        print ""
        print "Confirm"
        print "======="
        print ""
        print "Confirm following data:"
        for k,v in config.items():
            print "  %-15s = %s" % (k, v)
        print ""
        confirm = ChirriBackup.Input.ask("Continue (yes, no)", "y", "^(y(es)?|n(o)?)$")
        if confirm != "y":
            print "Aborting"
            return None

        return config;


    def create_db(self, config, excludes):
        if not ChirriBackup.LocalDatabase.check_db_exists(CONFIG.path):
            # build database
            logger.info("Going to initialize database")
            if not os.path.exists(CONFIG.path):
                logger.info("Creating directory '%s'." % CONFIG.path)
                os.makedirs(CONFIG.path)
            self.ldb = ChirriBackup.LocalDatabase.LocalDatabase(
                            CONFIG.path,
                            init = True,
                            storage_type = config["storage_type"])
            for k,v in config.items():
                setattr(self.ldb, k, v)
            self.ldb.connection.commit()
            logger.info("Database created succesfully.")
        else:
            logger.error("Database already exists.")

        for x in excludes:
            ChirriBackup.Exclude.Exclude(self.ldb).new(
                    exclude     = x["exclude"],
                    expr_type   = x["expr_type"],
                    ignore_case = x["ignore_case"],
                    disabled    = x["disabled"])

