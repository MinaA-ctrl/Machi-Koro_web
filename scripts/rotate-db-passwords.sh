#!/usr/bin/env bash
# Rotate the MySQL (WordPress) and Postgres (game backend) passwords.
#
# Run from the project root on the machine where the docker compose stack runs:
#   ./scripts/rotate-db-passwords.sh --check   # verify access only, change nothing
#   ./scripts/rotate-db-passwords.sh           # rotate
#
# Steps: generate new random passwords → change them INSIDE MySQL and Postgres
# (editing .env alone does nothing: the databases already exist) → write them to
# .env → recreate the containers that read them. Passwords are never printed.
set -euo pipefail

MYSQL_CONTAINER=machikoro_db
PG_CONTAINER=machikoro_postgres
ENV_FILE=.env

die() { echo "❌ $*" >&2; exit 1; }
env_get() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-; }

[ -f "$ENV_FILE" ] || die "No $ENV_FILE here. Run this from the project root."
command -v docker >/dev/null || die "docker not found."
command -v openssl >/dev/null || die "openssl not found."
for c in "$MYSQL_CONTAINER" "$PG_CONTAINER"; do
  [ "$(docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null)" = "true" ] \
    || die "Container $c is not running. Start the stack first: docker compose up -d"
done

OLD_ROOT=$(env_get MYSQL_ROOT_PASSWORD)
MYSQL_USER=$(env_get MYSQL_USER)
PG_USER=$(env_get POSTGRES_USER); PG_USER=${PG_USER:-machikoro}
PG_DB=$(env_get POSTGRES_DB); PG_DB=${PG_DB:-machikoro}
[ -n "$OLD_ROOT" ] && [ -n "$MYSQL_USER" ] || die "MYSQL_ROOT_PASSWORD / MYSQL_USER missing from $ENV_FILE."

mysql_root() { docker exec -i -e MYSQL_PWD="$1" "$MYSQL_CONTAINER" mysql -uroot -N -e "$2"; }
pg() { docker exec -i "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -q -U "$PG_USER" -d "$PG_DB" -c "$1"; }

echo "🔎 Checking access…"
mysql_root "$OLD_ROOT" "SELECT 1" >/dev/null \
  || die "Can't log in to MySQL as root with the password in $ENV_FILE. Nothing was changed."
pg "SELECT 1" >/dev/null || die "Can't reach Postgres as $PG_USER. Nothing was changed."
echo "✅ MySQL and Postgres reachable."
if [ "${1:-}" = "--check" ]; then echo "Check only — nothing changed."; exit 0; fi

NEW_ROOT=$(openssl rand -hex 24)
NEW_MYSQL=$(openssl rand -hex 24)
NEW_PG=$(openssl rand -hex 24)

echo "🔑 Changing MySQL passwords…"
# The official image creates root@'%' and root@'localhost'; change whichever exist.
mysql_root "$OLD_ROOT" "
  ALTER USER IF EXISTS 'root'@'%' IDENTIFIED BY '$NEW_ROOT';
  ALTER USER IF EXISTS 'root'@'localhost' IDENTIFIED BY '$NEW_ROOT';
  ALTER USER '$MYSQL_USER'@'%' IDENTIFIED BY '$NEW_MYSQL';
  FLUSH PRIVILEGES;"

echo "🔑 Changing Postgres password…"
pg "ALTER USER \"$PG_USER\" PASSWORD '$NEW_PG';"

echo "📝 Updating $ENV_FILE…"
TMP=$(mktemp)
awk -v r="$NEW_ROOT" -v m="$NEW_MYSQL" -v p="$NEW_PG" '
  /^MYSQL_ROOT_PASSWORD=/ { print "MYSQL_ROOT_PASSWORD=" r; next }
  /^MYSQL_PASSWORD=/      { print "MYSQL_PASSWORD=" m; next }
  /^POSTGRES_PASSWORD=/   { print "POSTGRES_PASSWORD=" p; seen=1; next }
  { print }
  END { if (!seen) print "POSTGRES_PASSWORD=" p }
' "$ENV_FILE" > "$TMP"
chmod 600 "$TMP"
mv "$TMP" "$ENV_FILE"

echo "🔄 Restarting services with the new passwords…"
docker compose up -d

echo "🔎 Verifying…"
sleep 5
mysql_root "$NEW_ROOT" "SELECT 1" >/dev/null && echo "✅ MySQL root: new password works."
docker exec -i -e MYSQL_PWD="$NEW_MYSQL" "$MYSQL_CONTAINER" mysql -u"$MYSQL_USER" -N -e "SELECT 1" >/dev/null \
  && echo "✅ WordPress DB user: new password works."
echo "Done. Open the site and check that WordPress pages and a game table both load."
