#!/bin/sh
# Diagonal addressing smoke: X0/Y0 through X63/Y63, in two transients.
# Prints RESULT PASS only when both halves pass.
cd "$(dirname "$0")" || exit 1
fail=0
for deck in array64x64_cycle_tb.cir array64x64_cycle_hi.cir; do
  log=$(mktemp)
  ngspice -b -o "$log" "$deck" >/dev/null 2>&1 || fail=1
  if ! grep -q "RESULT PASS" "$log"; then
    grep "FAIL " "$log" || echo "FAIL $deck did not pass"
    fail=1
  fi
  rm -f "$log"
done
if [ "$fail" -eq 0 ]; then
  echo RESULT PASS
else
  echo RESULT FAIL
  exit 1
fi
