#!/usr/bin/env bash
# Shared environment bootstrap. Source this file; do not execute it.

kn_project_root() {
  (cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
}

PROJECT_ROOT="${PROJECT_ROOT:-$(kn_project_root)}"

# Print a path unchanged when absolute, or resolved from the project root when relative.
kn_resolve_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s\n' "$PROJECT_ROOT/$1" ;;
  esac
}

kn_path_device() {
  local path="$1"
  local parent
  while [ -n "$path" ] && [ ! -e "$path" ]; do
    parent="$(dirname "$path")"
    [ "$parent" = "$path" ] && break
    path="$parent"
  done
  [ -e "$path" ] || return 1
  stat -c '%d' "$path" 2>/dev/null || stat -f '%d' "$path" 2>/dev/null
}

kn_export_uv_link_mode() {
  local mode="${UV_LINK_MODE:-}"
  if [ -n "$mode" ] && [ "${mode,,}" != "auto" ]; then
    export UV_LINK_MODE
    return 0
  fi

  unset UV_LINK_MODE
  command -v uv >/dev/null 2>&1 || return 0
  local cache_device
  local root_device
  cache_device="$(kn_path_device "$(uv cache dir 2>/dev/null)")" || cache_device=""
  root_device="$(kn_path_device "$PROJECT_ROOT/.venv")" || root_device=""
  if [ -n "$cache_device" ] && [ -n "$root_device" ] && [ "$cache_device" != "$root_device" ]; then
    export UV_LINK_MODE=copy
  fi
}

kn_export_tool_caches() {
  export RUFF_CACHE_DIR="${RUFF_CACHE_DIR:-$DATA_DIR/cache/ruff}"
  export MYPY_CACHE_DIR="${MYPY_CACHE_DIR:-$DATA_DIR/cache/mypy}"
}

kn_load_env() {
  # shellcheck source=/dev/null
  if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    . "$PROJECT_ROOT/.env"
    set +a
  fi
  DATA_DIR="$(kn_resolve_path "${DATA_DIR:-.data}")"
  export DATA_DIR
  kn_export_tool_caches
  kn_export_uv_link_mode
}

# Local database service (deploy/compose.yaml). Call kn_load_env first.
KN_COMPOSE_FILE="$PROJECT_ROOT/deploy/compose.yaml"
KN_DB_SERVICE="postgres"
KN_DB_NAME="kn"
KN_DB_SUPERUSER="postgres"
KN_DB_BOOTSTRAP_SQL="/docker-entrypoint-initdb.d/10-kn-bootstrap.sql"
KN_DB_VERIFY_SQL="$PROJECT_ROOT/deploy/postgres/verify-roles.sql"
KN_DB_WAIT_TIMEOUT_SECONDS=180
KN_DB_LOG_TAIL_LINES=30
KN_DB_PASSWORD_BYTES=32

kn_db_volume_dir() {
  printf '%s\n' "$DATA_DIR/postgres"
}

kn_db_password_file() {
  if [ -n "${KN_POSTGRES_PASSWORD_FILE:-}" ]; then
    kn_resolve_path "$KN_POSTGRES_PASSWORD_FILE"
  else
    printf '%s\n' "$DATA_DIR/secrets/postgres-password"
  fi
}

# Create a random superuser password at the default location. A configured file must exist.
kn_db_ensure_password() {
  local file
  file="$(kn_db_password_file)"
  [ -s "$file" ] && return 0
  if [ -e "$file" ] || [ -n "${KN_POSTGRES_PASSWORD_FILE:-}" ]; then
    echo "ERROR: database password file $file is missing or empty" >&2
    return 1
  fi
  (
    umask 077
    mkdir -p "$(dirname "$file")"
    od -An -tx1 -N"$KN_DB_PASSWORD_BYTES" /dev/urandom | tr -d ' \n' >"$file"
  ) || return 1
  echo "Created database superuser password file $file"
}

# Run docker compose on the KN stack as the invoking non-root user.
kn_compose() {
  local uid
  uid="$(id -u)"
  if [ "$uid" = "0" ]; then
    echo "ERROR: run the local services as a regular user in the docker group, not root" >&2
    return 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Engine with the Compose v2 plugin is required" >&2
    return 1
  fi
  KN_UID="$uid" KN_GID="$(id -g)" KN_POSTGRES_PASSWORD_FILE="$(kn_db_password_file)" \
    docker compose --file "$KN_COMPOSE_FILE" "$@"
}

# Run psql as the superuser in database kn inside the running service container.
kn_db_psql() {
  kn_compose exec -T "$KN_DB_SERVICE" psql -X -q -v ON_ERROR_STOP=1 \
    --username="$KN_DB_SUPERUSER" --dbname="$KN_DB_NAME" "$@"
}

kn_db_up() {
  local volume
  volume="$(kn_db_volume_dir)"
  kn_db_ensure_password || return 1
  mkdir -p "$volume" || return 1
  chmod 0700 "$volume" || return 1
  if ! kn_compose up --detach --wait --wait-timeout "$KN_DB_WAIT_TIMEOUT_SECONDS" \
    "$KN_DB_SERVICE"; then
    kn_compose logs --tail "$KN_DB_LOG_TAIL_LINES" "$KN_DB_SERVICE" >&2
    echo "ERROR: the database did not become healthy; see the log above." \
      "A failed first initialization needs make db-reset." >&2
    return 1
  fi
  kn_db_psql --file="$KN_DB_BOOTSTRAP_SQL"
}

kn_db_down() {
  kn_compose down
}

kn_db_verify() {
  kn_db_psql <"$KN_DB_VERIFY_SQL"
}

# Delete the database volume and start from empty. The password file is kept.
kn_db_reset() {
  local volume
  case "$DATA_DIR" in
    /?*) ;;
    *)
      echo "ERROR: DATA_DIR must be an absolute path below /, got '$DATA_DIR'" >&2
      return 1
      ;;
  esac
  volume="$(kn_db_volume_dir)"
  kn_compose down || return 1
  echo "Removing $volume"
  rm -rf -- "$volume" || return 1
  kn_db_up
}
