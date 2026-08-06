#!/usr/bin/env bash
# claude one-liner:
#   curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/REF/adapters/claude/uninstall.sh \
#     | bash -s -- --repo OWNER/REPO --ref REF
set -euo pipefail

HOST="claude"

resolve_local_root() {
  local src dir
  src="${BASH_SOURCE[0]:-}"
  if [[ -z "$src" || "$src" == "bash" || "$src" == "-" || ! -f "$src" ]]; then
    return 1
  fi
  dir="$(cd "$(dirname "$src")" && pwd)"
  if [[ -f "$dir/../_install_lib.py" && -f "$dir/../../.plugin/plugin.json" ]]; then
    cd "$dir/../.." && pwd
    return 0
  fi
  return 1
}

bootstrap_and_reexec() {
  local -a original=("$@")
  local repo="${PLUGIN_INSTALL_REPO:-}"
  local ref="${PLUGIN_INSTALL_REF:-master}"
  local url tmp status i
  i=0
  while [[ $i -lt ${#original[@]} ]]; do
    case "${original[$i]}" in
      --repo)
        repo="${original[$((i + 1))]:-}"
        i=$((i + 2))
        ;;
      --ref)
        ref="${original[$((i + 1))]:-}"
        i=$((i + 2))
        ;;
      *)
        i=$((i + 1))
        ;;
    esac
  done
  if [[ -z "$repo" ]]; then
    echo "error: curl|bash uninstall requires --repo OWNER/REPO (or PLUGIN_INSTALL_REPO)" >&2
    echo "example: bash -s -- --repo OWNER/REPO --ref main" >&2
    exit 2
  fi
  command -v git >/dev/null 2>&1 || { echo "error: git is required" >&2; exit 127; }
  command -v python3 >/dev/null 2>&1 || { echo "error: python3 is required" >&2; exit 127; }
  case "$repo" in
    https://*|git@*|ssh://*|file://*) url="$repo" ;;
    /*|./*|../*) url="$repo" ;;
    */*) url="https://github.com/${repo}.git" ;;
    *) echo "error: --repo must be OWNER/REPO, a git URL, or a local path" >&2; exit 2 ;;
  esac
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/agent-plugin-uninstall.XXXXXX")"
  echo "[*] Bootstrapping from ${url}@${ref} …"
  git clone --depth 1 --branch "$ref" "$url" "$tmp/repo"
  set +e
  "$tmp/repo/adapters/${HOST}/uninstall.sh" "${original[@]}"
  status=$?
  set -e
  rm -rf "$tmp"
  exit "$status"
}

if ROOT="$(resolve_local_root)"; then
  # shellcheck disable=SC1091
  source "$ROOT/adapters/_uninstall_lib.sh"
  INSTALL_HOST="$HOST"
  uninstall_main --root "$ROOT" "$@"
else
  bootstrap_and_reexec "$@"
fi
