"""'2 a.m. rain (forge epiano)': lofi-forge/ with its keys played on a physical electric piano.

Run by build.sh *after* it has copied lofi-forge/'s parts, cue sheet and project.json into this folder: this script
overwrites the five keys parts, keeps the rest (byte-identical to lofi-forge/, so the melody stays the forge kalimba),
and retitles project.json. Cue times, groups and the session (mix, inserts) are lofi-forge's; only the keys cues' base
vol is level-matched (LEVEL_DB below). usage: python make_lofi_epiano.py <out-dir>   (needs earshot, numpy, scipy)

The electric piano is epiano/epiano.py, preset D, running on earshot's forge dsp (MIT,
https://github.com/Leonxlnx/earshot @ 4ac3d2ac2b151e1c23376f9ce7f3047a17050013); no bank entry, no recorded audio.
From lofi/src/make_lofi.py, unchanged: the voicings, the 12 ms low-to-high strum, the swing, the velocities and their
jitter (default_rng(20261022), uniform 0.88-1.0 per note, then one wow phase per bar, in the original's order), the
register weighting (x1.15 below C4, x0.85 from C4 up), the key-off release (tau 0.35/4 s), the tape wow (7 cents at
0.33 Hz + 2 cents at 5.7 Hz, a wobbling read head) and the 4.3 Hz stereo tremolo (+-0.18, L against R).
Changed from preset D, both for the chords:
  - amp_drive 1.0 -> 0.5. Each tine has its own pickup, so the pickup's bark never mixes two notes; the one shared
    nonlinearity is the amp, and four strummed tones through it intermodulate. Measured as the cross-term energy
    nl(sum) - sum(nl(each)) relative to nl(sum) (imd_db below, printed on every build): preset D's own drive gives
    -9.5..-11.0 dB on these chords, against -13.8 dB on the nordic motif as approved (the same D, one or two notes
    at a time). 0.5 puts every bar at or below that reference. Lowering the velocity does not help (-9.0..-10.8 dB
    at x0.65): the amp sees the summed signal normalised to its peak, so only the drive sets the cross terms.
  - trem_depth 0.28 -> 0: the original's own 4.3 Hz tremolo (above) plays the Suitcase's role; two tremolos at
    3.2 and 4.3 Hz would beat against each other.

| file               | cue               | source                                                                  |
|--------------------|-------------------|-------------------------------------------------------------------------|
| keys-*, keys-last  | keys, last-chord  | epiano/epiano.py preset D (amp_drive 0.5, no own tremolo), per chord tone (G#3-E5), same voicings |
| melody-call/answer | melody-*          | copied from lofi-forge/ (forge `pluck/kalimba`)                         |
| kick1 / kick2      | kick              | copied from lofi-forge/ (forge `cut_hit/kick` / `cut_hit/sub`)          |
| hat1 / hat2 / hat3 | hats              | copied from lofi-forge/ (forge `hover_tick/air` / `hover_tick/high` / `pro_hover_tick/soft`) |
| snare1 / snare2    | snare             | copied from lofi-forge/ (= lofi/'s original synthesis)                  |
| bass-*             | bass              | copied from lofi-forge/ (= lofi/'s original synthesis)                  |
| dudu               | dudu              | copied from lofi-forge/ (= lofi/'s original synthesis)                  |
| ebass              | ebass             | copied from lofi-forge/ (= lofi/'s original synthesis)                  |
| crackle            | crackle           | copied from lofi-forge/ (= lofi/'s original synthesis)                  |
| rain.flac          | bgm               | copied from lofi-forge/ (= lofi/'s original synthesis)                  |
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
rng = np.random.default_rng(20261022)   # the original's jitter + wow draws, in the original's order
BEAT = 1.0
BAR = 4 * BEAT
REL = 0.35
P = {**epiano.PRESETS["D"], "amp_drive": 0.5, "trem_depth": 0.0, "damp_tau": REL / 4}
REF_IMD_DB = -13.8                        # nordic-epiano piano-1, preset D as approved (measured the same way)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def save(name_, x, peak_db=-1.0):
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak_db / 20)
    wavfile.write(os.path.join(AUD, name_ + ".wav"), SR, (x * 32767).astype(np.int16))


def wow(n, depth_cents=7.0):
    tt = np.arange(n) / SR
    c = depth_cents * np.sin(2 * np.pi * 0.33 * tt + rng.uniform(0, 6)) + 2.0 * np.sin(2 * np.pi * 5.7 * tt)
    return 2 ** (c / 1200)


def amp_nl(y, drive):
    """the amp stage of epiano.chain (asymmetric tanh), on an already peak-normalised signal"""
    k, b = 1 + drive * 2.0, 0.12
    return (np.tanh(k * (y + b)) - np.tanh(k * b)) / k


def imd_db(parts, drive):
    """amp cross-term energy relative to the amp output: nl(sum) - sum(nl(each)), all at the chain's gain"""
    s = sum(parts)
    g = 1 / (np.abs(s).max() + 1e-12)
    full = amp_nl(g * s, drive)
    res = full - sum(amp_nl(g * x, drive) for x in parts)
    return 10 * np.log10((res ** 2).sum() / (full ** 2).sum() + 1e-30)


def ep_bar(events, length, r):
    """events: (beat, [midi], dur_beats, vel). One pickup voice per tone, strum 12 ms low->high, through the amp/speaker
    chain once (the tones share it), then the original's tape wow and stereo tremolo."""
    n = int(length * SR)
    parts = []
    for beat, notes, dur, vel in events:
        for k, m in enumerate(notes):
            v = vel * rng.uniform(0.88, 1.0)
            x = epiano.voice(P, mtof(m), v, dur * BEAT, r, tail=REL + 0.05) * (0.85 + 0.3 * (m < 60))
            y1 = np.zeros(n)
            dsp.place(y1, x, beat * BEAT + k * 0.012)
            parts.append(y1)
    imd = imd_db(parts, P["amp_drive"])
    x = epiano.chain(P, sum(parts), r)[:n]
    pos = np.clip(np.cumsum(wow(n)) - 1, 0, n - 1)
    x = np.stack([np.interp(pos, np.arange(n), x[:, c]) for c in range(2)], 1)
    trem = 0.18 * np.sin(2 * np.pi * 4.3 * np.arange(n) / SR)
    x[:, 0] *= 1 + trem
    x[:, 1] *= 1 - trem
    return dsp.fade(x, 0.0005, 0.05), imd


CH = {"F": [57, 64, 67, 72], "E": [56, 62, 67, 72], "Am": [55, 60, 64, 71], "Gm": [58, 62, 65, 69], "C": [58, 64, 69, 74]}
SWING = 4 / 60


def comp(ch):
    return [(0, CH[ch], 2.4, 0.9), (2.75 + SWING, CH[ch][1:], 0.9, 0.55)]


keys_bars = {
    "keys-F": comp("F"), "keys-E": comp("E"), "keys-Am": comp("Am"),
    "keys-GmC": [(0, CH["Gm"], 1.8, 0.9), (2, CH["C"], 1.6, 0.8), (3.75 + SWING, CH["C"][2:], 0.6, 0.45)],
}
report = {}
for i, (k, ev) in enumerate(keys_bars.items()):
    x, report[k] = ep_bar(ev, BAR + 1.6, dsp.rng(300 + i))
    save(k, x, -3)
x, report["keys-last"] = ep_bar([(0, CH["F"] + [76], 3.4, 0.95)], 4.0, dsp.rng(304))
save("keys-last", x, -3)
print("amp IMD (dB, reference %.1f):" % REF_IMD_DB, {k: round(float(v), 1) for k, v in report.items()})
assert max(report.values()) <= REF_IMD_DB + 0.5, report

# ---------------------------------------------------------------- level match against lofi-forge's kalimba keys
# Gap = lofi-forge minus this build's integrated loudness, ffmpeg ebur128 on each file padded with 1 s of silence (the
# keys pool cue: the mean over its four files). The cue's base vol (lofi-forge's) is scaled by it.
# Negative: at the same -3 dBFS peak the pickup's sustained chords are ~5.5 dB louder than the kalimba_soft ones (forge
# -19.3..-20.6 LUFS, epiano -13.9..-15.0), i.e. back near the original FM keys (lofi-forge had raised them 3.2-4.6 dB).
LEVEL_DB = {"keys": -5.6, "last-chord": -5.3}
cj = os.path.join(OUT, "cues.json")
cues = json.load(open(cj, encoding="utf-8"))
for cue in cues:
    if cue["id"] in LEVEL_DB:
        cue["vol"] = round(cue["vol"] * 10 ** (LEVEL_DB[cue["id"]] / 20), 3)
assert {c["id"] for c in cues} >= set(LEVEL_DB)
json.dump(cues, open(cj, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- project: lofi-forge's, retitled
pj = os.path.join(OUT, "project.json")
project = json.load(open(pj, encoding="utf-8"))
assert project["title"].endswith(" (forge)"), project["title"]
project["title"] = project["title"][: -len(" (forge)")] + " (forge epiano)"
json.dump(project, open(pj, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("ok epiano D (chords):", project["title"])
