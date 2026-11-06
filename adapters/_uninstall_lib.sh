#!/usr/bin/env bash
# Shared bootstrap for adapters/*/uninstall.sh
set -euo pipefail

INSTALL_HOST="${INSTALL_HOST:-}"
PLUGIN_INSTALL_REPO="${PLUGIN_INSTALL_REPO:-}"
PLUGIN_INSTALL_REF="${PLUGIN_INSTALL_REF:-latest}"
INSTALL_DRY_RUN=0
INSTALL_PREFIX=""
INSTALL_ROOT_OVERRIDE=""
FORWARD_ARGS=()

usage() {
  local host="${INSTALL_HOST:-<host>}"
  cat <<EOF
Uninstall a managed ${host} adapter plugin.

Usage:
  adapters/${host}/uninstall.sh [options]
  curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/REF/adapters/${host}/uninstall.sh \\
    | bash -s -- --repo OWNER/REPO [--ref REF] [options]

Options:
  --repo OWNER/REPO   GitHub repo for curl|bash bootstrap (or full git URL)
  --ref REF           Git ref: latest (newest v* release tag, default), a tag, or a branch; or \$PLUGIN_INSTALL_REF
  --prefix DIR        Override install root (skips host CLI registration)
  --root DIR          Use an existing checkout instead of cloning
  --dry-run           Print the plan without changing files
  -h, --help          Show this help

Examples:
  ./adapters/${host}/uninstall.sh
  curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/adapters/${host}/uninstall.sh \\
    | bash -s -- --repo OWNER/REPO
EOF
}

parse_uninstall_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --repo)
        PLUGIN_INSTALL_REPO="${2:-}"
        shift 2
        ;;
      --ref)
        PLUGIN_INSTALL_REF="${2:-}"
        shift 2
        ;;
      --prefix)
        INSTALL_PREFIX="${2:-}"
        shift 2
        ;;
      --root)
        INSTALL_ROOT_OVERRIDE="${2:-}"
        shift 2
        ;;
      --dry-run)
        INSTALL_DRY_RUN=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "error: unknown option: $1" >&2
        usage >&2
        exit 2
        ;;
    esac
  done
}

resolve_local_root() {
  local src dir
  src="${BASH_SOURCE[1]:-${BASH_SOURCE[0]:-}}"
  if [[ -z "$src" || "$src" == "bash" || "$src" == "-" || ! -f "$src" ]]; then
    return 1
  fi
  dir="$(cd "$(dirname "$src")" && pwd)"
  if [[ -f "$dir/../../.plugin/plugin.json" && -f "$dir/../_install_lib.py" ]]; then
    cd "$dir/../.." && pwd
    return 0
  fi
  return 1
}

repo_url_from_arg() {
  local repo="$1"
  case "$repo" in
    https://*|git@*|ssh://*|file://*)
      printf '%s\n' "$repo"
      ;;
    /*|./*|../*)
      printf '%s\n' "$repo"
      ;;
    */*)
      printf 'https://github.com/%s.git\n' "$repo"
      ;;
    *)
      echo "error: --repo must be OWNER/REPO, a git URL, or a local path" >&2
      return 2
      ;;
  esac
}

bootstrap_remote_root() {
  local url tmp
  if [[ -z "$PLUGIN_INSTALL_REPO" ]]; then
    echo "error: curl|bash uninstall requires --repo OWNER/REPO (or PLUGIN_INSTALL_REPO)" >&2
    echo "example: bash -s -- --repo OWNER/REPO" >&2
    return 2
  fi
  command -v git >/dev/null 2>&1 || { echo "error: git is required" >&2; return 127; }
  command -v python3 >/dev/null 2>&1 || { echo "error: python3 is required" >&2; return 127; }
  url="$(repo_url_from_arg "$PLUGIN_INSTALL_REPO")"
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/agent-plugin-uninstall.XXXXXX")"
  INSTALL_TMP_ROOT="$tmp"
  if [[ "${PLUGIN_INSTALL_REF}" == "latest" ]]; then
    PLUGIN_INSTALL_REF="$(git ls-remote --tags --refs --sort=-v:refname "$url" 'v*' | head -n 1 | sed 's#.*refs/tags/##')"
    PLUGIN_INSTALL_REF="${PLUGIN_INSTALL_REF:-main}"
  fi
  echo "[*] Bootstrapping from ${url}@${PLUGIN_INSTALL_REF} …"
  git clone --depth 1 --branch "$PLUGIN_INSTALL_REF" "$url" "$tmp/repo"
  printf '%s\n' "$tmp/repo"
}

run_uninstaller() {
  local root="$1"
  FORWARD_ARGS=(--host "$INSTALL_HOST" --uninstall)
  if [[ -n "$INSTALL_PREFIX" ]]; then
    FORWARD_ARGS+=(--prefix "$INSTALL_PREFIX")
  fi
  if [[ "$INSTALL_DRY_RUN" -eq 1 ]]; then
    FORWARD_ARGS+=(--dry-run)
  fi
  exec python3 "$root/adapters/_install_lib.py" --root "$root" "${FORWARD_ARGS[@]}"
}

uninstall_main() {
  local root=""
  if [[ -z "$INSTALL_HOST" ]]; then
    echo "error: INSTALL_HOST must be set by the host uninstall.sh" >&2
    exit 2
  fi
  parse_uninstall_args "$@"
  if [[ -n "$INSTALL_ROOT_OVERRIDE" ]]; then
    root="$(cd "$INSTALL_ROOT_OVERRIDE" && pwd)"
  elif root="$(resolve_local_root)"; then
    :
  else
    root="$(bootstrap_remote_root)"
    trap 'rm -rf "${INSTALL_TMP_ROOT:-}"' EXIT
  fi
  if [[ ! -f "$root/adapters/_install_lib.py" ]]; then
    echo "error: not an fp-enforcer checkout: $root" >&2
    exit 2
  fi
  run_uninstaller "$root"
}
