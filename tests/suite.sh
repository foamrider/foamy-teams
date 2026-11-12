#!/bin/bash
# foamy-teams' own tests; tests/validate.sh runs this after the linters.
#   --ci    no Quickshell, no Omarchy host: the node tests only
#   --fast  skip the offscreen Quickshell tests
set -uo pipefail
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." || exit 1
ci=0 fast=0
for arg in "$@"; do
  case $arg in
    --ci) ci=1 ;;
    --fast) fast=1 ;;
    *)
      echo "suite.sh: unknown argument $arg" >&2
      exit 2
      ;;
  esac
done
status=0
run() {
  echo "== $*"
  "$@" || status=1
}
skip() { echo "SKIP $*"; }
run node tests/model.test.js
run node tests/i18n.test.cjs
run node tests/launch.test.js
if ((ci || fast)); then
  skip "tests/runtime.py and the kit's i18n_runtime.py: offscreen Quickshell on the Omarchy shell"
elif [[ -z ${FOAMY_KIT:-} ]]; then
  echo "suite.sh: the runtime tests need foamy-kit; set FOAMY_KIT" >&2
  status=1
else
  run python3 -I "$FOAMY_KIT/preview/i18n_runtime.py" .
  run python3 -I tests/runtime.py
fi
exit $status
