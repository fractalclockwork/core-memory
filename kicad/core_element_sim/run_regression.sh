#!/bin/sh
# L0 / L1 (+ optional L2 / L3) regression suite.
# Usage:
#   ./run_regression.sh           # L0 + L1
#   ./run_regression.sh --l2      # also L2 decks
#   ./run_regression.sh --ideal   # also L3 ideal decks
#   ./run_regression.sh --all     # L0–L3
set -eu
cd "$(dirname "$0")/models" || exit 1

run_expect() {
  deck=$1
  expect=$2
  log=$(mktemp)
  if ! ngspice -b -o "$log" "$deck" >/dev/null 2>&1; then
    echo "FAIL $deck ngspice exited non-zero"
    rm -f "$log"
    return 1
  fi
  if grep -q "FAIL transient did not produce" "$log" || grep -q "Timestep too small" "$log"; then
    echo "FAIL $deck simulation aborted"
    grep -E 'FAIL |Timestep|Error' "$log" | head -10 || true
    rm -f "$log"
    return 1
  fi
  if grep -q "RESULT PASS" "$log"; then
    got=PASS
  elif grep -q "RESULT FAIL" "$log"; then
    got=FAIL
  else
    echo "FAIL $deck no RESULT line"
    grep -E 'FAIL |Error|error' "$log" | head -20 || true
    rm -f "$log"
    return 1
  fi
  rm -f "$log"
  if [ "$got" = "$expect" ]; then
    echo "OK $deck ($expect)"
    return 0
  fi
  echo "FAIL $deck got $got want $expect"
  return 1
}

# L1 single-CCS deck: PASS means the failure mode was recorded (no flip).
L0_L1="ideal_core_tb.cir:PASS coremem_tb.cir:PASS array2x2_tb.cir:PASS array2x2_cycle_tb.cir:PASS"
L2="array2x2_drive_tb.cir:PASS array2x2_matrix_tb.cir:PASS array2x2_inhibit_tb.cir:PASS array2x2_sense_tb.cir:PASS array2x2_e2e_tb.cir:PASS array2x2_strobe_tb.cir:PASS"
L3="array_ideal_nxn_tb.cir:PASS array64x64_ideal_tb.cir:PASS"

do_l2=0
do_ideal=0
for arg in "$@"; do
  case "$arg" in
    --l2) do_l2=1 ;;
    --ideal) do_ideal=1 ;;
    --all) do_l2=1; do_ideal=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
  esac
done

fail=0
for item in $L0_L1; do
  deck=${item%:*}; expect=${item#*:}
  run_expect "$deck" "$expect" || fail=1
done
if [ "$do_l2" -eq 1 ]; then
  for item in $L2; do
    deck=${item%:*}; expect=${item#*:}
    run_expect "$deck" "$expect" || fail=1
  done
fi
if [ "$do_ideal" -eq 1 ]; then
  for item in $L3; do
    deck=${item%:*}; expect=${item#*:}
    if [ ! -f "$deck" ]; then
      echo "FAIL $deck missing — run: uv run python kicad/scripts/gen_pipeline.py --spice-only"
      fail=1
      continue
    fi
    run_expect "$deck" "$expect" || fail=1
  done
fi

if [ "$fail" -eq 0 ]; then
  echo RESULT PASS
  exit 0
fi
echo RESULT FAIL
exit 1
