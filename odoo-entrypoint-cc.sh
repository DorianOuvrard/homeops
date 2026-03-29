#!/bin/bash
set -e

export PGDATABASE="${POSTGRESQL_ADDON_DB}"

exec /usr/bin/odoo \
  --db_host="${POSTGRESQL_ADDON_HOST}" \
  --db_port="${POSTGRESQL_ADDON_PORT:-5432}" \
  --db_user="${POSTGRESQL_ADDON_USER}" \
  --db_password="${POSTGRESQL_ADDON_PASSWORD}" \
  --db-filter="^${POSTGRESQL_ADDON_DB}$" \
  --http-port="${PORT:-8069}" \
  --proxy-mode \
  --no-database-list
