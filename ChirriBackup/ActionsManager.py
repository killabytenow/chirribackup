#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Actions.py
#
#   Chirri actions launcher
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
from ChirriBackup.Logger import logger
import exceptions
import traceback

action_handlers = {
        "db" : {
            "init"     : "DbInit",
            "check"    : "DbCheck",
            "rebuild"  : "DbRebuild",
            "status"   : "DbStatus",
            "config"   : {
                "set"    : "DbConfigSet",
                "save"   : "DbConfigSave",
                "delete" : "DbConfigDelete",
                "print"  : "DbConfigPrint",
                "list"   : "DbConfigList",
            },
        },
        "exclude" : {
            "add"      : "ExcludeAdd",
            "delete"   : "ExcludeDelete",
            "list"     : "ExcludeList",
            "disable"  : "ExcludeDisable",
            "enable"   : "ExcludeEnable",
        },
        "help"         : "Help",
        "snapshot" : {
            "delete"   : "SnapshotDelete",
            "details"  : "SnapshotDetails",
            "diff"     : "SnapshotDiff",
            "list"     : "SnapshotList",
            "new"      : "SnapshotNew",
            "restore"  : "SnapshotRestore",
            "run"      : "SnapshotRun",
        },
        "sync"   : "Sync",
}

def get_method(args, cah = None, action_words = None):
    if cah is None:
        cah = action_handlers
        action_words = [ ]

    # no more parameters, but we dont have nothing ... return none
    if len(args) == 0:
        return (None, action_words, args, cah)

    ## at least we have read one acceptable command token. If next word is
    ## 'help' then return 'help'.
    #if len(action_words) == 1:
    #    if len(args) == 0 or (len(args) == 1 and args[0] == "help"):
    #        return (None, action_words, args, cah)
    #elif len(action_words) == 0 and len(args) < 1:
    #    return (None, action_words, args, cah)

    action = args[0]
    action_words.append(action)
    args = args[1:] if len(args) > 1 else [ ]

    if action not in cah.keys():
        return (None, action_words, args, None)

    if isinstance(cah[action], dict):
        return get_method(args, cah[action], action_words)
    else:
        return (cah[action], action_words, args, None)


def check(args):
    (name, action_words, args, cah) = get_method(args)
    return (
        name is not None,
        cah.keys() if isinstance(cah, dict) else None
    )


def print_help(command, action):
    print "%s - %s" % (command, action.help["synopsis"])
    print ""
    if action.help["description"] is not None:
        for d in action.help["description"]:
            print "  %s" % d
        print ""
    print "Syntax:"
    if action.help["args"] is not None:
        args = []
        for a in action.help["args"]:
            args.append(a[0])
        print "  ... %s %s" % (command, " ".join(args))
    else:
        print "  ... %s" % command
    print ""
    if action.help["args"] is not None:
        print "Arguments:"
        for a in action.help["args"]:
            print "  %s" % a[0]
            for i in range(1, len(a)):
                print "    %s" % a[i]
            print ""
    else:
        print "Arguments: this command does not take any argument."
        print ""

def invoke(args):
    (name, action_words, args, cah) = get_method(args)

    modref = __import__("ChirriBackup.Actions.%s" % name,
                fromlist=["ChirriBackup.Actions"])

    if modref is None:
        raise ChirriException("Uknown action '%s'." % " ".join(action_words))

    classref = getattr(modref, name)
    action = classref()

    try:
        # execute action
        if len(args) == 1 and args[0] == 'help':
            print_help(" ".join(action_words), action)
        else:
            try:
                p = action.parse_args(args)
                if len(args) > 0:
                    raise ChirriException("Too many parameters.")
            except IndexError, ex:
                raise ChirriException("Need more parameters.")
            action.go(**p)

        # commit changes
        if action.ldb is not None:
            logger.debug("Commiting changes")
            action.ldb.connection.commit()

    except exceptions.Exception, ex:
        logger.error("Action failed")
        if action.ldb is not None:
            logger.debug("Trying to rollback")
            action.ldb.connection.rollback()
        else:
            logger.warning("Cannot rollback")

        logger.error(traceback.format_exc(), escape_nl = False)
        raise

    finally:
        if action.ldb is not None:
            logger.debug("Closing database")
            action.ldb.connection.close()


