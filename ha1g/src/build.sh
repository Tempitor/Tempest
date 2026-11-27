#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
#
# Build Tempest HA1G v1.0.1 (D022) from your own stock firmware.
#   usage: ./build.sh /path/to/HA1G_V1.01.14.002_20260422.bin [OUTDIR] [--test]
# Writes OUTDIR/HA1G_V1.01.14.002_D022.bin (default OUTDIR = ./out) and checks that it is
# byte-identical to the released build. --test also runs the emulator checks (unicorn, capstone).
set -e
STOCK=${1:?usage: ./build.sh HA1G_V1.01.14.002_20260422.bin [OUTDIR]}
OUT=out; TEST=0
for a in "$2" "$3"; do case "$a" in --test) TEST=1;; "") ;; *) OUT=$a;; esac; done
HERE=$(cd "$(dirname "$0")" && pwd)
STOCK=$(cd "$(dirname "$STOCK")" && pwd)/$(basename "$STOCK")
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
T=$HERE/tools

STOCK_SHA=267bee83b844d99f76a008ab2698a822c78fd8fecc27ab6cd79e4f869e8f2d77
MON_TAFR_SHA=09a75c39fc04dac7dcc8e8a96d72aa99bf0bce37f7b4d5378db30d3eaf242943
D022_SHA=2048b495e06c8f9a04ce98e52b5e407d37febed36e0b67075a2c317cb67eb123

sha() { python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"; }
check() {
  got=$(sha "$1")
  if [ "$got" != "$2" ]; then echo "FAIL: $1 sha256 $got, expected $2" >&2; exit 1; fi
  echo "  ok  $(basename "$1")  $got"
}

echo "== stock"
check "$STOCK" $STOCK_SHA

echo "== 1/5 monitor fix + TA/FR display fix"
python3 "$T/build_mon.py"  "$STOCK"       "$OUT/mon.bin"      >/dev/null
python3 "$T/build_tafr.py" "$OUT/mon.bin" "$OUT/mon_tafr.bin" >/dev/null
check "$OUT/mon_tafr.bin" $MON_TAFR_SHA

echo "== 2/5 compile the add-on (scope.c + glue.S)"
sh "$T/vfo3/scope/make_cave_clang.sh" >/dev/null 2>&1 || { echo "FAIL: clang build, run tools/vfo3/scope/make_cave_clang.sh to see why" >&2; exit 1; }

echo "== 3/5 S-meter, band scope, waterfall, menus, themes"
python3 "$T/vfo3/scope/build_scope.py" "$OUT/mon_tafr.bin" "$OUT/scope.bin" >/dev/null

echo "== 4/5 3-VFO screens, 4-decimal display, version D022"
python3 "$T/vfo3/build_vfo3.py" "$OUT/scope.bin" "$OUT/vfo3.bin" >/dev/null

echo "== 5/5 Tempest boot logo"
HA1G_IMG="$STOCK" python3 "$T/vfo3/logo/build_logo.py" "$OUT/vfo3.bin" "$OUT/HA1G_V1.01.14.002_D022.bin" >/dev/null

echo "== result"
check "$OUT/HA1G_V1.01.14.002_D022.bin" $D022_SHA
D022="$OUT/HA1G_V1.01.14.002_D022.bin"
if [ $TEST = 1 ]; then
  echo "== tests"
  run() { if python3 "$@" > "$OUT/test.log" 2>&1; then echo "  ok  $(basename "$1")"; else cat "$OUT/test.log"; echo "FAIL: $1" >&2; exit 1; fi; }
  run "$T/verify_mon.py"  "$STOCK"       "$OUT/mon.bin"
  run "$T/verify_tafr.py" "$OUT/mon.bin" "$OUT/mon_tafr.bin"
  run "$T/vfo3/scope/verify_scope.py" "$OUT/mon_tafr.bin" "$D022"
  HA1G_IMG="$STOCK" run "$T/vfo3/logo/verify_logo.py" "$OUT/vfo3.bin" "$D022"
  rm -f "$OUT/test.log"
fi
rm -f "$OUT/mon.bin" "$OUT/scope.bin" "$OUT/vfo3.bin"
echo "Built $OUT/HA1G_V1.01.14.002_D022.bin (identical to release ha1g-v1.0.1)."
