#!/bin/sh
# build.sh -- the one command CI and a second operator run. Stages the node
# files OUTSIDE the tree, builds with every Gradle output redirected outside
# the tree, and copies the APK out. The same script runs on the runner and on
# a PC: run it where the runner runs it.
#   needs: JDK 17, Gradle 8.13 on PATH (or GRADLE=...), ANDROID_HOME with
#   platform 35 + build-tools and licences accepted, python3.12 on PATH.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
STAGEROOT="${COVENANT_APP_STAGE:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/covenant-app}"
export COVENANT_PY_STAGE="$STAGEROOT/assets"      # AGP assets srcDir; the core lands in assets/core/
export COVENANT_APP_BUILD="$STAGEROOT/build"      # every Gradle output goes here, never into the tree
sh "$HERE/stage.sh" "$ROOT" "$COVENANT_PY_STAGE/core"
export COVENANT_APP_VERSION_CODE=$(git -C "$ROOT" rev-list --count HEAD 2>/dev/null || echo 1)
export COVENANT_APP_VERSION_NAME="0.1.$COVENANT_APP_VERSION_CODE+$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo local)"
cd "$HERE"
"${GRADLE:-gradle}" --no-daemon --project-cache-dir "$STAGEROOT/.gradle" -p "$HERE" assembleDebug
cp "$COVENANT_APP_BUILD/app/outputs/apk/debug/app-debug.apk" "$STAGEROOT/covenant-node.apk"
echo "APK: $STAGEROOT/covenant-node.apk (version $COVENANT_APP_VERSION_NAME code $COVENANT_APP_VERSION_CODE)"
