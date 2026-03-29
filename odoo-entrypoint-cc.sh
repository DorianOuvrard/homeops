#!/bin/bash
set -e

exec python3 /usr/local/bin/odoo_cc_start.py \
  --db_host="${POSTGRESQL_ADDON_HOST}" \
  --db_port="${POSTGRESQL_ADDON_PORT:-5432}" \
  --db_user="${POSTGRESQL_ADDON_USER}" \
  --db_password="${POSTGRESQL_ADDON_PASSWORD}" \
  -d "${POSTGRESQL_ADDON_DB}" \
  --db-filter="^${POSTGRESQL_ADDON_DB}$" \
  -i maintenance_image \
  -u maintenance \
  --http-port="${PORT:-8069}" \
  --proxy-mode
