#!/usr/bin/env bash
# Rebuild lofi-epiano/. Everything but the keys (drums, bass, the forge kalimba melody, dudu, electronic bass, crackle,
# rain), the cue sheet and the mix are copied from lofi-forge/, so they are byte-identical to it (regenerate those with
# lofi-forge/src/build.sh); make_lofi_epiano.py then re-voices the keys on the physical electric piano in
# epiano/epiano.py (preset D, amp drive lowered for chords) and retitles project.json.
# Needs python3 with numpy + scipy + earshot (pinned commit in epiano/epiano.py).
# usage: bash lofi-epiano/src/build.sh        (run from the repo root; EARSHOT_PYTHON=<python with earshot> if it is not python3)
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)"
ORIG="$OUT/../lofi-forge"
EPY="${EARSHOT_PYTHON:-python3}"
mkdir -p "$OUT/audio"
cp "$ORIG/project.json" "$ORIG/cues.json" "$OUT/"
for f in kick1.wav kick2.wav hat1.wav hat2.wav hat3.wav snare1.wav snare2.wav bass-F.wav bass-E.wav bass-Am.wav bass-GmC.wav \
         melody-call.wav melody-answer.wav dudu.wav ebass.wav crackle.wav rain.flac; do
  cp "$ORIG/audio/$f" "$OUT/audio/$f"
done
# the keys stay 48 kHz stereo 16-bit, as in lofi/ and lofi-forge/
PYTHONUTF8=1 "$EPY" "$OUT/src/make_lofi_epiano.py" "$OUT"
echo "done: $OUT"
