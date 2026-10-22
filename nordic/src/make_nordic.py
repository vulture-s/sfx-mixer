"""Synthesise 'Fjord, 4 a.m.' — a 60 s ambient piece for SFX Mixer: electric piano + synth pad, wind, snow, a drone.
Every sound is generated here from scratch.  usage: python3 make_nordic.py <out-dir>
"""
import json, os, sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 48000
OUT = sys.argv[1]
AUD = os.path.join(OUT, "audio")
os.makedirs(AUD, exist_ok=True)
rng = np.random.default_rng(4)
FPS, DUR = 60, 60


def t_(sec):
    return np.arange(int(sec * SR)) / SR


def flt(x, kind, f, order=2):
    return sosfilt(butter(order, f, btype=kind, fs=SR, output="sos"), x, axis=0)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def save(name, x, peak_db=-1.0):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    x = x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak_db / 20)
    wavfile.write(os.path.join(AUD, name + ".wav"), SR, (x * 32767).astype(np.int16))


def place(buf, x, at):
    a = int(at * SR)
    e = min(len(buf), a + len(x))
    buf[a:e] += x[: e - a]


# ---------------------------------------------------------------- electric piano: soft, felt-like FM, two detuned voices (L/R)
def ep(m, dur, vel):
    out = []
    for det in (-4, 4):
        f = mtof(m) * 2 ** (det / 1200)
        t = t_(dur + 2.5)
        idx = 0.7 * vel * np.exp(-t / 0.4) + 0.08
        ph = 2 * np.pi * f * t
        x = np.sin(ph + idx * np.sin(ph)) + 0.04 * vel * np.sin(2 * np.pi * f * 7.0 * t) * np.exp(-t / 0.05)
        env = np.minimum(1, t / 0.012) * np.exp(-t / 3.5) * np.where(t > dur, np.exp(-(t - dur) / 0.6), 1)
        out.append(x * env * vel)
    return np.stack(out, 1)


def ep_phrase(notes, length):
    y = np.zeros((int(length * SR), 2))
    for at, ms, dur, vel in notes:
        for k, m in enumerate(ms):
            place(y, ep(m, dur, vel * rng.uniform(0.9, 1.0)), at + k * 0.03)
    return flt(y, "lowpass", 5000)


# the motif: D5 · A4 · F4 · E4 (held) — played three times; the third time the E never comes
MOTIF = [(0.0, [74], 1.4, 0.8), (1.25, [69], 1.4, 0.7), (2.5, [65], 1.6, 0.7), (4.0, [64], 3.5, 0.75), (6.6, [62, 69], 3.0, 0.45)]
save("piano-1", ep_phrase(MOTIF, 11.0), -2)
save("piano-2", ep_phrase([(a, [m + 12 for m in ms] if i == 0 else ms, d, v) for i, (a, ms, d, v) in enumerate(MOTIF)], 11.0), -2)
save("piano-3", ep_phrase(MOTIF[:3], 8.0), -2)


# ---------------------------------------------------------------- synth pad: detuned saws, slow attack/release, slow filter breathing
def pad(chord, length=17.0, att=5.0, rel=6.0):
    t = t_(length)
    y = np.zeros((len(t), 2))
    for m in chord:
        f0 = mtof(m)
        for v, det in enumerate((-9, -4, 0, 5, 10)):
            f = f0 * 2 ** (det / 1200)
            ph0 = rng.uniform(0, 2 * np.pi)
            saw = sum(np.sin(2 * np.pi * h * f * t + h * ph0) / h for h in range(1, int(3000 / f) + 1))
            pan = (v / 4)
            y[:, 0] += saw * (1 - pan)
            y[:, 1] += saw * pan
    hold = length - rel
    env = np.minimum(1, t / att) * np.where(t > hold, np.clip(1 - (t - hold) / rel, 0, 1), 1)
    y = flt(y, "lowpass", 1400) * 0.6 + flt(y, "lowpass", 2600) * (0.4 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t)))[:, None]
    return y * (env ** 2)[:, None]


PADS = {
    "pad-Dm9":     [50, 57, 60, 64, 65],   # D A C E F
    "pad-Bbmaj7":  [46, 53, 57, 62, 64],   # Bb F A D E  (#11)
    "pad-Fmaj7":   [48, 53, 57, 64, 67],   # C F A E G   (Fmaj9 over C)
    "pad-Dsus2":   [50, 57, 62, 64, 69],   # D A D E A   (open, unresolved)
}
for k, v in PADS.items():
    save(k, pad(v), -3)


# ---------------------------------------------------------------- drone: D1 + A1, slow beating
t = t_(DUR)
drone = np.sin(2 * np.pi * mtof(26) * t) + 0.5 * np.sin(2 * np.pi * mtof(33) * 1.0015 * t) + 0.25 * np.sin(2 * np.pi * mtof(38) * t)
drone *= np.minimum(1, t / 8) * np.clip((DUR - t) / 4, 0, 1) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.05 * t))
save("drone", drone, -6)


# ---------------------------------------------------------------- footsteps in snow (pool of 4 crunches)
def crunch(seed):
    r = np.random.default_rng(seed)
    t = t_(0.45)
    y = np.zeros(len(t))
    for start, length, dens in ((0.0, 0.12, 900), (0.13, 0.22, 1400)):          # heel, then roll onto the toe
        k = r.poisson(dens * length)
        for p in r.uniform(start, start + length, k):
            L = r.integers(10, 80)
            g = r.standard_normal(L) * np.exp(-np.arange(L) / (L / 3)) * r.uniform(0.2, 1)
            place(y, g, p)
    y = flt(y, "bandpass", [250, 4500])
    return y * np.exp(-t / 0.25)


for i in range(4):
    save(f"step{i + 1}", crunch(30 + i), -3)


# ---------------------------------------------------------------- high sparkle: glassy bells, baked into a long space
y = np.zeros((int(12 * SR), 2))
for at, m, vel in ((0.0, 86, 0.7), (1.7, 81, 0.5), (3.1, 88, 0.6), (5.2, 86, 0.4), (7.0, 93, 0.3)):
    tt = t_(4.0)
    b = (np.sin(2 * np.pi * mtof(m) * tt) + 0.3 * np.sin(2 * np.pi * mtof(m) * 3.01 * tt) * np.exp(-tt / 0.3)) * np.exp(-tt / 1.5) * np.minimum(1, tt / 0.005) * vel
    pan = rng.uniform(0.2, 0.8)
    place(y, np.stack([b * (1 - pan), b * pan], 1), at)
ir_t = t_(5.0)
ir = np.stack([rng.standard_normal(len(ir_t)) for _ in range(2)], 1) * np.exp(-6.9 * ir_t / 5.0)[:, None]
ir = flt(ir, "lowpass", 6000)
ir /= np.sqrt((ir ** 2).sum(0))
wet = np.stack([fftconvolve(y[:, c], ir[:, c])[: len(y)] for c in range(2)], 1)
save("sparkle", y * 0.5 + wet * 1.2, -4)


# ---------------------------------------------------------------- BGM: wind over ice, snow hiss, far-off low rumble
n = int(DUR * SR)
tt = np.arange(n) / SR
gust = 0.55 + 0.25 * np.sin(2 * np.pi * 0.031 * tt) + 0.2 * np.sin(2 * np.pi * 0.083 * tt + 1.0)
gust += 0.35 * np.exp(-((tt - 44) / 4.0) ** 2)                      # one big gust between the second and third motif
noise = rng.standard_normal((n, 2))
wind = np.zeros((n, 2))
for fc, w in ((180, 1.0), (320, 0.8), (560, 0.55), (900, 0.35), (1500, 0.2)):
    band = flt(noise, "bandpass", [fc * 0.8, fc * 1.25])
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(0.02, 0.09) * tt + rng.uniform(0, 6))
    wind += band * (w * mod * gust)[:, None]
whistle = flt(rng.standard_normal(n), "bandpass", [1180, 1260], 3) * np.clip(gust - 0.7, 0, None) * 3
wind[:, 0] += whistle * 0.7
wind[:, 1] += whistle
hiss = flt(rng.standard_normal((n, 2)), "highpass", 5000) * 0.02
rum = flt(np.cumsum(rng.standard_normal((n, 2)), axis=0), "bandpass", [25, 110])
rum /= np.abs(rum).max()
bed = wind + hiss + rum * 0.25
bed *= (np.minimum(1, tt / 3) * np.clip((DUR - tt) / 5, 0, 1))[:, None]
bed = bed / np.abs(bed).max() * 10 ** (-3 / 20)
wavfile.write(os.path.join(AUD, "wind.wav"), SR, (bed * 32767).astype(np.int16))


# ---------------------------------------------------------------- project + cues
def c(id, label, group, src, at_s, dur_s, vol, space="hall", send=0.2, duck=None, **kw):
    d = dict(id=id, at=round(at_s * FPS), src=src, label=label, group=group, vol=vol, dur=round(dur_s * FPS), space=space, send=send,
             start=0, fade=0, duck=duck)
    d.update(kw)
    return d


steps = [round((3.0 + i * 0.78 + (0.05 if i % 2 else 0)) * FPS) for i in range(13)]
pad_order = ["pad-Dm9", "pad-Bbmaj7", "pad-Fmaj7", "pad-Dsus2"]
seed = sum(map(ord, "pad"))                                         # mixer picks pool[(seed + 5i) % len]
pool = [None] * 4
for i, name in enumerate(pad_order):
    pool[(seed + 5 * i) % 4] = name
cues = [
    c("steps", "Footsteps in snow", "field", "pool", 3.0, 10.5, 0.45, "room", 0.05, pool=[f"step{i + 1}" for i in range(4)], hits=steps, soft=[0, 1, 2, 3]),
    c("drone", "Drone D + A", "drone", "drone", 0.0, DUR, 0.5, "dry", 0.0),
    c("pad", "Pad: Dm9 · B♭maj7♯11 · Fmaj9/C · Dsus2", "pad", "pool", 8.0, 50.0, 0.42, "hall", 0.18, pool=pool,
      hits=[round(s * FPS) for s in (8, 23, 38, 50)], soft=[]),
    c("piano-1", "Piano: the motif", "piano", "piano-1", 14.0, 11.0, 0.5, "hall", 0.35),
    c("piano-2", "Piano: again, an octave up", "piano", "piano-2", 28.5, 11.0, 0.45, "hall", 0.35),
    c("piano-3", "Piano: the last note never comes", "piano", "piano-3", 43.0, 8.0, 0.45, "hall", 0.35),
    c("sparkle", "High bells", "sparkle", "sparkle", 50.5, 9.5, 0.3, "hall", 0.4),
]
by = {x["id"]: x for x in cues}
P = by["pad"]
assert [P["pool"][(seed + 5 * i) % 4] for i in range(4)] == pad_order
pfx = dict(delay="1/8d", fb=0.45, dmix=0.28, lpf=4800, drive=2)
project = {
    "title": "Fjord, 4 a.m.", "fps": FPS, "duration": DUR, "video": None,
    "bgm": {"src": "audio/wind.flac", "label": "Wind over ice"},
    "groups": [{"id": "piano", "label": "Piano", "color": "#7a6cff"}, {"id": "pad", "label": "Pad", "color": "#2a56c6"},
               {"id": "drone", "label": "Drone", "color": "#3a3a4a"}, {"id": "field", "label": "Snow", "color": "#8a8a7a"},
               {"id": "sparkle", "label": "Bells", "color": "#2fb59a"}],
    "session": {"global": {"preRoll": 0, "amb": -70, "bgm": -9, "master": -7, "hallRT": 3.5, "hallSend": 1.3, "verbLP": 6000,
                           "bgmFx": {"hpf": 20, "lpf": 7000, "q": 0.7, "drive": 0, "bits": 16, "sweep": 0}},
                "cues": {"piano-1": {"pan": -0.1, "fx": pfx}, "piano-2": {"pan": 0.1, "fx": pfx}, "piano-3": {"fx": pfx},
                         "pad": {"fx": {"lpf": 2600}}, "steps": {"pan": -0.3, "fx": {"lpf": 6000}},
                         "sparkle": {"fx": {"delay": "1/8d", "fb": 0.5, "dmix": 0.3}}}},
}
json.dump(project, open(os.path.join(OUT, "project.json"), "w"), indent=1, ensure_ascii=False)
json.dump(cues, open(os.path.join(OUT, "cues.json"), "w"), indent=1, ensure_ascii=False)
print("ok", len(cues), "cues; pad pool", pool)
