#!/usr/bin/env python3
"""Odoo starter for Clever Cloud managed PostgreSQL.

CC doesn't grant access to the 'postgres' database, which Odoo 17 uses
for DB existence checks and creation. This wrapper patches those functions
to work directly with the pre-provisioned database.
"""
import sys
import odoo
from odoo.service import db as db_service


def _cc_db_exist(db_name):
    """Check DB existence by connecting directly instead of via 'postgres'."""
    try:
        conn = odoo.sql_db.db_connect(db_name)
        with conn.cursor() as cr:
            cr.execute("SELECT 1")
            return True
    except Exception:
        return False


def _cc_create_empty_database(name):
    """Initialize extensions in the existing CC database."""
    db = odoo.sql_db.db_connect(name)
    conn = db.cursor()
    conn._obj.connection.autocommit = True
    conn.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    conn.close()


db_service.db_exist = _cc_db_exist
db_service.exp_db_exist = _cc_db_exist
db_service._create_empty_database = _cc_create_empty_database

sys.exit(odoo.cli.main())
