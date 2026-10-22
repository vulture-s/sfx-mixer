import json, os, sys
OUT = sys.argv[1]
BAR, STEP = 240, 15
def fr(bar, step): return BAR * bar + STEP * step + (4 if step % 2 else 0)
def run(bars, steps_of, soft_of=lambda b: []):
    hits, soft = [], []
    for b in bars:
        for s in sorted(set(steps_of(b)) | set(soft_of(b))):
            if s in soft_of(b): soft.append(len(hits))
            hits.append(fr(b, s))
    return hits, soft
G = [1, 2, 3, 4]
kh, _ = run(G, lambda b: [0, 7, 10] + ([14] if b == 4 else []))
kh.append(fr(7, 0))
sh, ss = run(G, lambda b: [4, 12], lambda b: {2: [15], 3: [9], 4: [15]}.get(b, []))
hh, hs = run(G, lambda b: list(range(0, 16, 2)), lambda b: [3, 11] + ([13, 15] if b == 4 else []))
KEYS = ["F", "E", "Am", "GmC"]
def c(id, label, group, src, at, dur, vol, space="dry", send=0.0, duck=None, fade=0, **kw):
    d = dict(id=id, at=at, src=src, label=label, group=group, vol=vol, dur=dur, space=space, send=send, start=0, fade=fade, duck=duck); d.update(kw); return d
cues = [
    c("crackle", "Vinyl crackle", "texture", "crackle", 0, 1920, 0.6),
    c("keys", "Rhodes: Fmaj9 · E7♯9 · Am9 · Gm9–C13", "keys", "pool", 0, 1680, 0.5, "room", 0.08, pool=[f"keys-{k}" for k in KEYS], hits=[BAR * b for b in range(7)], soft=[]),
    c("kick", "Kick", "drums", "pool", kh[0], kh[-1] - kh[0] + 40, 0.9, pool=["kick1", "kick2"], hits=kh, soft=[]),
    c("snare", "Snare + ghost notes", "drums", "pool", sh[0], sh[-1] - sh[0] + 30, 0.42, "room", 0.05, pool=["snare1", "snare2"], hits=sh, soft=ss),
    c("hats", "Hats (swung 16ths)", "drums", "pool", hh[0], hh[-1] - hh[0] + 15, 0.22, pool=["hat1", "hat2", "hat3"], hits=hh, soft=hs),
    c("bass", "Bass", "bass", "pool", BAR, 4 * BAR, 0.6, pool=[f"bass-{k}" for k in KEYS], hits=[BAR * b for b in (1, 2, 3, 4)], soft=[]),
    c("melody-call", "Melody: call", "melody", "melody-call", 3 * BAR, 540, 0.32, "hall", 0.18, duck=-2),
    c("melody-answer", "Melody: answer (no drums)", "melody", "melody-answer", 5 * BAR, 540, 0.32, "hall", 0.18, duck=-2),
    c("dudu", "Dudu: near → far", "fx", "dudu", BAR, 600, 0.38, "hall", 0.12),
    c("ebass", "Electronic bass: near → far", "fx", "ebass", BAR, 600, 0.5, "room", 0.05),
    c("last-chord", "Last chord → tape stop", "keys", "keys-last", 7 * BAR, 240, 0.55, "room", 0.08),
]
# hits pool order is (sum of id char codes + 5i) mod len — check every progression lands on the right chord
def order(cue):
    seed = sum(map(ord, cue["id"])); P = cue["pool"]; return [P[(seed + i * 5) % len(P)] for i in range(len(cue["hits"]))]
by = {x["id"]: x for x in cues}
assert order(by["keys"]) == [f"keys-{k}" for k in KEYS * 2][:7], order(by["keys"])
assert order(by["bass"]) == ["bass-E", "bass-Am", "bass-GmC", "bass-F"], order(by["bass"])
melfx = dict(delay="1/8", fb=0.3, dmix=0.22, lpf=5000, bits=10, decim=2)
session = {"global": {"preRoll": 0, "amb": -70, "bgm": -16, "master": -5, "bgmFx": {"hpf": 500, "lpf": 5000, "q": 0.7, "drive": 0, "bits": 16, "sweep": 0}},
           "cues": {"keys": {"fx": {"lpf": 3200, "drive": 7, "bits": 9, "decim": 3}},
                    "last-chord": {"fx": {"lpf": 3200, "drive": 7, "bits": 9, "decim": 3, "tape": 0.5}},
                    "snare": {"fx": {"bits": 12, "lpf": 4500}},
                    "hats": {"pan": 0.25, "fx": {"lpf": 7000, "bits": 8}},
                    "dudu": {"fx": {"lpf": 16000, "sweep": -1.5}},
                    "melody-call": {"pan": -0.15, "fx": melfx}, "melody-answer": {"pan": 0.15, "fx": melfx}}}
project = {"title": "2 a.m. rain", "fps": 60, "duration": 32, "video": None,
           "bgm": {"src": "audio/rain.flac", "label": "Rain, traffic, drone"},
           "groups": [{"id": "drums", "label": "Drums", "color": "#c43d2b"}, {"id": "keys", "label": "Keys", "color": "#7a6cff"},
                      {"id": "bass", "label": "Bass", "color": "#2a56c6"}, {"id": "melody", "label": "Melody", "color": "#e0a43b"},
                      {"id": "texture", "label": "Vinyl", "color": "#8a8a7a"}, {"id": "fx", "label": "FX", "color": "#2fb59a"}],
           "session": session}
json.dump(project, open(os.path.join(OUT, "project.json"), "w"), indent=1, ensure_ascii=False)
json.dump(cues, open(os.path.join(OUT, "cues.json"), "w"), indent=1, ensure_ascii=False)
print("cues", len(cues), "kick", len(kh), "snare", len(sh), "ghost", ss, "hats", len(hh))
