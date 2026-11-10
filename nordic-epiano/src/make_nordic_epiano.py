"""'Fjord, 4 a.m. (forge epiano)': nordic-forge/ with its piano motif played on a physical electric piano.

Run by build.sh *after* it has copied nordic-forge/'s parts, cue sheet and project.json into this folder: this script
overwrites the three piano parts, keeps the rest (byte-identical to nordic-forge/), and retitles project.json.
Cue times, groups and the session (mix, inserts) are nordic-forge's; only the piano cues' base vol is level-matched
(LEVEL_DB below). usage: python make_nordic_epiano.py <out-dir>   (needs earshot, numpy, scipy)

The electric piano is epiano/epiano.py, preset D (Mark I voicing: the 0.7-0.8 notes bark a little, the soft dyad stays
round; a 0.9 Hz tine/tonebar beat; a Suitcase-style amp with a 3.2 Hz panning tremolo, depth 0.28). It runs on
earshot's forge dsp (MIT, https://github.com/Leonxlnx/earshot @ 4ac3d2ac2b151e1c23376f9ce7f3047a17050013) and
rewrites the tine of its pluck recipe; no bank entry and no recorded audio is used.
The notes, timing, velocities and the velocity-jitter draw (default_rng(4), uniform 0.9-1.0 per note, in the same
order as nordic/src/make_nordic.py) are the original's; the 30 ms dyad spread and the 0.6 s key-off release are
epiano.phrase's, which match it. The original's 5 kHz phrase low-pass is not added: preset D's speaker already rolls
off at 5.5 kHz and the cue's insert low-passes at 4.8 kHz. piano-1 is the take auditioned as "D".

| file          | cue                       | source                                                                  |
|---------------|---------------------------|-------------------------------------------------------------------------|
| piano-1/2/3   | piano-1/2/3 (the motif)   | epiano/epiano.py preset D, per note (D5 A4 F4 E4, D4+A4; D6 in piano-2) |
| sparkle       | sparkle (high bells)      | copied from nordic-forge/ (forge `mallet/glock` into the original hall) |
| pad-*         | pad (4 chords)            | copied from nordic-forge/ (= nordic/'s original synthesis)              |
| drone         | drone                     | copied from nordic-forge/ (= nordic/'s original synthesis)              |
| step1-4       | steps (snow)              | copied from nordic-forge/ (= nordic/'s original synthesis)              |
| wind.flac     | bgm                       | copied from nordic-forge/ (= nordic/'s original synthesis)              |
"""
import json, os, sys
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "epiano"))
import epiano
from earshot.forge import dsp

SR = 48000
assert dsp.SR == SR
OUT = sys.argv[1]
AUD = os.path.join(OUT, "audio")
rng = np.random.default_rng(4)          # the original's velocity jitter, drawn in the original's order
P = epiano.PRESETS["D"]


def save(name_, x, peak_db=-1.0):
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak_db / 20)
    wavfile.write(os.path.join(AUD, name_ + ".wav"), SR, (x * 32767).astype(np.int16))


MOTIF = [(0.0, [74], 1.4, 0.8), (1.25, [69], 1.4, 0.7), (2.5, [65], 1.6, 0.7), (4.0, [64], 3.5, 0.75), (6.6, [62, 69], 3.0, 0.45)]
# noise/room/beat draws: rng(168) is the audition's seed for D (100 + ord("D")); the other two take the next seeds
save("piano-1", epiano.phrase(P, MOTIF, 11.0, dsp.rng(168), jitter=rng), -2)
save("piano-2", epiano.phrase(P, [(a, [m + 12 for m in ms] if i == 0 else ms, d, v) for i, (a, ms, d, v) in enumerate(MOTIF)],
                              11.0, dsp.rng(169), jitter=rng), -2)
save("piano-3", epiano.phrase(P, MOTIF[:3], 8.0, dsp.rng(170), jitter=rng), -2)

# ---------------------------------------------------------------- level match against nordic-forge's kalimba piano
# Gap = nordic-forge piano-N minus this piano-N integrated loudness, ffmpeg ebur128 on the final 24 kHz files, each
# padded with 1 s of silence (as the forge versions measured). The cue's base vol (nordic-forge's) is scaled by it.
# Negative: at the same -2 dBFS peak the pickup's sustained tone is ~5.5 dB louder than the kalimba's (forge -15.4..-15.8
# LUFS, epiano -9.6..-10.4), i.e. back to about the original FM piano's level (nordic-forge had raised it 6.2-6.5 dB).
LEVEL_DB = {"piano-1": -5.4, "piano-2": -5.4, "piano-3": -5.8}
cj = os.path.join(OUT, "cues.json")
cues = json.load(open(cj, encoding="utf-8"))
for cue in cues:
    if cue["id"] in LEVEL_DB:
        cue["vol"] = round(cue["vol"] * 10 ** (LEVEL_DB[cue["id"]] / 20), 3)
assert {c["id"] for c in cues} >= set(LEVEL_DB)
json.dump(cues, open(cj, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- project: nordic-forge's, retitled
pj = os.path.join(OUT, "project.json")
project = json.load(open(pj, encoding="utf-8"))
assert project["title"].endswith(" (forge)"), project["title"]
project["title"] = project["title"][: -len(" (forge)")] + " (forge epiano)"
json.dump(project, open(pj, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("ok epiano D:", project["title"])
