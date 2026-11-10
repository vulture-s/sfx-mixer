# SFX Mixer

A small, single-page sound-to-picture mixer for short films and motion graphics. It runs in the browser with no build step and no dependencies. You place one-shot sound effects on frames, then mix them against a music bed like you would in a DAW. When you're done, export the result as a WAV file or save the session as JSON.

**Try it online:** <https://vulture-s.github.io/sfx-mixer/>

| Demo | Link |
|---|---|
| Demo session (32 s: UI clicks, typing, whoosh) | <https://vulture-s.github.io/sfx-mixer/> |
| 2 a.m. rain (lofi + ambience) | <https://vulture-s.github.io/sfx-mixer/?project=lofi/> |
| Fjord, 4 a.m. (ambient) | <https://vulture-s.github.io/sfx-mixer/?project=nordic/> |

- **Mix window**: one channel strip per track (music bed + each cue), with mute / solo (Pro Tools rules: any solo ⇒ only soloed tracks play; mute beats solo), fader, pan, send, room / hall return and an insert rack.
- **Edit window**: a timeline of every cue, with a playhead. Click anywhere on it to jump.
- **Insert rack** (per track): pitch / start / attack / length, filter with sweep, lo-fi (drive, bit depth, sample-rate reduction), beat-synced stutter, Euclidean choke gate, tempo delay and tape stop. The rhythmic and lo-fi modules are printed into a new buffer before playback, so what you hear in real time matches the exported file.
- **Groups (VCA)**: one level per group, plus music ducking under cues, a short pre-roll so transients land slightly before the frame, an ambience bed and a look-ahead limiter on export.

## Run

```bash
python3 -m http.server 8000
# open http://localhost:8000/            → the bundled demo
# open http://localhost:8000/?project=myfilm/   → your own project folder
```

Any static file server works. Opening `index.html` from disk won't work, because the browser blocks `fetch()` on `file://` URLs.

## Use your own sounds (no install)

Drag audio files onto the page, or press **＋ 你的音效** above the scope. They are decoded in your browser and never uploaded anywhere.

- **Audio only**: each file becomes its own track, laid out one after another. A file whose name starts with `bgm`, `music` or `bed` becomes the music bed.
- **With a cue sheet**: drop `cues.json` (and optionally `project.json` and a video) together with the audio files, and the page builds that project. Samples are matched by file name without the extension, so `thud.mp3` serves a cue whose `src` is `thud`.
- Formats are whatever your browser can decode (wav, mp3, m4a and flac are safe bets).

To keep a project or share it, use the folder layout below and serve it, or fork the repo.

## Your own project

Create a folder next to `index.html` and add these files:

```
myfilm/
  project.json
  cues.json
  film.mp4          (optional — without it you get a play bar)
  audio/<name>.wav  (one file per sample name used in cues.json)
```

**project.json**

```json
{
  "title": "My film",
  "fps": 60,
  "duration": 32,
  "video": "film.mp4",
  "bgm": { "src": "audio/music.flac", "label": "Music bed" },
  "groups": [ { "id": "hit", "label": "Hits", "color": "#c43d2b" } ],
  "session": { "global": {}, "cues": {} }
}
```

`session` is the state the page opens on. Paste a saved settings JSON there (its `global` and `cues` parts).

**cues.json**: an array of cues. Frames use the project's `fps`.

| field | meaning |
|---|---|
| `id`, `label`, `group` | identity, label shown on the strip, group id from `project.json` |
| `at`, `dur` | first frame of the sound and how many frames it stays mounted |
| `src` | sample name, read from `audio/<src>.wav` |
| `vol` | base gain |
| `space`, `send` | default return (`dry` / `room` / `hall`) and send amount |
| `start` | ms into the file where the transient actually begins (used when "起音對齊" is on). Many library files have 50–200 ms of silence or handling noise before the hit. Measure it, or the sound will land late. |
| `fade`, `duck` | tail fade in frames; how far the music ducks under this cue, in dB |
| `hits`, `pool`, `soft` | optional, turns the cue into a run of hits (for example typing). `hits` lists the frames, `pool` lists the samples to rotate through, and `soft` lists the hit indices to play quieter |

Tip for typing on screen: if `n` characters are revealed linearly between frames `a` and `b`, character `k` appears at `a + ceil(k·(b−a)/n)`.

## Demo material

Everything in `demo/` was synthesised from scratch for this repository (clicks, ticks, a low thud, a filtered-noise whoosh, a knob, a hum, a chime, eight key clicks and a 120 BPM bed). It contains no recordings or third-party samples.

## Second demo: 2 a.m. rain (lofi + ambience)

Open `http://localhost:8000/?project=lofi/` for a 32-second lofi hip hop sketch built entirely out of cues. It shows that the same mixer can work as a small sequencer.

- **Every part is its own track**: drums, Rhodes-style electric piano, bass, a two-phrase melody, vinyl crackle, a bright pulse and an electronic bass that both move from near to far, with rain, distant traffic and a low drone as the bed. Mute or solo any of them.
- **The lo-fi character lives in the insert rack, not in the samples**: bit reduction and drive on the keys, 12-bit snare, 8-bit hats, a tempo delay on the melody, a downward filter sweep on the pulse and a tape stop on the last chord. Switch the inserts off to hear the dry version.
- **Drums are `hits` cues**: swung 16ths are frames shifted by 4, ghost notes are the `soft` indices. With a pool of four bar-long samples, the keys and bass play the chord progression in order (Fmaj9, E7♯9, Am9, Gm9–C13).
- **Shape**: rain alone, then the groove, then the drums drop out while the melody answers, then one last chord stops like tape.
- 60 BPM, because the mixer's beat-synced modules assume 120 BPM and half of that keeps them on the grid.

Every sound was synthesised from scratch. `bash lofi/src/build.sh` regenerates all of them (needs Python with numpy and scipy, plus ffmpeg).

## Third demo: Fjord, 4 a.m. (ambient)

`?project=nordic/` plays a 60-second ambient piece: footsteps in snow, a low D + A drone, a slow synth pad (Dm9 · B♭maj7♯11 · Fmaj9/C · Dsus2), and wind over ice as the bed. An electric-piano motif (D · A · F · E) comes three times; the third time the E never arrives. High bells close it out. Long hall reverb and a dotted-eighth delay on the piano come from the insert rack. `bash nordic/src/build.sh` regenerates every sound.

## Forge versions: the same pieces, voiced by earshot

`?project=lofi-forge/` and `?project=nordic-forge/` are the lofi and Fjord demos with the same cue sheet, groups and
mix, but their drums and tuned voices rendered from the forge bank of [earshot](https://github.com/Leonxlnx/earshot)
(MIT, Leon Lin; pinned at commit `4ac3d2ac2b151e1c23376f9ce7f3047a17050013`). Switch between a demo and its forge
version in the track menu to compare hand-written synthesis with the forge, part by part.

- Live: https://vulture-s.github.io/sfx-mixer/?project=lofi-forge/ and https://vulture-s.github.io/sfx-mixer/?project=nordic-forge/
- **lofi-forge**: kicks `cut_hit/kick` and `cut_hit/sub` (landing at 48 Hz), hats `hover_tick/air`, `hover_tick/high`,
  `pro_hover_tick/soft`, keys `pluck/kalimba_soft` and melody `pluck/kalimba`, one pitched note per chord tone and
  melody note, with the original voicings, swing, tape wow and tremolo. Kept from the original synthesis: snare,
  bass, dudu, electronic bass, vinyl crackle and the rain bed.
- **nordic-forge**: the piano motif on `pluck/kalimba_ring` and the high bells on `mallet/glock`, same notes and timing,
  the bells into the original hall. Kept from the original synthesis: pads, drone, snow steps and the wind bed.
- The forged cues' base `vol` is raised by the measured loudness gap (ffmpeg ebur128, 3-7 dB: the forge parts have
  sharper attacks at the same peak); everything else matches the original.
- The bank renders with numpy and scipy only, and no `fit/*` entry is used, so these demos also contain no
  recordings or third-party samples. `bash lofi-forge/src/build.sh` and `bash nordic-forge/src/build.sh` rebuild them
  (Python with earshot, numpy and scipy, plus ffmpeg); each `make_*_forge.py` lists every part and its bank id.

## Electric-piano versions: a physical Rhodes on the forge dsp

`?project=lofi-epiano/` and `?project=nordic-epiano/` are the two forge versions with their kalimba keys and piano
swapped for a Rhodes-style electric piano, computed from physics in [`epiano/epiano.py`](epiano/epiano.py): a felt
hammer whose contact time shortens on harder blows, a tine and its tonebar as two coupled modes (a slow 0.9 Hz beat
and a long sustain), and an electromagnetic pickup whose bell-shaped field adds even harmonics and, on hard notes,
the "bark". Preset D is used: Mark I voicing (only the 0.7-0.8 notes bark a little), a Suitcase-style amp and its
3.2 Hz panning tremolo. It is built on the forge dsp of [earshot](https://github.com/Leonxlnx/earshot) (MIT, Leon
Lin; same pinned commit `4ac3d2ac2b151e1c23376f9ce7f3047a17050013`), rewriting the tine model of its `pluck` recipe.

- Live: https://vulture-s.github.io/sfx-mixer/?project=lofi-epiano/ and https://vulture-s.github.io/sfx-mixer/?project=nordic-epiano/
- **nordic-epiano**: piano-1/2/3 are the original motif (same notes, timing, velocities and jitter seed) on preset D.
  Everything else (pads, drone, snow, wind, the forge bells) is copied from `nordic-forge/`.
- **lofi-epiano**: the keys are the original voicings, 12 ms strum, swing, tape wow and 4.3 Hz tremolo on preset D,
  with the amp drive halved for the chords (each tine has its own pickup, so only the shared amp mixes the notes of a
  chord; the drive is set so a four-note chord intermodulates no more than the approved motif does) and the amp's own
  tremolo off, so it does not beat against the original's. The melody stays the forge kalimba; everything else is
  copied from `lofi-forge/`.
- The new cues' base `vol` is lowered by the measured loudness gap against the forge parts they replace (ffmpeg
  ebur128, 5.3-5.8 dB: the pickup's sustained tone is louder at the same peak).
- Every sample is computed with numpy and scipy; no bank entry, recording or third-party sample is used, so these
  demos also contain no recordings or third-party samples. `bash lofi-epiano/src/build.sh` and
  `bash nordic-epiano/src/build.sh` rebuild them; each `make_*_epiano.py` lists every part and its source.

The page's track menu (under the play bar) switches between the demos.

## License

MIT — see [LICENSE](LICENSE).

---

# SFX Mixer（中文）

一頁式的音效對畫面混音器，打開瀏覽器就能用，不用建置，也沒有任何相依套件。把單發音效放在指定的影格上，再像在 DAW 裡一樣和配樂一起混音，完成後匯出 WAV，或把設定存成 JSON。

**線上試用：** <https://vulture-s.github.io/sfx-mixer/>

| Demo | 網址 |
|---|---|
| Demo session（32 秒：UI 點擊、打字、whoosh） | <https://vulture-s.github.io/sfx-mixer/> |
| 2 a.m. rain（lofi＋環境音） | <https://vulture-s.github.io/sfx-mixer/?project=lofi/> |
| Fjord, 4 a.m.（ambient） | <https://vulture-s.github.io/sfx-mixer/?project=nordic/> |

- **Mix 視窗**：每軌一條（配樂一條，每個 cue 各一條），有 M／S（規則同 Pro Tools：任何一軌開 solo，就只聽得到 solo 的軌；mute 比 solo 優先）、推桿、pan、send、room／hall 回送，以及 Insert 效果架。
- **Edit 視窗**：所有 cue 排在時間軸上，有播放線，點時間軸任何位置就能跳過去。
- **Insert 效果架**（每軌都有）：
  - 音高、起點、attack、長度
  - 濾波器，可以掃頻
  - Lo-fi：drive、bit 數、降取樣
  - 跟拍的 stutter
  - Euclidean choke 閘門
  - 跟拍 delay
  - tape stop

  stutter、choke 這類節奏效果和 lo-fi，會先把整顆音效算好再播，所以即時聽到的跟匯出的檔案一模一樣。
- **分類音量（VCA）**：每個分類一條總音量。另外還有：音效出現時壓低配樂、提前觸發讓起音略早於畫面、環境底層，匯出時會經過前視限幅器。

**用自己的音效（不用安裝）**：把音檔拖進頁面，或按示波器上方的「＋ 你的音效」。檔案只在你的瀏覽器裡解碼，不會上傳。只丟音檔的話，每個檔自動變成一軌、依序排開；檔名以 `bgm`、`music` 或 `bed` 開頭的會當成配樂。連同 `cues.json`（可再加 `project.json` 和影片）一起丟，就會照 cue 表建出整個專案，檔名不含副檔名要跟 `src` 對得上。

**執行**：在這個資料夾裡執行 `python3 -m http.server 8000`，然後開 `http://localhost:8000/`。要載入自己的專案，網址加上 `?project=資料夾/`。資料檔的格式見上面的英文說明。

**最重要的一個提醒**：音效庫的檔案在真正的起音前，常有 50–200 ms 的空白或雜音。請把這段長度量出來，填進 cue 的 `start` 欄位，不然聲音一定會比畫面晚。

**第二個示範「2 a.m. rain」**：網址加 `?project=lofi/`。這是一段 32 秒的 lofi hip hop，全部用 cue 排出來，示範這台混音器也能當小型編曲器用。
- 每個聲部都是獨立的一軌：鼓、電鋼琴、貝斯、旋律、黑膠底噪，還有兩條由近到遠的聲音（明亮的脈衝音、電子 bass）。雨聲、遠處車流和低頻嗡鳴當底層。
- lofi 的質感大多來自 Insert 效果架，素材本身是乾淨的。把效果關掉就能聽到前後差別。
- 素材全部用程式合成。執行 `bash lofi/src/build.sh` 可以重新產生（需要 numpy、scipy、ffmpeg）。

**第三個示範「Fjord, 4 a.m.」**：網址加 `?project=nordic/`。這是 60 秒的北歐氛圍音樂：雪地腳步、低頻嗡鳴、緩慢的合成器 pad，風聲當底層。電鋼琴動機 D·A·F·E 出現三次，第三次最後那個 E 沒有出現。執行 `bash nordic/src/build.sh` 可以重新產生所有聲音。播放列下方的選單可以切換各個示範。

**forge 版（`lofi-forge/`、`nordic-forge/`）**：cue 表、分組、混音跟原版一樣，只把鼓和有音高的聲部換成 [earshot](https://github.com/Leonxlnx/earshot)（MIT，Leon Lin；鎖在 commit `4ac3d2ac2b151e1c23376f9ce7f3047a17050013`）forge 音色庫算出來的聲音，可以在選單裡跟原版切換 A/B。
- 網址：<https://vulture-s.github.io/sfx-mixer/?project=lofi-forge/>、<https://vulture-s.github.io/sfx-mixer/?project=nordic-forge/>
- **lofi-forge**：kick 用 `cut_hit/kick`、`cut_hit/sub`，hats 用 `hover_tick/air`、`hover_tick/high`、`pro_hover_tick/soft`，電鋼琴和旋律用 `pluck/kalimba_soft`、`pluck/kalimba` 照原音符逐音重做。snare、bass、dudu、電子 bass、黑膠底噪、雨聲維持原版合成。
- **nordic-forge**：鋼琴動機用 `pluck/kalimba_ring`，高音鈴用 `mallet/glock`。pad、嗡鳴、雪地腳步、風聲維持原版合成。
- forge 聲部的 cue `vol` 依實測響度差（ffmpeg ebur128，3–7 dB）調高，其他設定不變。
- forge 只用 numpy／scipy 運算，也沒有用到 `fit/*` 條目，所以這兩個示範一樣沒有任何錄音或第三方素材。

**電鋼琴版（`lofi-epiano/`、`nordic-epiano/`）**：把兩個 forge 版的 kalimba 電鋼琴換成 Rhodes 風格的電鋼琴，聲音由 [`epiano/epiano.py`](epiano/epiano.py) 依物理模型算出：毛氈琴槌（敲得越重、接觸時間越短，聲音越亮也越大聲）、音叉與音棒兩個耦合模態（0.9 Hz 的慢拍頻和長延音），以及電磁拾音器（鐘形磁場帶出偶次泛音，重音時出現「咬聲」）。用的是 D 配方：Mark I 式的調聲（只有力度 0.7–0.8 的音會微微咬）、Suitcase 式音箱和 3.2 Hz 左右聲道 tremolo。它建立在 [earshot](https://github.com/Leonxlnx/earshot)（MIT，Leon Lin；同樣鎖在 commit `4ac3d2ac2b151e1c23376f9ce7f3047a17050013`）的 forge dsp 上，改寫自它 `pluck` 配方的音叉模型。
- 網址：<https://vulture-s.github.io/sfx-mixer/?project=lofi-epiano/>、<https://vulture-s.github.io/sfx-mixer/?project=nordic-epiano/>
- **nordic-epiano**：piano-1/2/3 照原版動機（音符、時間、力度、抖動種子都相同）用 D 配方重做。其餘（pad、嗡鳴、雪地腳步、風聲、forge 高音鈴）直接沿用 `nordic-forge/`。
- **lofi-epiano**：電鋼琴照原版和弦音、12 ms 由低到高的 strum、swing、磁帶 wow 和 4.3 Hz tremolo 用 D 配方重做；和弦把音箱推力減半（每根音叉有自己的拾音器，只有共用的音箱會讓和弦內的音互調，推力調到四音和弦的互調不超過已確認的動機），並關掉音箱自己的 tremolo，免得跟原版的打拍。旋律維持 forge 的 kalimba，其餘直接沿用 `lofi-forge/`。
- 新聲部的 cue `vol` 依跟被取代的 forge 聲部的實測響度差（ffmpeg ebur128，5.3–5.8 dB）調低。
- 全部用 numpy／scipy 運算，沒有用到音色庫條目、錄音或第三方素材，所以這兩個示範一樣沒有任何錄音或第三方素材。

`demo/` 裡的聲音全部用程式合成，沒有任何錄音或第三方素材。授權：MIT（見 [LICENSE](LICENSE)）。
