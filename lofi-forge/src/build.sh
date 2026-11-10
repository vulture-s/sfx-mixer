#!/usr/bin/env bash
# Rebuild lofi-forge/. The parts the forge cannot voice (snare, bass, dudu, electronic bass, crackle, rain), the cue sheet
# and the mix are copied from lofi/, so they are byte-identical to the original (regenerate those with lofi/src/build.sh);
# make_lofi_forge.py then re-voices kicks, hats, keys and melody from the earshot bank and retitles project.json.
# Needs python3 with numpy + scipy + earshot (see make_lofi_forge.py for the pinned commit), and ffmpeg.
# usage: bash lofi-forge/src/build.sh        (run from the repo root; EARSHOT_PYTHON=<python with earshot> if it is not python3)
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)"
ORIG="$OUT/../lofi"
EPY="${EARSHOT_PYTHON:-python3}"
mkdir -p "$OUT/audio"
cp "$ORIG/project.json" "$ORIG/cues.json" "$OUT/"
for f in snare1.wav snare2.wav bass-F.wav bass-E.wav bass-Am.wav bass-GmC.wav dudu.wav ebass.wav crackle.wav rain.flac; do
  cp "$ORIG/audio/$f" "$OUT/audio/$f"
done
PYTHONUTF8=1 "$EPY" "$OUT/src/make_lofi_forge.py" "$OUT"
cd "$OUT/audio"
# same encoding as lofi/: the melody is narrow-band, mono 24 kHz keeps the page light
for f in melody-*.wav; do ffmpeg -v error -y -i "$f" -ac 1 -ar 24000 "tmp-$f" && mv "tmp-$f" "$f"; done
echo "done: $OUT"
