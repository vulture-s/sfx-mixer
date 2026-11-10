"""'Fjord, 4 a.m. (forge)': the nordic/ demo with its tuned voices re-voiced from the earshot forge bank.

Run by build.sh *after* it has copied nordic/'s parts, cue sheet and project.json into this folder: this script
overwrites the parts the forge can voice, keeps the rest (byte-identical to nordic/), and retitles project.json.
Cue times, groups and the session (mix, inserts) are the original's; only the forged cues' base vol is level-matched
(LEVEL_DB below). usage: python make_nordic_forge.py <out-dir>   (needs earshot, numpy, scipy)

earshot (MIT, https://github.com/Leonxlnx/earshot) @ 4ac3d2ac2b151e1c23376f9ce7f3047a17050013, bank
forge_v2r6+forge04r1+fit1+pluck1. No fit/* entry is used. Every note below is one bank.render(id, pitch=note) at
48 kHz; the phrase timing, velocities, note-off release, low-pass and the bells' baked hall are the original's.

| file          | cue                       | source                                                                 |
|---------------|---------------------------|------------------------------------------------------------------------|
| piano-1/2/3   | piano-1/2/3 (the motif)   | forge `pluck/kalimba_ring`, pitch per note (D5 A4 F4 E4, D4+A4; D6 in piano-2) |
| sparkle       | sparkle (high bells)      | forge `mallet/glock`, pitch D6 A5 E6 D6 A6, into the original 5 s hall |
| pad-*         | pad (4 chords)            | original synthesis, copied from nordic/ (forge has no sustained pad)   |
| drone         | drone                     | original synthesis, copied from nordic/ (forge has no drone)           |
| step1-4       | steps (snow)              | original synthesis, copied from nordic/ (no snow crunch in the bank)   |
| wind.flac     | bgm                       | original synthesis, copied from nordic/ (forge has no long ambience)   |
"""
import json, os, sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
from earshot.forge import bank

SR = 48000
OUT = sys.argv[1]
AUD = os.path.join(OUT, "audio")
rng = np.random.default_rng(4)
NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_cache = {}


def t_(sec):
    return np.arange(int(sec * SR)) / SR


def flt(x, kind, f, order=2):
    return sosfilt(butter(order, f, btype=kind, fs=SR, output="sos"), x, axis=0)


def name(m):
    return f"{NOTE[m % 12]}{m // 12 - 1}"


def forge(sid, m):
    """one bank note at MIDI m, stereo float64 at -1 dBFS; refuses a note that missed by more than 50 cents"""
    if (sid, m) not in _cache:
        y, meta = bank.render(sid, pitch=name(m), sr=SR)
        p = meta["edits"]["pitch"]
        assert p["ok"], (sid, name(m), p)
        y = np.asarray(y, dtype=np.float64)
        _cache[(sid, m)] = y if y.ndim == 2 else np.stack([y, y], 1)
    return _cache[(sid, m)]


def save(name_, x, peak_db=-1.0):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    x = x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak_db / 20)
    wavfile.write(os.path.join(AUD, name_ + ".wav"), SR, (x * 32767).astype(np.int16))


def place(buf, x, at):
    a = int(at * SR)
    e = min(len(buf), a + len(x))
    buf[a:e] += x[: e - a]


# ---------------------------------------------------------------- piano motif -> pluck/kalimba_ring, same notes and timing
def note(m, dur, vel):
    x = forge("pluck/kalimba_ring", m)
    t = np.arange(len(x)) / SR
    env = np.where(t > dur, np.exp(-(t - dur) / 0.6), 1.0)            # the original's note-off release
    return x * (env * vel)[:, None]


def ep_phrase(notes, length):
    y = np.zeros((int(length * SR), 2))
    for at, ms, dur, vel in notes:
        for k, m in enumerate(ms):
            place(y, note(m, dur, vel * rng.uniform(0.9, 1.0)), at + k * 0.03)
    return flt(y, "lowpass", 5000)


MOTIF = [(0.0, [74], 1.4, 0.8), (1.25, [69], 1.4, 0.7), (2.5, [65], 1.6, 0.7), (4.0, [64], 3.5, 0.75), (6.6, [62, 69], 3.0, 0.45)]
save("piano-1", ep_phrase(MOTIF, 11.0), -2)
save("piano-2", ep_phrase([(a, [m + 12 for m in ms] if i == 0 else ms, d, v) for i, (a, ms, d, v) in enumerate(MOTIF)], 11.0), -2)
save("piano-3", ep_phrase(MOTIF[:3], 8.0), -2)

# ---------------------------------------------------------------- high bells -> mallet/glock, same notes, pans and hall
y = np.zeros((int(12 * SR), 2))
for at, m, vel in ((0.0, 86, 0.7), (1.7, 81, 0.5), (3.1, 88, 0.6), (5.2, 86, 0.4), (7.0, 93, 0.3)):
    b = forge("mallet/glock", m).mean(1) * vel
    pan = rng.uniform(0.2, 0.8)
    place(y, np.stack([b * (1 - pan), b * pan], 1), at)
ir_t = t_(5.0)
ir = np.stack([rng.standard_normal(len(ir_t)) for _ in range(2)], 1) * np.exp(-6.9 * ir_t / 5.0)[:, None]
ir = flt(ir, "lowpass", 6000)
ir /= np.sqrt((ir ** 2).sum(0))
wet = np.stack([fftconvolve(y[:, c], ir[:, c])[: len(y)] for c in range(2)], 1)
save("sparkle", y * 0.5 + wet * 1.2, -4)

# ---------------------------------------------------------------- level match: cue vol up by the measured loudness gap
# At the same sample peak the forge parts are quieter than the originals (sharper attacks, less sustain). Gap =
# original - forge integrated loudness, ffmpeg ebur128 on each file padded with 1 s of silence (pool cues: the mean
# over their files). Measured on this build; the cue's base vol is scaled by it so the A/B compares sound, not level.
LEVEL_DB = {"piano-1": 6.2, "piano-2": 6.3, "piano-3": 6.5, "sparkle": 4.6}
cj = os.path.join(OUT, "cues.json")
cues = json.load(open(cj, encoding="utf-8"))
for cue in cues:
    if cue["id"] in LEVEL_DB:
        cue["vol"] = round(cue["vol"] * 10 ** (LEVEL_DB[cue["id"]] / 20), 3)
assert {c["id"] for c in cues} >= set(LEVEL_DB)
json.dump(cues, open(cj, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- project: the original's, retitled
pj = os.path.join(OUT, "project.json")
project = json.load(open(pj, encoding="utf-8"))
assert not project["title"].endswith("(forge)")
project["title"] += " (forge)"
json.dump(project, open(pj, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("ok forge:", sorted({f"{s} {name(m)}" for s, m in _cache}))
