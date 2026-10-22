#!/usr/bin/env bash
# Rebuild every sound in nordic/ from scratch. Needs python3 with numpy + scipy, and ffmpeg.
# usage: bash nordic/src/build.sh        (run from the repo root)
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$OUT/src/make_nordic.py" "$OUT"
cd "$OUT/audio"
# wind, pads and piano live below 12 kHz — 24 kHz keeps the page light
ffmpeg -v error -y -i wind.wav -ar 24000 -c:a flac -compression_level 8 wind.flac && rm wind.wav
for f in pad-*.wav piano-*.wav; do ffmpeg -v error -y -i "$f" -ar 24000 "tmp-$f" && mv "tmp-$f" "$f"; done
ffmpeg -v error -y -i drone.wav -ac 1 -ar 24000 tmp-drone.wav && mv tmp-drone.wav drone.wav
echo "done: $OUT"
