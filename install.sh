#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/lib/common.sh"
# shellcheck source=/dev/null
source "$ROOT/lib/transaction.sh"
# shellcheck source=/dev/null
source "$ROOT/lib/design-bank.sh"
# shellcheck source=/dev/null
source "$ROOT/lib/tools.sh"
# shellcheck source=/dev/null
source "$ROOT/lib/skills.sh"
# shellcheck source=/dev/null
source "$ROOT/lib/doctor.sh"
# shellcheck source=/dev/null
source "$ROOT/lib/install.sh"

usage() {
  cat <<'USAGE_EOF'
Install AntigravityBestFriend as a native Antigravity CLI plugin.

Usage:
  ./install.sh --dry-run
  ./install.sh
  ./install.sh --doctor
  ./install.sh --doctor --repair
  ./install.sh --restore [stamp]
  ./install.sh --recover
  ./install.sh --skip-design-bank
USAGE_EOF
}

mode="install"
restore_stamp=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) GBFC_DRY_RUN=1 ;;
    --doctor) mode="doctor" ;;
    --repair) GBFC_REPAIR=1 ;;
    --skip-design-bank) GBFC_SKIP_DESIGN_BANK=1 ;;
    --help|-h) usage; exit 0 ;;
    --restore)
      mode="restore"
      if [[ $# -ge 2 && ! "$2" =~ ^-- ]]; then
        shift
        restore_stamp="$1"
      fi
      ;;
    --recover) mode="recover" ;;
    *)
      if [[ "$mode" == "restore" && -z "$restore_stamp" ]]; then
        restore_stamp="$1"
      else
        gbfc_die "Unknown argument: $1"
      fi
      ;;
  esac
  shift
done

case "$mode" in
  doctor)
    gbfc_doctor || exit 1
    ;;
  restore)
    # shellcheck source=/dev/null
    source "$ROOT/lib/restore.sh"
    gbfc_lock_begin
    trap 'gbfc_lock_end' EXIT
    if [[ -z "$restore_stamp" ]]; then
      restore_stamp="$(gbfc_tx_backup_stamp)"
    fi
    [[ -n "$restore_stamp" ]] || gbfc_die "no backup stamp specified"
    gbfc_restore_backup "$restore_stamp"
    gbfc_tx_clear
    ;;
  recover)
    gbfc_lock_begin
    trap 'gbfc_lock_end' EXIT
    gbfc_tx_recover
    ;;
  install)
    trap 'gbfc_lock_end' EXIT
    gbfc_run_install
    ;;
esac
