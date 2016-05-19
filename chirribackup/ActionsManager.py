#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions.py
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

from __future__ import absolute_import

from chirribackup.Logger import logger
import exceptions
import traceback

from chirribackup.exceptions import BadActionException, ChirriException, BadParameterException, \
    ActionInvocationException

action_handlers = {
        "db" : {
            "attribute" : {
                "delete" : "DbAttributeDelete",
                "get"    : "DbAttributeGet",
                "set"    : "DbAttributeSet",
                "list"   : "DbAttributeList",
            },
            "init"     : "DbInit",
            "check"    : "DbCheck",
            "rebuild"  : "DbRebuild",
            "status"   : "DbStatus",
            "config"   : {
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
            "print"    : "SnapshotPrint",
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

def get_action_name(args):
    # process arg list
    rargs = []
    cah = action_handlers
    while len(args) > 0:
        cm = args.pop(0)
        rargs.append(cm)
        if cm not in cah:
            raise BadActionException("Invalid command '%s'." % " ".join(rargs))
        cah = cah[cm]
        if not isinstance(cah, dict):
            return (rargs, None, cah)
    if len(rargs) > 0:
        raise BadActionException("Incomplete action '%s'; valid subactions: %s" \
                                    % (", ".join(rargs), ", ".join(cah.keys())))
    else:
        raise BadActionException("Need an action; valid subactions: %s" \
                                    % ", ".join(cah.keys()))


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
    # parse call
    # NOTE: in this call 'args' get modified, and action name args are moved to
    # the rargs array.
    (rargs, __this_should_be_None__, action_name) = get_action_name(args)
    if __this_should_be_None__ is not None:
        raise ChirriException("__this_should_be_None__ is not None!")

    # load action module
    modref = __import__("chirribackup.actions.%s" % action_name,
                fromlist=["chirribackup.actions"])
    if modref is None:
        raise BadActionException("Uknown action '%s'." % " ".join(rargs))
    classref = getattr(modref, action_name)
    action = classref()

    try:
        if len(args) == 1 and args[0] == 'help':
            # print help about this command
            print_help(" ".join(rargs), action)
        else:
            # execute action
            try:
                p = action.parse_args(args)
                if len(args) > 0:
                    raise BadParameterException("Too many parameters.")
            except IndexError, ex:
                raise BadParameterException("Need more parameters.")
            action.go(**p)

        # commit changes
        if action.ldb is not None:
            logger.debug("Commiting changes")
            action.ldb.connection.commit()

    except ActionInvocationException, ex:
        raise

    except exceptions.Exception, ex:
        if action.ldb is not None:
            logger.debug("Trying to rollback")
            action.ldb.connection.rollback()
        else:
            logger.warning("Cannot rollback")

        logger.debug(traceback.format_exc(), escape_nl = False)
        raise

    finally:
        if action.ldb is not None:
            logger.debug("Closing database")
            action.ldb.connection.close()


