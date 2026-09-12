#!/bin/sh
# stage.sh -- copy the allowlisted node files from the repo root to a directory
# OUTSIDE the checkout, and write a STAMP (sha256 over the staged bytes) beside
# them. This is how the APK carries the core without a second copy of it ever
# existing in the tree: test_p18 forbids that, and this script refuses a
# destination inside the checkout for the same reason.
#   usage: sh mobile/app/stage.sh <repo root> <dest dir>     (build.sh calls it)
set -eu
ROOT=$(cd "$1" && pwd); DEST=$2
case "$DEST" in
  "$ROOT"/*|"$ROOT") echo "refusing: $DEST is inside the checkout (test_p18 forbids a second copy of the core)"; exit 2;;
esac
LIST="$ROOT/mobile/app/python_sources.txt"
rm -rf "$DEST"; mkdir -p "$DEST"
sed 's/#.*//' "$LIST" | tr -d '\r' | while read -r f; do
  [ -n "$f" ] || continue
  case "$f" in */*) echo "refusing subpath $f (root-level names only)"; exit 1;; esac
  [ -f "$ROOT/$f" ] || { echo "python_sources.txt names $f but it is not at the repo root"; exit 1; }
  cp "$ROOT/$f" "$DEST/$f"
done
( cd "$DEST" && ls | LC_ALL=C sort | xargs sha256sum ) | sha256sum | cut -d' ' -f1 > "$DEST/STAMP"
echo "staged $(ls "$DEST" | wc -l) files to $DEST (STAMP $(cat "$DEST/STAMP"))"
