# SFX Mixer

A small, single-page sound-to-picture mixer for short films and motion graphics. It runs in the browser with no build step and no dependencies. You place one-shot sound effects on frames, then mix them against a music bed like you would in a DAW. When you're done, export the result as a WAV file or save the session as JSON.

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

## License

MIT — see [LICENSE](LICENSE).

---

# SFX Mixer（中文）

一頁式的音效對畫面混音器，打開瀏覽器就能用，不用建置，也沒有任何相依套件。把單發音效放在指定的影格上，再像在 DAW 裡一樣和配樂一起混音，完成後匯出 WAV，或把設定存成 JSON。

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

**執行**：在這個資料夾裡執行 `python3 -m http.server 8000`，然後開 `http://localhost:8000/`。要載入自己的專案，網址加上 `?project=資料夾/`。資料檔的格式見上面的英文說明。

**最重要的一個提醒**：音效庫的檔案在真正的起音前，常有 50–200 ms 的空白或雜音。請把這段長度量出來，填進 cue 的 `start` 欄位，不然聲音一定會比畫面晚。

`demo/` 裡的聲音全部用程式合成，沒有任何錄音或第三方素材。授權：MIT（見 [LICENSE](LICENSE)）。
