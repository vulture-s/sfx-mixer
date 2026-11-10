#!/usr/bin/env bash
# Rebuild nordic-epiano/. Everything but the piano (pads, drone, snow, wind, the forge bells), the cue sheet and the mix
# are copied from nordic-forge/, so they are byte-identical to it (regenerate those with nordic-forge/src/build.sh);
# make_nordic_epiano.py then re-voices the piano motif on the physical electric piano in epiano/epiano.py (preset D)
# and retitles project.json.
# Needs python3 with numpy + scipy + earshot (pinned commit in epiano/epiano.py), and ffmpeg.
# usage: bash nordic-epiano/src/build.sh       (run from the repo root; EARSHOT_PYTHON=<python with earshot> if it is not python3)
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)"
ORIG="$OUT/../nordic-forge"
EPY="${EARSHOT_PYTHON:-python3}"
mkdir -p "$OUT/audio"
cp "$ORIG/project.json" "$ORIG/cues.json" "$OUT/"
for f in pad-Dm9.wav pad-Bbmaj7.wav pad-Fmaj7.wav pad-Dsus2.wav drone.wav step1.wav step2.wav step3.wav step4.wav sparkle.wav wind.flac; do
  cp "$ORIG/audio/$f" "$OUT/audio/$f"
done
PYTHONUTF8=1 "$EPY" "$OUT/src/make_nordic_epiano.py" "$OUT"
cd "$OUT/audio"
# same encoding as nordic/ and nordic-forge/: the piano lives below 12 kHz, 24 kHz keeps the page light
for f in piano-*.wav; do ffmpeg -v error -y -i "$f" -ar 24000 "tmp-$f" && mv "tmp-$f" "$f"; done
echo "done: $OUT"
