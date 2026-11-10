"""'2 a.m. rain (forge)': the lofi/ demo with its drums and tuned voices re-voiced from the earshot forge bank.

Run by build.sh *after* it has copied lofi/'s parts, cue sheet and project.json into this folder: this script
overwrites the parts the forge can voice, keeps the rest (byte-identical to lofi/), and retitles project.json.
Cue times, groups and the session (mix, inserts) are the original's; only the forged cues' base vol is
level-matched (LEVEL_DB below).
usage: python make_lofi_forge.py <out-dir>   (needs earshot, numpy, scipy)

earshot (MIT, https://github.com/Leonxlnx/earshot) @ 4ac3d2ac2b151e1c23376f9ce7f3047a17050013, bank
forge_v2r6+forge04r1+fit1+pluck1. No fit/* entry is used. Every sound below is bank.render(id, ...) at 48 kHz; the
voicings, strum, swing, note-off releases, tape wow and stereo tremolo are the original's.

| file               | cue               | source                                                                          |
|--------------------|-------------------|---------------------------------------------------------------------------------|
| kick1              | kick              | forge `cut_hit/kick`, pitch 48 Hz (the sub's landing, as the original's 48 Hz)  |
| kick2              | kick              | forge `cut_hit/sub`, pitch 48 Hz                                                |
| hat1 / hat2 / hat3 | hats              | forge `hover_tick/air` / `hover_tick/high` / `pro_hover_tick/soft` (pro_hover_tick/air is flagged by the audit) |
| keys-*, keys-last  | keys, last-chord  | forge `pluck/kalimba_soft`, pitch per chord tone (G3-E5), same voicings         |
| melody-call/answer | melody-*          | forge `pluck/kalimba`, pitch per note (A4-A5, D#5 blue note)                    |
| snare1 / snare2    | snare             | original synthesis, copied from lofi/ (no snare in the bank)                    |
| bass-*             | bass              | original synthesis, copied from lofi/ (A1-C3 is under every tuned voice's range) |
| dudu               | dudu              | original synthesis, copied from lofi/ (a designed pulse pattern, distance baked in) |
| ebass              | ebass             | original synthesis, copied from lofi/ (saw bass under the tuned range)          |
| crackle            | crackle           | original synthesis, copied from lofi/ (no long texture in the bank)             |
| rain.flac          | bgm               | original synthesis, copied from lofi/ (no long ambience in the bank)            |
"""
import json, os, sys
import numpy as np
from scipy.io import wavfile
from earshot.forge import bank

SR = 48000
OUT = sys.argv[1]
AUD = os.path.join(OUT, "audio")
rng = np.random.default_rng(20261022)
BEAT = 1.0
BAR = 4 * BEAT
NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_cache = {}


def name(m):
    return f"{NOTE[m % 12]}{m // 12 - 1}"


def forge(sid, pitch=None):
    """one bank render, float64; a take the audit flags, or a tuned note that missed by more than 50 cents, is refused"""
    key = (sid, pitch)
    if key not in _cache:
        y, meta = bank.render(sid, pitch=pitch, sr=SR)
        p = (meta.get("edits") or {}).get("pitch")
        if p is not None and p.get("ok") is not None:      # cut_hit's pitch is not measured (ok None)
            assert p["ok"], (sid, pitch, p)
        assert meta["checks"]["ok"], (sid, pitch, meta["checks"]["summary"])
        _cache[key] = np.asarray(y, dtype=np.float64)
    return _cache[key]


def mono(x):
    return x.mean(1) if x.ndim == 2 else x


def save(name_, x, peak_db=-1.0):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    x = x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak_db / 20)
    wavfile.write(os.path.join(AUD, name_ + ".wav"), SR, (x * 32767).astype(np.int16))


def wow(n, depth_cents=7.0):
    tt = np.arange(n) / SR
    c = depth_cents * np.sin(2 * np.pi * 0.33 * tt + rng.uniform(0, 6)) + 2.0 * np.sin(2 * np.pi * 5.7 * tt)
    return 2 ** (c / 1200)


# ---------------------------------------------------------------- drums: kicks and hats from the bank
save("kick1", forge("cut_hit/kick", 48))
save("kick2", forge("cut_hit/sub", 48))
for i, sid in enumerate(["hover_tick/air", "hover_tick/high", "pro_hover_tick/soft"]):
    save(f"hat{i + 1}", forge(sid))


# ---------------------------------------------------------------- keys: the original's voicings, each tone a kalimba_soft note
def ep_note(m, dur, vel=1.0, rel=0.35):
    x = mono(forge("pluck/kalimba_soft", name(m)))
    x = x[: int((dur + rel + 0.05) * SR)]
    t = np.arange(len(x)) / SR
    env = np.where(t > dur, np.exp(-(t - dur) / (rel / 4)), 1.0)
    return x * env * vel * (0.85 + 0.3 * (m < 60))


def ep_bar(events, length):
    n = int(length * SR)
    y = np.zeros(n)
    for beat, notes, dur, vel in events:
        for k, m in enumerate(notes):
            s = int((beat * BEAT + k * 0.012) * SR)
            note = ep_note(m, dur * BEAT, vel * rng.uniform(0.88, 1.0))
            e = min(n, s + len(note))
            y[s:e] += note[: e - s]
    pos = np.cumsum(wow(n)) - 1
    y = np.interp(np.clip(pos, 0, n - 1), np.arange(n), y)
    trem = 0.18 * np.sin(2 * np.pi * 4.3 * np.arange(n) / SR)
    return np.stack([y * (1 + trem), y * (1 - trem)], axis=1)


CH = {"F": [57, 64, 67, 72], "E": [56, 62, 67, 72], "Am": [55, 60, 64, 71], "Gm": [58, 62, 65, 69], "C": [58, 64, 69, 74]}
SWING = 4 / 60


def comp(ch):
    return [(0, CH[ch], 2.4, 0.9), (2.75 + SWING, CH[ch][1:], 0.9, 0.55)]


keys_bars = {
    "keys-F": comp("F"), "keys-E": comp("E"), "keys-Am": comp("Am"),
    "keys-GmC": [(0, CH["Gm"], 1.8, 0.9), (2, CH["C"], 1.6, 0.8), (3.75 + SWING, CH["C"][2:], 0.6, 0.45)],
}
for k, ev in keys_bars.items():
    save(k, ep_bar(ev, BAR + 1.6), -3)
save("keys-last", ep_bar([(0, CH["F"] + [76], 3.4, 0.95)], 4.0), -3)


# ---------------------------------------------------------------- melody: the original's call and answer on pluck/kalimba
def pluck(m, dur, vel=1.0):
    x = mono(forge("pluck/kalimba", name(m)))
    x = x[: int((dur + 0.8) * SR)]
    t = np.arange(len(x)) / SR
    return x * np.where(t > dur, np.exp(-(t - dur) / 0.08), 1.0) * vel


def phrase(notes, length):
    n = int(length * SR)
    y = np.zeros(n)
    for beat, m, dur in notes:
        s = int(beat * BEAT * SR)
        p = pluck(m, dur * BEAT, rng.uniform(0.75, 1.0))
        e = min(n, s + len(p))
        y[s:e] += p[: e - s]
    pos = np.cumsum(wow(n, 5)) - 1
    return np.interp(np.clip(pos, 0, n - 1), np.arange(n), y)


S = SWING
call = [(0.5, 74, 0.5), (1, 77, 0.5), (1.5, 79, 1), (2.5, 81, 0.75), (3.5, 79, 0.5),
        (4, 76, 1.5), (6, 72, 0.75), (6.75 + S, 74, 0.25), (7, 69, 1.0)]
answer = [(0.5, 71, 0.5), (1, 72, 0.5), (1.5, 74, 0.5), (2, 76, 1.5),
          (4, 76, 0.5), (4.5, 75, 0.5), (5, 74, 0.5), (5.5, 72, 0.5), (6, 71, 0.75), (7, 69, 1.0)]
save("melody-call", phrase(call, 9.0), -2)
save("melody-answer", phrase(answer, 9.0), -2)

# ---------------------------------------------------------------- level match: cue vol up by the measured loudness gap
# At the same sample peak the forge parts are quieter than the originals (sharper attacks, less sustain). Gap =
# original - forge integrated loudness, ffmpeg ebur128 on each file padded with 1 s of silence (pool cues: the mean
# over their files). Measured on this build; the cue's base vol is scaled by it so the A/B compares sound, not level.
LEVEL_DB = {"kick": 6.4, "hats": 6.7, "keys": 4.6, "last-chord": 3.2, "melody-call": 3.4, "melody-answer": 3.3}
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
print("ok forge:", sorted(f"{s} {p}" for s, p in _cache))
