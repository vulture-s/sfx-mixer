#!/usr/bin/env bash
# Rebuild nordic-forge/. The parts the forge cannot voice (pads, drone, snow, wind), the cue sheet and the mix are
# copied from nordic/, so they are byte-identical to the original (regenerate those with nordic/src/build.sh);
# make_nordic_forge.py then re-voices the tuned parts from the earshot bank and retitles project.json.
# Needs python3 with numpy + scipy + earshot (see make_nordic_forge.py for the pinned commit), and ffmpeg.
# usage: bash nordic-forge/src/build.sh        (run from the repo root; EARSHOT_PYTHON=<python with earshot> if it is not python3)
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)"
ORIG="$OUT/../nordic"
EPY="${EARSHOT_PYTHON:-python3}"
mkdir -p "$OUT/audio"
cp "$ORIG/project.json" "$ORIG/cues.json" "$OUT/"
for f in pad-Dm9.wav pad-Bbmaj7.wav pad-Fmaj7.wav pad-Dsus2.wav drone.wav step1.wav step2.wav step3.wav step4.wav wind.flac; do
  cp "$ORIG/audio/$f" "$OUT/audio/$f"
done
PYTHONUTF8=1 "$EPY" "$OUT/src/make_nordic_forge.py" "$OUT"
cd "$OUT/audio"
# same encoding as nordic/: piano lives below 12 kHz — 24 kHz keeps the page light; the bells stay at 48 kHz
for f in piano-*.wav; do ffmpeg -v error -y -i "$f" -ar 24000 "tmp-$f" && mv "tmp-$f" "$f"; done
echo "done: $OUT"
