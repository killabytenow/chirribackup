#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbCreator.py
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

from chirribackup.exceptions import ExcludeNotFound, ChirriException


class Exclude(object):
    ldb = None
    exclude_id = None
    exclude = None
    expr_type = None
    ignore_case = None
    disabled = None

    def __init__(self, ldb, exclude_id=None):
        self.ldb = ldb
        if exclude_id is not None:
            self.load(exclude_id)

    @classmethod
    def parse_expr_type(cls, expr_type):
        if isinstance(expr_type, (int, long)) and 0 <= expr_type <= 2:
            return expr_type

        if expr_type == "literal":
            return 0
        elif expr_type == "wildcard":
            return 1
        elif expr_type == "re":
            return 2

        raise ChirriException("Invalid expression type '%s'." % expr_type)

    def new(self, exclude, expr_type, ignore_case, disabled):
        expr_type = self.parse_expr_type(expr_type)

        if exclude == "":
            raise ChirriException("Void exclude expression.")

        # get a new exclude id
        self.exclude_id = self.ldb.last_exclude_id + 1
        self.ldb.last_exclude_id = self.exclude_id

        # populate structure
        self.exclude     = exclude
        self.expr_type   = expr_type
        self.ignore_case = ignore_case if ignore_case is not None else 0
        self.disabled    = disabled if disabled is not None else 0

        # insert in db
        self.ldb.connection.execute(
            """
                INSERT INTO excludes (exclude_id, exclude, expr_type, ignore_case, disabled)
                    VALUES (:exclude_id, :exclude, :expr_type, :ignore_case, :disabled)
            """, {
                "exclude_id": self.exclude_id,
                "exclude": self.exclude,
                "expr_type": self.expr_type,
                "ignore_case": self.ignore_case,
                "disabled": self.disabled,
            })

        return self

    def load(self, exclude_id):
        x = self.ldb.connection.execute(
            "SELECT * FROM excludes WHERE exclude_id = :exclude_id",
            {"exclude_id": exclude_id}).fetchone()

        if x is None:
            raise ExcludeNotFound("Exclude '%s' not found." % exclude_id)

        self.exclude_id  = x["exclude_id"]
        self.exclude     = x["exclude"]
        self.expr_type   = x["expr_type"]
        self.ignore_case = x["ignore_case"]
        self.disabled    = x["disabled"]

        if self.expr_type == 0:
            self.expr_type = "literal"
        elif self.expr_type == 1:
            self.expr_type = "wildcard"
        elif self.expr_type == 2:
            self.expr_type = "re"

        return self

    def enable(self, enable=True):
        self.disabled = 0 if enable else 1
        self.ldb.connection.execute(
            """
                UPDATE excludes
                SET disabled = :disabled
                WHERE exclude_id = :exclude_id
            """, {
                "exclude_id": self.exclude_id,
                "disabled": self.disabled,
            })

    def disable(self, disable=True):
        self.enable(not disable)

    def delete(self):
        self.ldb.connection.execute(
            """
                DELETE FROM excludes
                WHERE exclude_id = :exclude_id
            """, {
                "exclude_id": self.exclude_id,
            })
        self.ldb = None
        self.exclude_id = None
        self.exclude = None
        self.expr_type = None
        self.ignore_case = None
        self.disabled = None

    @classmethod
    def list(cls, ldb):
        l = []
        for x in ldb.connection.execute("SELECT exclude_id FROM excludes"):
            l.append(Exclude(ldb, x["exclude_id"]))
        return l
