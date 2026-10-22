#!/usr/bin/env bash
# Rebuild every sound in lofi/ from scratch. Needs python3 with numpy + scipy, and ffmpeg.
# usage: bash lofi/src/build.sh        (run from the repo root)
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$OUT/src"
python3 "$SRC/make_lofi.py" "$OUT"
python3 "$SRC/dudu.py" "$OUT"
python3 "$SRC/ebass.py" "$OUT"
python3 "$SRC/make_project.py" "$OUT"
cd "$OUT/audio"
ffmpeg -v error -y -i rain.wav -c:a flac -compression_level 8 rain.flac && rm rain.wav
# narrow-band parts don't need 48 kHz stereo — keeps the page light
for f in bass-*.wav melody-*.wav; do ffmpeg -v error -y -i "$f" -ac 1 -ar 24000 "tmp-$f" && mv "tmp-$f" "$f"; done
ffmpeg -v error -y -i crackle.wav -ar 24000 tmp-crackle.wav && mv tmp-crackle.wav crackle.wav
echo "done: $OUT"
