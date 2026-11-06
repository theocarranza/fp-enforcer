#!/usr/bin/env bash
# Shared bootstrap for adapters/*/install.sh
# Local: run from a clone. Remote: curl|bash with --repo OWNER/REPO [--ref REF]
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
Install the ${host} adapter plugin.

Plain install replaces any prior managed install of this plugin (one command to upgrade).
To remove without installing, use adapters/${host}/uninstall.sh.

Usage:
  adapters/${host}/install.sh [options]
  curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/REF/adapters/${host}/install.sh \\
    | bash -s -- --repo OWNER/REPO [--ref REF] [options]

Options:
  --repo OWNER/REPO   GitHub repo for curl|bash bootstrap (or full git URL)
  --ref REF           Git ref: latest (newest v* release tag, default), a tag, or a branch; or \$PLUGIN_INSTALL_REF
  --prefix DIR        Override install root (skips host CLI registration)
  --root DIR          Use an existing checkout instead of cloning
  --dry-run           Print the plan without changing files
  -h, --help          Show this help

Environment:
  PLUGIN_INSTALL_REPO   Same as --repo
  PLUGIN_INSTALL_REF    Same as --ref
  CURSOR_HOME / CLAUDE_HOME / CODEX_HOME / AGENTS_HOME

Examples:
  ./adapters/${host}/install.sh
  ./adapters/${host}/install.sh --dry-run
  curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/adapters/${host}/install.sh \\
    | bash -s -- --repo OWNER/REPO
EOF
}

parse_install_args() {
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
      --uninstall)
        echo "error: --uninstall was removed from install.sh" >&2
        echo "use: adapters/${INSTALL_HOST:-<host>}/uninstall.sh" >&2
        exit 2
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
  # adapters/<host>/install.sh -> repo root
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
    echo "error: curl|bash install requires --repo OWNER/REPO (or PLUGIN_INSTALL_REPO)" >&2
    echo "example: bash -s -- --repo OWNER/REPO" >&2
    return 2
  fi
  if ! command -v git >/dev/null 2>&1; then
    echo "error: git is required for curl|bash install" >&2
    return 127
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 is required" >&2
    return 127
  fi
  url="$(repo_url_from_arg "$PLUGIN_INSTALL_REPO")"
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/agent-plugin-install.XXXXXX")"
  # Caller owns cleanup via INSTALL_TMP_ROOT
  INSTALL_TMP_ROOT="$tmp"
  if [[ "${PLUGIN_INSTALL_REF}" == "latest" ]]; then
    PLUGIN_INSTALL_REF="$(git ls-remote --tags --refs --sort=-v:refname "$url" 'v*' | head -n 1 | sed 's#.*refs/tags/##')"
    PLUGIN_INSTALL_REF="${PLUGIN_INSTALL_REF:-main}"
  fi
  echo "[*] Bootstrapping from ${url}@${PLUGIN_INSTALL_REF} …"
  git clone --depth 1 --branch "$PLUGIN_INSTALL_REF" "$url" "$tmp/repo"
  printf '%s\n' "$tmp/repo"
}

build_python_args() {
  FORWARD_ARGS=(--host "$INSTALL_HOST")
  if [[ -n "$INSTALL_PREFIX" ]]; then
    FORWARD_ARGS+=(--prefix "$INSTALL_PREFIX")
  fi
  if [[ "$INSTALL_DRY_RUN" -eq 1 ]]; then
    FORWARD_ARGS+=(--dry-run)
  fi
}

run_installer() {
  local root="$1"
  build_python_args
  exec python3 "$root/adapters/_install_lib.py" --root "$root" "${FORWARD_ARGS[@]}"
}

install_main() {
  local root=""
  if [[ -z "$INSTALL_HOST" ]]; then
    echo "error: INSTALL_HOST must be set by the host install.sh" >&2
    exit 2
  fi
  parse_install_args "$@"
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
  run_installer "$root"
}
