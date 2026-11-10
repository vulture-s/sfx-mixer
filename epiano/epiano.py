"""A Rhodes-style electric piano (tine + tonebar + electromagnetic pickup), built from physics on earshot.forge.dsp.

Shared by nordic-epiano/ and lofi-epiano/ (their make_*_epiano.py import it from here). Preset D is the one used.
Based on earshot (MIT, Copyright (c) 2026 Leon Lin, https://github.com/Leonxlnx/earshot) pinned at commit
4ac3d2ac2b151e1c23376f9ce7f3047a17050013: it uses that commit's forge dsp primitives (earshot.forge.dsp: butter,
peq, stereo, room, mic, place, fade, rng) and note-name parser, and rewrites the tine model of its pluck recipe
(earshot/forge/recipes/pluck.py, the kalimba: a clamped-free steel tine) into an electric piano. In short:
  1. hammer, not thumb: a half-sine felt contact whose time shrinks with impact speed (Hertzian felt), so harder =
     shorter = brighter AND louder;
  2. tine + tonebar: an asymmetric tuning fork, two coupled normal modes a fraction of a Hz apart (slow beat, long
     tonebar sustain) plus the tine's 2nd bending mode as the attack ping; no wooden box (a Rhodes is heard through
     its pickup);
  3. electromagnetic pickup: emf = d/dt of a bell-shaped flux of the tine-tip offset; off-axis voicing gives even
     harmonics and, on hard notes, the folded "bark"; then the coil/cable resonance, an optional Suitcase-style amp,
     speaker and panning tremolo.
Each tine has its own pickup, so the pickup nonlinearity never mixes two notes; only the shared amp stage
(amp_drive) can intermodulate a chord. Every sample is computed: no recorded audio, no third-party samples.

The detail, from the pluck recipe's tine with three changes:

    import epiano
    from earshot.forge import dsp
    x = epiano.render({**epiano.PRESETS['B'], 'f0': 'E4', 'vel': 0.8, 'dur': 2.0}, dsp.rng(1))   # 48 kHz stereo

1. Excitation: a felt/neoprene hammer, not a thumb slipping off.
   The hammer stays on the tine for a contact time T (0.5-3 ms), modelled as a half-sine force pulse. Its spectrum is
   ~ |cos(pi f T) / (1 - (2 f T)^2)|: flat to ~1/(2T), first null at 1.5/T, so a short contact excites the high tine
   modes (bright) and a long one does not (dark). Hertzian contact of a stiffening felt: T shrinks with impact speed,
   T(v) = hammer_ms * v^-hard_exp (felt with exponent p ~ 2.5-3.5 gives an exponent of 1/5 .. 1/3), so a harder
   blow is shorter AND larger: the brightness/loudness coupling of a real Rhodes.
   The force pulse is convolved with the modal impulse response of the tine (displacement, ~ sin(wt) e^(-t/tau) / w).
2. Resonator: the tine (a clamped-free steel cantilever, like the kalimba tine) PLUS the tonebar, its heavy brass
   partner bolted to the same block: an asymmetric tuning fork. The two are tuned near the same fundamental and
   coupled through the block, so the note is two normal modes a few tenths of a Hz to ~2 Hz apart: the tine-heavy
   one decays faster, the tonebar-heavy one stores energy and carries the long sustain (bar_sus x tau1), and the
   difference beats slowly. The tine's own second bending mode (~5-7 x f0, ideal 6.27) is the short "bell/ping" in the
   attack. The kalimba's wooden box (Helmholtz + plate modes), knock, skin noise and sympathetic tines are removed:
   a Rhodes is heard through its pickup, not through a radiating body.
3. Pickup: the tine tip swings laterally in front of an electromagnetic pickup. The coil sees the flux, a bell-shaped
   function of the tip's offset from the pole axis, f(u) = 1 / (1 + u^2) (u = displacement / field width), and the
   voltage is d/dt f(u(t) + off). With the tine set off-axis by `off` the small-signal response is linear (fundamental)
   plus an asymmetry (even harmonics, 2nd strongest); when the swing amplitude approaches `off` the tip crosses the
   field's peak and the output folds: the Rhodes "bark", strongest on hard notes and fading as the note decays
   (the nonlinearity acts on the decaying displacement, before any envelope). The coil's inductance into the cable's
   capacitance is a resonant low-pass (coil_hz, coil_q).
   Then an optional amp: an asymmetric tube-ish tanh (amp_drive) and a 12" speaker box (high-pass 80 Hz, low-pass
   ~5.5 kHz, a presence bump), an optional stereo tremolo (Suitcase "vibrato" is a panning tremolo), a small room
   (or nearly dry) and a mic noise floor. Damper: at key-off the felt damper falls on the tine (release tau damp_tau).
Pitch: `f0` in Hz or a note name ('E4', 'F#3'); velocity `vel` 0..1; `dur` = key hold time in seconds.
"""
import numpy as np
from scipy import signal

from earshot.forge import dsp
from earshot.forge.recipes.pluck import note as _note_name

SR = dsp.SR

SPACE = {
    'hammer_ms': (0.4, 3.0, 'log'),   # contact time at vel 1 (felt/neoprene tip); soft tips are longer
    'hard_exp': (0.15, 0.4),          # T ~ v^-hard_exp (Hertz contact of a stiffening felt)
    'tau1': (1.0, 6.0, 'log'),        # tine-mode decay at C5 (lower notes longer, ~ f^-0.5)
    'bar_lvl': (0.1, 0.6),            # share of the tonebar-heavy normal mode
    'bar_sus': (1.2, 3.0),            # its decay relative to tau1
    'beat_hz': (0.2, 2.5, 'log'),     # split of the two normal modes (tine/tonebar coupling)
    'p2_ratio': (5.0, 7.0),           # tine second bending mode / f0
    'p2_lvl': (0.0, 0.6),             # its velocity amplitude at the strike (before the hammer's filter)
    'p2_tau': (0.02, 0.3, 'log'),     # its decay at C5
    'amp': (0.05, 1.6, 'log'),        # tip swing at vel 1, in field widths
    'off': (0.15, 1.0),               # tine offset from the pole axis, in field widths (voicing)
    'coil_hz': (2500, 9000, 'log'),   # coil + cable resonance
    'coil_q': (0.5, 2.0),
    'amp_drive': (0.0, 3.0),          # 0 = DI (no amp)
    'trem_hz': (0.0, 6.0),
    'trem_depth': (0.0, 0.6),
    'damp_tau': (0.08, 0.8, 'log'),   # key-off release
    'room_wet': (0.0, 0.3),
    'rt60': (0.15, 0.8, 'log'),
    'width': (0.0, 0.3),
    'air_db': (-9.0, 0.0),
    'floor_db': (-96.0, -66.0),
}

_BASE = {'hammer_ms': 1.2, 'hard_exp': 0.25, 'tau1': 2.6, 'bar_lvl': 0.35, 'bar_sus': 1.4, 'beat_hz': 0.7,
         'p2_ratio': 6.0, 'p2_lvl': 0.25, 'p2_tau': 0.08, 'amp': 0.35, 'off': 0.55, 'coil_hz': 5200.0, 'coil_q': 0.9,
         'amp_drive': 0.0, 'trem_hz': 0.0, 'trem_depth': 0.0, 'damp_tau': 0.6, 'room_wet': 0.06, 'rt60': 0.3,
         'width': 0.08, 'air_db': -3.0, 'floor_db': -84.0}

PRESETS = {
    # A mellow: long soft contact, tine well off-axis and a small swing -> nearly linear pickup, little 2nd mode
    'A': {**_BASE, 'hammer_ms': 2.6, 'hard_exp': 0.2, 'p2_lvl': 0.12, 'amp': 0.3, 'off': 0.65, 'coil_hz': 4200.0,
          'coil_q': 0.8, 'amp_drive': 0.0, 'room_wet': 0.08},
    # B classic: medium tip, tine moderately off-axis; bark appears on the louder notes only
    'B': {**_BASE, 'hammer_ms': 1.3, 'hard_exp': 0.25, 'p2_lvl': 0.25, 'amp': 0.45, 'off': 0.5, 'coil_hz': 5200.0,
          'amp_drive': 0.6},
    # C bite: hard short contact, tine close to the axis and a big swing -> the tip crosses the field peak: bark
    'C': {**_BASE, 'hammer_ms': 0.6, 'hard_exp': 0.3, 'p2_lvl': 0.4, 'p2_tau': 0.06, 'amp': 0.95, 'off': 0.35,
          'coil_hz': 6500.0, 'coil_q': 1.1, 'amp_drive': 1.4, 'room_wet': 0.04},
    # D: my pick for "most Rhodes": Mark I voicing (bark only when pushed, so the motif's 0.7-0.8 notes growl a little
    # and the soft D4+A4 dyad stays round), a clear tonebar beat, a Suitcase-style amp and its panning tremolo
    'D': {**_BASE, 'hammer_ms': 1.1, 'hard_exp': 0.3, 'tau1': 3.0, 'bar_lvl': 0.3, 'bar_sus': 1.5, 'beat_hz': 0.9,
          'p2_lvl': 0.3, 'p2_tau': 0.07, 'amp': 0.62, 'off': 0.45, 'coil_hz': 5000.0, 'coil_q': 1.0,
          'amp_drive': 1.0, 'trem_hz': 3.2, 'trem_depth': 0.28, 'room_wet': 0.07, 'width': 0.0},
}
DEFAULTS = PRESETS['D']


def pitch_hz(f0):
    if isinstance(f0, str):
        s = f0.strip().lower()
        return float(s[:-2]) if s.endswith('hz') else _note_name(f0.strip())
    return float(f0)


def contact_ms(p, vel):
    """hammer contact time (ms) at velocity vel"""
    return float(np.clip(p['hammer_ms'] * max(vel, 0.05) ** -p['hard_exp'], 0.3, 4.0))


def _displacement(p, f0, vel, n, r):
    """tine tip displacement (in field widths): coupled tine/tonebar normal modes + the tine's 2nd mode,
    struck by a half-sine force pulse"""
    t = np.arange(n) / SR
    tau1 = p['tau1'] * (f0 / 523.25) ** -0.5
    w1 = 2 * np.pi * f0
    ph = r.uniform(-0.02, 0.02)
    m = p['bar_lvl']
    h = (1 - m) * np.sin(w1 * t + ph) * np.exp(-t / tau1)                                         # tine-heavy mode
    fb = f0 + p['beat_hz'] * (1 + 0.05 * r.standard_normal())
    h += m * np.sin(2 * np.pi * fb * t + ph) * np.exp(-t / (tau1 * p['bar_sus'])) * (w1 / (2 * np.pi * fb))
    f2 = f0 * p['p2_ratio'] * (1 + 0.004 * r.standard_normal())
    if p['p2_lvl'] > 0.003 and f2 < SR * 0.45:
        tau2 = p['p2_tau'] * (f0 / 523.25) ** -0.5
        h += p['p2_lvl'] * (f0 / f2) * np.sin(2 * np.pi * f2 * t) * np.exp(-t / tau2)           # 1/w: displacement
    T = contact_ms(p, vel) / 1000
    k = max(3, int(round(T * SR)))
    pulse = np.sin(np.pi * (np.arange(k) + 0.5) / k)
    x = signal.fftconvolve(h, pulse / pulse.sum())[:n]
    return x / (np.abs(x).max() + 1e-12) * p['amp'] * vel


def _damper(n, dur, tau):
    t = np.arange(n) / SR
    return np.where(t > dur, np.exp(-(t - dur) / tau), 1.0)


def voice(p, f0, vel, dur, r, tail=2.5):
    """one note through the pickup and coil: mono, at the pickup's own (physical) level, register-normalised"""
    f0 = pitch_hz(f0)
    n = dsp.n_of(dur + tail)
    x = _displacement(p, f0, vel, n, r) * _damper(n, dur, p['damp_tau'])
    flux = 1.0 / (1.0 + (x + p['off']) ** 2)
    y = np.gradient(flux) * SR / (2 * np.pi * f0)                    # emf = d(flux)/dt; voicing evens out the register
    y = dsp.butter(y, 'low', p['coil_hz'], 2)
    if p['coil_q'] > 0.71:
        y = dsp.peq(y, p['coil_hz'] * 0.9, 20 * np.log10(p['coil_q'] / 0.707), 1.2)
    return dsp.butter(y, 'high', 25, 1)


def chain(p, y, r):
    """amp (optional), speaker, tremolo, room, mic: mono pickup signal -> 48 kHz stereo"""
    y = y / (np.abs(y).max() + 1e-12)
    if p['amp_drive'] > 0.01:
        k, b = 1 + p['amp_drive'] * 2.0, 0.12                       # asymmetric (tube-ish) soft clip
        y = (np.tanh(k * (y + b)) - np.tanh(k * b)) / k
        y = dsp.butter(y, 'high', 80, 2)
        y = dsp.butter(y, 'low', 5500, 2)
        y = dsp.peq(y, 1800, 2.0, 0.8)
        y = dsp.peq(y, 350, -1.0, 0.8)
    x = dsp.stereo(y, r, width=p['width'], pan=0.0)
    if p['trem_depth'] > 0.005 and p['trem_hz'] > 0.05:
        t = np.arange(len(x)) / SR
        lfo = np.sin(2 * np.pi * p['trem_hz'] * t)
        g = p['trem_depth']
        x[:, 0] *= 1 - g * 0.5 * (1 + lfo)
        x[:, 1] *= 1 - g * 0.5 * (1 - lfo)
    x = dsp.room(x, r, rt60=p['rt60'], size=0.2, damp=0.6, wet=p['room_wet'])
    x = dsp.mic(x, r, low_cut=20.0, air_db=p['air_db'], floor_db=p['floor_db'])
    return x


def render(p, r):
    """one note, 48 kHz stereo (n, 2); p['f0'] (Hz or note name), p['vel'] (0..1), p['dur'] (key hold, s)"""
    f0 = p.get('f0') or 'E4'
    dur = p.get('dur', 1.5)
    x = chain(p, voice(p, f0, p.get('vel', 0.8), dur, r), r)
    x = x[: dsp.n_of(dur + 2.5)]
    return dsp.fade(x, 0.0005, 0.3)


def phrase(p, notes, length, r, jitter=None):
    """notes = [(at_s, [midi...], dur_s, vel)], the sfx-mixer MOTIF format; chord notes 30 ms apart"""
    jitter = jitter or dsp.rng(4)
    y = np.zeros(dsp.n_of(length))
    for at, ms, dur, vel in notes:
        for k, m in enumerate(ms):
            v = vel * jitter.uniform(0.9, 1.0)
            dsp.place(y, voice(p, 440.0 * 2 ** ((m - 69) / 12), v, dur, r), at + k * 0.03)
    x = chain(p, y, r)[: len(y)]
    return dsp.fade(x, 0.0005, 0.5)
