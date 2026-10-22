"""Synthesise the '2 a.m. rain' lofi demo for SFX Mixer. Every sound is generated here from scratch.

60 BPM, 4/4, 8 bars = 32 s, 60 fps  ->  1 beat = 60 frames, 1 bar = 240 frames, 1/16 = 15 frames.
"""
import json, os, sys
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR = 48000
OUT = sys.argv[1]
AUD = os.path.join(OUT, "audio")
os.makedirs(AUD, exist_ok=True)
rng = np.random.default_rng(20261022)

BEAT = 1.0          # seconds (60 BPM)
BAR = 4 * BEAT
FPS = 60


def t_(sec):
    return np.arange(int(sec * SR)) / SR


def flt(x, kind, f, order=2):
    sos = butter(order, f, btype=kind, fs=SR, output="sos")
    return sosfilt(sos, x, axis=0)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def save(name, x, peak_db=-1.0):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    x = x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak_db / 20)
    wavfile.write(os.path.join(AUD, name + ".wav"), SR, (x * 32767).astype(np.int16))


def wow(n, depth_cents=7.0):
    """slow tape wow + a little flutter, returned as a playback-rate curve"""
    tt = np.arange(n) / SR
    c = depth_cents * np.sin(2 * np.pi * 0.33 * tt + rng.uniform(0, 6)) + 2.0 * np.sin(2 * np.pi * 5.7 * tt)
    return 2 ** (c / 1200)


# ---------------------------------------------------------------- drums
def kick(dec=0.32, top=95, seed=0):
    t = t_(0.7)
    f = 48 + top * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)
    click = flt(np.random.default_rng(seed).standard_normal(len(t)), "lowpass", 2500) * np.exp(-t / 0.003) * 0.4
    x = np.tanh(1.8 * (body + click))
    return flt(x, "lowpass", 3000)


def snare(tone=185, nd=0.15, seed=0):
    t = t_(0.5)
    r = np.random.default_rng(seed)
    body = np.sin(2 * np.pi * tone * t) * np.exp(-t / 0.07) * 0.55
    nz = flt(r.standard_normal(len(t)), "bandpass", [1100, 6500]) * np.exp(-t / nd)
    x = np.tanh(1.4 * (body + nz))
    return flt(x, "lowpass", 7000)


def hat(dec=0.03, seed=0):
    t = t_(0.25)
    r = np.random.default_rng(seed)
    metal = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)) / 6
    x = 0.6 * metal + r.standard_normal(len(t))
    x = flt(x, "highpass", 7000, 4) * np.exp(-t / dec)
    return flt(x, "lowpass", 11000)


for i, (d, top) in enumerate([(0.32, 95), (0.28, 105)]):
    save(f"kick{i + 1}", kick(d, top, seed=i))
for i, (tone, nd) in enumerate([(185, 0.15), (198, 0.12)]):
    save(f"snare{i + 1}", snare(tone, nd, seed=10 + i))
for i, d in enumerate([0.028, 0.035, 0.022]):
    save(f"hat{i + 1}", hat(d, seed=20 + i))


# ---------------------------------------------------------------- Rhodes-ish electric piano (2-op FM + tine)
def ep_note(m, dur, vel=1.0, rel=0.35):
    f = mtof(m)
    t = t_(dur + rel + 0.05)
    idx = 1.6 * np.exp(-t / 0.22) * vel + 0.25
    ph = 2 * np.pi * f * t
    x = np.sin(ph + idx * np.sin(ph))
    x += 0.12 * vel * np.sin(2 * np.pi * f * 14.1 * t) * np.exp(-t / 0.025)          # tine
    env = np.minimum(1, t / 0.004) * np.exp(-t / 2.2)
    env *= np.where(t > dur, np.exp(-(t - dur) / (rel / 4)), 1.0)
    return x * env * vel * (0.85 + 0.3 * (m < 60))


def ep_bar(events, length):
    """events: (beat, [midi], dur_beats, vel). strum 12 ms low->high. stereo tremolo, wow."""
    n = int(length * SR)
    y = np.zeros(n)
    for beat, notes, dur, vel in events:
        for k, m in enumerate(notes):
            s = int((beat * BEAT + k * 0.012) * SR)
            v = vel * rng.uniform(0.88, 1.0)
            note = ep_note(m, dur * BEAT, v)
            e = min(n, s + len(note))
            y[s:e] += note[: e - s]
    # tape wow: resample along a wobbling read head
    pos = np.cumsum(wow(n)) - 1
    y = np.interp(np.clip(pos, 0, n - 1), np.arange(n), y)
    tt = np.arange(n) / SR
    trem = 0.18 * np.sin(2 * np.pi * 4.3 * tt)
    return np.stack([y * (1 + trem), y * (1 - trem)], axis=1)


CH = {
    "F":   [57, 64, 67, 72],        # Fmaj9 (A E G C)
    "E":   [56, 62, 67, 72],        # E7#9b13 (G# D G C)
    "Am":  [55, 60, 64, 71],        # Am9 (G C E B)
    "Gm":  [58, 62, 65, 69],        # Gm9 (Bb D F A)
    "C":   [58, 64, 69, 74],        # C13 (Bb E A D)
}
SWING = 4 / 60                       # swung 16th: +4 frames


def comp(ch):
    return [(0, CH[ch], 2.4, 0.9), (2.75 + SWING, CH[ch][1:], 0.9, 0.55)]


keys_bars = {
    "keys-F": comp("F"),
    "keys-E": comp("E"),
    "keys-Am": comp("Am"),
    "keys-GmC": [(0, CH["Gm"], 1.8, 0.9), (2, CH["C"], 1.6, 0.8), (3.75 + SWING, CH["C"][2:], 0.6, 0.45)],
}
for name, ev in keys_bars.items():
    save(name, ep_bar(ev, BAR + 1.6), -3)
save("keys-last", ep_bar([(0, CH["F"] + [76], 3.4, 0.95)], 4.0), -3)


# ---------------------------------------------------------------- bass
def bass_bar(notes, length=BAR + 0.4):
    n = int(length * SR)
    y = np.zeros(n)
    for beat, m, dur in notes:
        f = mtof(m)
        t = t_(dur * BEAT + 0.12)
        x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
        env = np.minimum(1, t / 0.012) * np.exp(-t / 1.6) * np.where(t > dur * BEAT, np.exp(-(t - dur * BEAT) / 0.03), 1)
        s = int(beat * BEAT * SR)
        e = min(n, s + len(t))
        y[s:e] += (np.tanh(1.5 * x) * env)[: e - s]
    return flt(y, "lowpass", 450)


bass = {
    "bass-F":   [(0, 41, 2.2), (2.5, 48, 0.8), (3.5, 41, 0.4)],          # F  ... -> E
    "bass-E":   [(0, 40, 2.2), (2.5, 47, 0.8), (3.5 + SWING, 44, 0.4)],  # E  ... G# -> A
    "bass-Am":  [(0, 33, 2.2), (2.5, 40, 0.8), (3.5 + SWING, 32, 0.4)],  # A  ... G# -> G
    "bass-GmC": [(0, 43, 1.8), (2, 36, 1.4), (3.5 + SWING, 40, 0.4)],    # G  C ... E -> F
}
for k, v in bass.items():
    save(k, bass_bar(v))


# ---------------------------------------------------------------- melody: soft kalimba-ish pluck, A minor pentatonic + blue note
def pluck(m, dur, vel=1.0):
    f = mtof(m)
    t = t_(dur + 0.8)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.12) + 0.15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.04)
    env = np.minimum(1, t / 0.003) * np.exp(-t / 0.9)
    env *= np.where(t > dur, np.exp(-(t - dur) / 0.08), 1.0)
    return x * env * vel


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
call = [(0.5, 74, 0.5), (1, 77, 0.5), (1.5 + 0, 79, 1), (2.5, 81, 0.75), (3.5, 79, 0.5),     # over Gm9 -> C13
        (4, 76, 1.5), (6, 72, 0.75), (6.75 + S, 74, 0.25), (7, 69, 1.0)]                      # over Fmaj9
answer = [(0.5, 71, 0.5), (1, 72, 0.5), (1.5, 74, 0.5), (2, 76, 1.5),                          # over E7#9b13
          (4, 76, 0.5), (4.5, 75, 0.5), (5, 74, 0.5), (5.5, 72, 0.5), (6, 71, 0.75), (7, 69, 1.0)]  # Am9, Eb = blue note
save("melody-call", phrase(call, 9.0), -2)
save("melody-answer", phrase(answer, 9.0), -2)


# ---------------------------------------------------------------- vinyl crackle (32 s, its own track)
def crackle(sec=32.0):
    n = int(sec * SR)
    y = np.zeros((n, 2))
    hiss = flt(rng.standard_normal((n, 2)), "bandpass", [800, 5000]) * 0.03
    y += hiss
    for rate, amp in ((14, 0.15), (0.6, 0.7)):
        k = rng.poisson(rate * sec)
        pos = rng.integers(0, n - 200, k)
        for p in pos:
            L = rng.integers(8, 60)
            c = rng.standard_normal(L) * np.exp(-np.arange(L) / (L / 4)) * amp * rng.uniform(0.3, 1)
            ch = rng.integers(0, 2)
            y[p:p + L, ch] += c
            y[p:p + L, 1 - ch] += c * 0.5
    y = flt(y, "highpass", 300)
    tt = np.arange(n) / SR
    y[:, 0] += 0.01 * np.sin(2 * np.pi * 0.555 * tt) * np.sin(2 * np.pi * 38 * tt)                # 33⅓ rpm thump
    y[:, 1] += 0.01 * np.sin(2 * np.pi * 0.555 * tt) * np.sin(2 * np.pi * 38 * tt)
    return y


save("crackle", crackle(), -6)


# ---------------------------------------------------------------- BGM: rain on a window, distant traffic, a low drone (32 s)
def rain_bed(sec=32.0):
    n = int(sec * SR)
    tt = np.arange(n) / SR
    wash = flt(rng.standard_normal((n, 2)), "bandpass", [400, 7000], 2)
    wash *= (0.85 + 0.15 * np.sin(2 * np.pi * 0.07 * tt + np.array([[0, 1.3]]).T).T)
    y = wash * 0.25
    drops = np.zeros((n, 2))
    k = rng.poisson(45 * sec)
    for p in rng.integers(0, n - 2000, k):
        f = rng.uniform(1800, 5200)
        L = int(rng.uniform(0.004, 0.012) * SR)
        tl = np.arange(L) / SR
        d = np.sin(2 * np.pi * f * tl) * np.exp(-tl / (L / SR / 3)) * rng.uniform(0.05, 0.5)
        pan = rng.uniform(0, 1)
        drops[p:p + L, 0] += d * (1 - pan)
        drops[p:p + L, 1] += d * pan
    for p in rng.integers(0, n - 20000, rng.poisson(0.6 * sec)):          # heavier drips off the sill
        L = int(0.06 * SR)
        tl = np.arange(L) / SR
        f = rng.uniform(700, 1100) * (1 + 2.0 * tl / 0.06)
        d = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tl / 0.015) * 0.6
        pan = rng.uniform(0.2, 0.8)
        drops[p:p + L, 0] += d * (1 - pan)
        drops[p:p + L, 1] += d * pan
    y += drops * 0.5
    brown = np.cumsum(rng.standard_normal((n, 2)), axis=0)
    brown = flt(brown - np.mean(brown, axis=0), "highpass", 25)
    rumble = flt(brown, "lowpass", 160)
    rumble = rumble / np.max(np.abs(rumble)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * tt))[:, None]
    y += rumble * 0.35
    # one car passing far away during the break (20-27 s)
    car = flt(rng.standard_normal(n), "bandpass", [250, 900])
    sw = np.exp(-((tt - 23.5) / 2.2) ** 2)
    pan = np.clip((tt - 21) / 5, 0, 1)
    y[:, 0] += car * sw * 0.3 * (1 - pan)
    y[:, 1] += car * sw * 0.3 * pan
    drone = 0.05 * (np.sin(2 * np.pi * 55 * tt) + 0.6 * np.sin(2 * np.pi * 82.6 * tt)) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.11 * tt))
    y += drone[:, None]
    fade = np.minimum(1, tt / 1.5)[:, None]
    return y * fade


bed = rain_bed()
bed = bed / np.max(np.abs(bed)) * 10 ** (-3 / 20)
wavfile.write(os.path.join(AUD, "rain.wav"), SR, (bed * 32767).astype(np.int16))
print("ok")
