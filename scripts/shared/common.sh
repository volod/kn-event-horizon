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
KN_DB_WAIT_TIMEOUT_SECONDS=180
KN_DB_LOG_TAIL_LINES=30
KN_DB_PASSWORD_BYTES=32
KN_DB_HOST_ADDRESS="127.0.0.1"
# Non-standard, so that another PostgreSQL on the same host keeps 5432.
KN_DB_HOST_PORT_DEFAULT=15432
KN_DB_HOST_PORT_MAX=65535

# Print the loopback port that publishes the database; refuse a value that is not a TCP port.
kn_db_host_port() {
  local port="${KN_POSTGRES_HOST_PORT:-$KN_DB_HOST_PORT_DEFAULT}"
  # One to five digits without a leading zero, so the numeric comparison cannot overflow.
  if [[ "$port" =~ ^[1-9][0-9]{0,4}$ ]] && [ "$port" -le "$KN_DB_HOST_PORT_MAX" ]; then
    printf '%s\n' "$port"
    return 0
  fi
  echo "ERROR: KN_POSTGRES_HOST_PORT must be a port from 1 to $KN_DB_HOST_PORT_MAX, got '$port'" >&2
  return 1
}

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
  local port
  uid="$(id -u)"
  if [ "$uid" = "0" ]; then
    echo "ERROR: run the local services as a regular user in the docker group, not root" >&2
    return 1
  fi
  port="$(kn_db_host_port)" || return 1
  if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Engine with the Compose v2 plugin is required" >&2
    return 1
  fi
  KN_UID="$uid" KN_GID="$(id -g)" KN_POSTGRES_PASSWORD_FILE="$(kn_db_password_file)" \
    KN_POSTGRES_HOST_PORT="$port" docker compose --file "$KN_COMPOSE_FILE" "$@"
}

# Run psql as the superuser in database kn inside the running service container.
kn_db_psql() {
  kn_compose exec -T "$KN_DB_SERVICE" psql -X -q -v ON_ERROR_STOP=1 \
    --username="$KN_DB_SUPERUSER" --dbname="$KN_DB_NAME" "$@"
}

kn_db_up() {
  local volume
  local port
  volume="$(kn_db_volume_dir)"
  port="$(kn_db_host_port)" || return 1
  kn_db_ensure_password || return 1
  mkdir -p "$volume" || return 1
  chmod 0700 "$volume" || return 1
  if ! kn_compose up --detach --wait --wait-timeout "$KN_DB_WAIT_TIMEOUT_SECONDS" \
    "$KN_DB_SERVICE"; then
    kn_compose logs --tail "$KN_DB_LOG_TAIL_LINES" "$KN_DB_SERVICE" >&2
    echo "ERROR: the database did not become healthy; see the output above." \
      "If $KN_DB_HOST_ADDRESS:$port is in use, set KN_POSTGRES_HOST_PORT in .env." \
      "A failed first initialization needs make db-reset." >&2
    return 1
  fi
  kn_db_govern upgrade || return 1
  echo "Database $KN_DB_NAME is on $KN_DB_HOST_ADDRESS:$port" \
    "(user $KN_DB_SUPERUSER, password in $(kn_db_password_file))"
}

kn_db_down() {
  kn_compose down
}

kn_db_govern() {
  local port
  port="$(kn_db_host_port)" || return 1
  KN_DATABASE_URL="postgresql://$KN_DB_SUPERUSER@$KN_DB_HOST_ADDRESS:$port/$KN_DB_NAME" \
    KN_DATABASE_PASSWORD_FILE="$(kn_db_password_file)" \
    "$PROJECT_ROOT/.venv/bin/kn" db "$1"
}

kn_db_verify() {
  kn_db_govern verify
}

# Export the integration test connection (tests/integration/harness.py): the loopback port as a
# URI without a password, and the password file that holds it.
kn_db_test_env() {
  local port
  port="$(kn_db_host_port)" || return 1
  KN_TEST_DATABASE_URL="postgresql://$KN_DB_SUPERUSER@$KN_DB_HOST_ADDRESS:$port/$KN_DB_NAME"
  KN_TEST_DATABASE_PASSWORD_FILE="$(kn_db_password_file)"
  export KN_TEST_DATABASE_URL KN_TEST_DATABASE_PASSWORD_FILE
}

# Delete the database volume and start from empty. The password file is kept.
kn_db_reset() {
  if [ "${KN_ENVIRONMENT:-}" = "released" ]; then
    echo "ERROR: database reset is refused in a released environment" >&2
    return 1
  fi
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
