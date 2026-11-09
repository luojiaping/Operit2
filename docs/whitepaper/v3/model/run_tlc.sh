#!/usr/bin/env bash
# Runs every experiment listed in experiments.txt with TLC and stores the logs
# under results/.  Usage:
#   TLA2TOOLS=/path/to/tla2tools.jar ./run_tlc.sh [experiment-name ...]
# The whitepaper results were produced with tla2tools.jar v1.7.4
# (sha256 936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88)
# on OpenJDK 21.  TLC metadata is written to ${TLC_META:-$TMPDIR/tlc-meta}.
set -euo pipefail
cd "$(dirname "$0")"
: "${TLA2TOOLS:?set TLA2TOOLS to the path of tla2tools.jar}"
META="${TLC_META:-${TMPDIR:-/tmp}/tlc-meta}"
mkdir -p results "$META"
names=("$@")
if [ ${#names[@]} -eq 0 ]; then
  mapfile -t names < <(cut -d'|' -f1 experiments.txt)
fi
for name in "${names[@]}"; do
  echo "== $name"
  set +e
  java -XX:+UseParallelGC -cp "$TLA2TOOLS" tlc2.TLC -deadlock -workers auto \
       -metadir "$META/$name" -config "cfg/$name.cfg" TurnHandoff.tla > "results/$name.log" 2>&1
  status=$?
  set -e
  echo "   TLC exit status $status"
  grep -E "is violated|No error has been found|states generated|depth of the complete" "results/$name.log" | sed 's/^/   /'
done
