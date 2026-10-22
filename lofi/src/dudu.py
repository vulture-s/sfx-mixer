"""bright 'du du du dud / du du dud' pulse that travels from near to far (distance baked in)."""
import os, sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
SR = 48000; OUT = sys.argv[1]; rng = np.random.default_rng(7)
STEP = 0.25; SW = 4 / 60                                   # 1/16 at 60 BPM, swung by 4 frames
LEN = 8 * 4 * STEP + 2.5                                  # 2 bars + tail
n = int(LEN * SR); dry = np.zeros(n)
f0 = 440 * 2 ** ((88 - 69) / 12)                          # E6
pat = [(0, 1), (1, 1), (2, 1), (3, 2), (5, 1), (6, 2)]    # du du du dud . du dud  (8 steps)
hits = [(g * 8 + s, L) for g in range(4) for s, L in pat]
for k, (s, L) in enumerate(hits):
    t0 = s * STEP + (SW if s % 2 else 0)
    d = L * STEP * 0.8
    t = np.arange(int((d + 0.25) * SR)) / SR
    ph = (f0 * (2 if k % 6 == 5 else 1) * t) % 1.0          # last 'dud' of each group jumps an octave
    x = np.where(ph < 0.25, 1.0, -0.33)                    # 25 % pulse = bright
    x = x - x.mean()
    env = np.minimum(1, t / 0.002) * np.exp(-t / (0.09 * L)) * np.where(t > d, np.exp(-(t - d) / 0.02), 1)
    a = int(t0 * SR); e = min(n, a + len(t)); dry[a:e] += (x * env * rng.uniform(0.85, 1))[: e - a]
tt = np.arange(n) / SR
prog = np.clip(tt / (8 * STEP * 4), 0, 1)                  # 0 = near, 1 = far
# distance: level, air absorption (moving low-pass), more reverb
gain = 10 ** (-18 * prog / 20)
cut_lo = sosfilt(butter(2, 2000, 'lowpass', fs=SR, output='sos'), dry)
cut_hi = sosfilt(butter(2, 12000, 'lowpass', fs=SR, output='sos'), dry)
near_far = cut_hi * (1 - prog) + cut_lo * prog
ir_t = np.arange(int(1.8 * SR)) / SR
ir = np.stack([rng.standard_normal(len(ir_t)), rng.standard_normal(len(ir_t))], 1) * np.exp(-6.9 * ir_t / 1.8)[:, None]
ir = sosfilt(butter(2, 5000, 'lowpass', fs=SR, output='sos'), ir, axis=0); ir /= np.sqrt((ir ** 2).sum(0))
wet = np.stack([fftconvolve(near_far, ir[:, c])[:n] for c in range(2)], 1)
wmix = (0.1 + 0.6 * prog)[:, None]
direct = (near_far * gain)[:, None] * np.array([[1.0, 1.0]])
y = direct * (1 - wmix) + wet * gain[:, None] * wmix * 1.5
y /= np.abs(y).max(); y *= 10 ** (-1 / 20)
wavfile.write(os.path.join(OUT, "audio", "dudu.wav"), SR, (y * 32767).astype(np.int16))
print("ok", len(hits), "hits", round(LEN, 2), "s")
