"""electronic 'DUDUDUDU' bass: saw + sub, 16th-note octave bounce, per-note filter envelope, travels near -> far."""
import os, sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
SR = 48000; OUT = sys.argv[1]; rng = np.random.default_rng(11)
STEP = 0.25; SW = 4 / 60                                  # 1/16 at 60 BPM, swung by 4 frames
LEN = 8.0 + 2.0
n = int(LEN * SR)
bright = np.zeros(n); dark = np.zeros(n)
lp = lambda x, f: sosfilt(butter(2, f, 'lowpass', fs=SR, output='sos'), x)
for k in range(32):
    root = 40 if k < 16 else 45                            # E (bar over E7) then A (bar over Am9)
    m = root + (12 if k % 2 else 0)                        # octave bounce: DU-du-DU-du
    f = 440 * 2 ** ((m - 69) / 12)
    t0 = k * STEP + (SW if k % 2 else 0)
    d = STEP * 0.7
    t = np.arange(int((d + 0.05) * SR)) / SR
    saw = sum(np.sin(2 * np.pi * h * f * t) / h for h in range(1, int(12000 / f)))
    x = 0.8 * saw + 0.6 * np.sin(2 * np.pi * f / (2 if m > root else 1) * t)   # sub one octave under the high notes
    amp = np.minimum(1, t / 0.003) * np.where(t > d, np.exp(-(t - d) / 0.01), 1) * (1.0 if k % 4 == 0 else 0.8)
    fenv = np.exp(-t / 0.07)                               # filter envelope: opens on the attack, closes fast
    a = int(t0 * SR); e = min(n, a + len(t))
    bright[a:e] += (x * amp * fenv)[: e - a]
    dark[a:e] += (x * amp * (1 - fenv))[: e - a]
y0 = lp(bright, 3200) + lp(dark, 380)
y0 = np.tanh(1.6 * y0 / np.abs(y0).max())
tt = np.arange(n) / SR
prog = np.clip(tt / 8.0, 0, 1)
gain = 10 ** (-18 * prog / 20)
near_far = lp(y0, 9000) * (1 - prog) + lp(y0, 900) * prog
ir_t = np.arange(int(1.6 * SR)) / SR
ir = np.stack([rng.standard_normal(len(ir_t)) for _ in range(2)], 1) * np.exp(-6.9 * ir_t / 1.6)[:, None]
ir = sosfilt(butter(2, 3000, 'lowpass', fs=SR, output='sos'), ir, axis=0); ir /= np.sqrt((ir ** 2).sum(0))
wet = np.stack([fftconvolve(near_far, ir[:, c])[:n] for c in range(2)], 1)
wmix = (0.05 + 0.55 * prog)[:, None]
y = (near_far * gain)[:, None] * (1 - wmix) + wet * gain[:, None] * wmix * 1.5
y /= np.abs(y).max(); y *= 10 ** (-1 / 20)
wavfile.write(os.path.join(OUT, "audio", "ebass.wav"), SR, (y * 32767).astype(np.int16))
print("ok ebass", LEN, "s")
