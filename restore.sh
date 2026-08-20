#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/lib/common.sh"
# shellcheck source=/dev/null
source "$ROOT/lib/transaction.sh"
# shellcheck source=/dev/null
source "$ROOT/lib/restore.sh"

if [[ "${1:-}" == "--list" ]]; then
  gbfc_list_backups
  exit 0
fi

stamp="${1:-}"
gbfc_lock_begin
trap 'gbfc_lock_end' EXIT
gbfc_restore_backup "$stamp"
