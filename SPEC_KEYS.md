# Rotation video spec keys (make_story.py = Shorts, make_long.py = long-form)

Updated 2026-10-29 for the "Study 2" upgrade, then the **v7 / Study 3** upgrade (section at the end supersedes anything above it). Backups of the previous code: `make_story.bak6.py`, `make_long.bak6.py`, `opener.bak6.py`, `gfx.bak6.py`.
New shared module: `mixbus.py` (audio bus). Run with `PYTHONPATH=/workspace/work/pylib:$HOME/.local/lib/python3.12/site-packages`.

## Locked looks (unchanged)
White logo mark + ROTATION top-left (no yellow bar). Shorts captions: white Montserrat 700, 64 px, max width 760, y=1360, with shadow. Stats: yellow #F0B400 boxless count-up, no SFX on numbers; long-form stats keep the dark scrim. Orange-slab Short cover (`cover_overlay`). Grade, vignette and grain. Final loudness -14 LUFS.

## Top-level keys

| Key | Renderer | What it does |
|---|---|---|
| `output` | both | Output mp4 path. |
| `title` | Shorts | Cover headline. It is also the fallback text for the 0-3 s hook card. |
| `scenes` | both | List of scene dicts. The old `[clip, text, stat]` lists still work in Shorts. |
| `rate` | both | edge-tts speaking rate, e.g. `"+24%"` (Shorts) or `"+12%"` (long). Script target: 165-180 WPM. Defaults: Shorts `+5%`, long `+3%`. |
| `outro` | Shorts | **New.** Closing line: the dated next catalyst, e.g. `"The next test comes in early 2027, when Alphabet reports its next results."`. It can be a string or `{"text": ..., "clip": "hd_x" or [..]}`. If missing, the Short ends on the fallback line "Full breakdown in this weekend's deep dive on Rotation." Set `false` for no outro. An old last scene that still reads "Follow Rotation for more stories…" is dropped automatically, and its clip is reused. |
| `outro_clip` | Shorts | Clip for the outro when `outro` is a plain string. Default: the dropped CTA clip, else `hd_49845`. |
| `chapters` | long | **New.** List of 3-4 chapter names. This turns on the chapter-list (agenda) card. |
| `subscribe` | long | **New.** String (card line) or `{"line": ..., "text": VO}`. The subscribe card is placed automatically at the scene boundary nearest 60 % of the runtime. It is never placed in the opener or on a chapter start. A `{"subscribe": ...}` scene still works if you want to place it yourself. |
| `captions` | long | Running captions. Now **off by default**. `true` turns them back on and switches off the keyword pops. |
| `pool` | long | Extra clip ids for auto-split shots, used when a scene has only one clip. |

## Scene keys: Shorts (make_story.py)

| Key | What it does |
|---|---|
| `clip` | Clip id or list of ids. An id may carry an in-point: `"hd_4713@5"` starts 5 s in. Shots cut on sentence or comma beats, and the maximum shot is 7.5 s. |
| `text` | Narration. |
| `hook_card` | **New, first scene only.** A 2-3 line headline card for 0-3 s: white Montserrat 800, sentence case, over a dark gradient. The scene's `loc` pin moves into the card. Fallback: `title`. Set `false` for no card. The first clip should show the subject. |
| `stat` | `["$51.4B", "label"]`. **Changed timing:** it starts as the first number is spoken, counts up for 0.7 s, holds 2.5-4 s, then fades out over 0.3 s. It always sits inside a single shot (the first shot is lengthened, or extra shots are dropped). |
| `pill` | **New.** Company pills (text only, no logos), e.g. `["Alphabet", "Microsoft"]` or `[["Microsoft", "#00A4EF"]]`. They pop in one by one, sit above the captions (y ≈ 1166-1250) and stay about 4.3 s. Not shown while the hook card is up. |
| `sticker` | **New.** A yellow tilted label with a drawn white arrow, e.g. `"AI Mode"` or `{"text", "x", "y", "to": [x, y], "angle"}`. Default: label at (470, 420), arrow pointing to the centre of the frame. Plays one soft click. Stays about 4.2 s. |
| `loc`, `blur`, `card`, `chart` | Unchanged (see the rotation-video-craft skill). Charts now build in steps (below). |
| `vo_gain` / `vo_punch` | Optional voice emphasis override in dB, or force "punch" (+2 dB). |

Keep extras sparse: about 1 pill and 1 sticker per Short. Don't stack a sticker on a `card` or `chart` scene.

## Scene keys: long-form (make_long.py)

| Key | What it does |
|---|---|
| `clip` | Id or list. **Auto-split:** each scene is cut into shots that average `shot` s (default 3.5) and never exceed 6 s. Cuts snap to sentence or comma ends. Extra shots reuse the scene's clips at new in-points (or alternate with neighbouring scenes' clips / `pool`). `"id@sec"` sets an in-point. |
| `shot` | **New.** Target average shot length for this scene. Use `2.0` for cold-open scenes (1.5-2.5 s shots). |
| `max_shot` | Optional per-scene cap (default 6). |
| `keywords` | **New.** 1-4 word pop-ups, e.g. `["$9.1B burn", "HDFC Bank"]`. Each one is timed to the word in the VO, lasts 1.5 s, and appears lower-third left: white Montserrat 800 with a yellow bar, numbers in yellow. If the key is absent, up to `kw_max` (default 2) are auto-pulled from numbers (with their unit: %, B, crore, ₹/$) and proper nouns. `false` turns them off. They are skipped on stat, card, chart, agenda, title and full-frame scenes. |
| `agenda` | **New.** `1`-based chapter number. Shows the chapter-list card over moving footage, with the current chapter in #F0B400. It runs 3 s the first time and 2 s at later chapter starts (`min` overrides). A `chapter: ["Chapter 2", "Name"]` scene renders the same way when `chapters` is set. |
| `stat` | Same new timing as Shorts: count-up 0.7 s, hold 2.5-4 s, fade, inside one shot. The dark scrim is kept. |
| `chart` | Same dicts as before. It now **builds in steps:** a new point, bar or dot group every 1-3 s, then a highlight ring or outline that moves every ~2.5-3 s, then the badge. The finished chart holds for 3 s or less. Chart scenes run at least 8 s (keep the narration under ~20 s). |
| `sting`, `question`, `card` (stack/pills/doc/compare/quote/headline), `loc`, `source`, `title`, `min` | Unchanged. |

### Long opener order (Study 2)
Cold open of 45-75 s in hook scenes with `"shot": 2.0` → `{"sting": true}` (lands at about 0:45-1:15) → `{"question": "..."}` → `{"agenda": 1}` → chapter 1 … Chapter 2 and 3 each start with `{"agenda": n}` (2 s). There is no subscribe card in the opener: use the top-level `subscribe`. Aim for 2.5-3.5 graphics per minute. Stats, cards, charts, agenda cards and keyword pops all count.

## Audio (both renderers, mixbus.py)
- Music is high-passed at 130 Hz (24 dB/oct) and ducked to 24 dB under the voice while it speaks, using an explicit gain envelope instead of a sidechain. It rises to 9 dB under voice-level on music-only stretches longer than 1.2 s, such as the sting and the question and agenda cards.
- The music dips below -60 dB for 0.4 s at sentence-end pauses: about 5 per 3 min, minimum 2.
- Voice emphasis contour: +2.75 dB on "punch" scenes (hook, stat, card, chart, question) and -2.75 dB on explainer scenes. This lifts TTS loudness range into the 5-8 LU target.
- Master: gain to -14 LUFS, gentle limiter at about -2.5 dBFS, then a trim. There is no dynamic loudnorm, so the range is kept.
- Every scene segment is tagged bt709 (setparams + `-colorspace/-color_primaries/-color_trc bt709`) before the concat. This fixes the mid-stream colour reconfigure.

## Script rules (Shorts)
Number + twist hook by 12 s. "Why it matters" by 30 s. A count promise ("Three numbers explain it"). 165-180 WPM. Mix short and long sentences. End on the dated next catalyst (`outro`). Use only sourced numbers.


## v7 / Study 3 upgrade (user approved "yes build it all", 2026-10-29 22:33 IST)
Backups of the v6 code: `make_long.bak7.py`, `opener.bak7.py`, `gfx.bak7.py`, `make_story.bak7.py`. Study: /workspace/web/notes/adda395e-a9fe-460a-aeb7-b7f7c467f3e0/study3-longform.md.
Demo: `long/spec_v7_demo.json` -> `out/demo_v7_long.mp4` (preview `out/demo_v7_long_preview.mp4`), thumbnail `covers/demo_v7_long_thumb.jpg`.
Map data (Natural Earth admin-0, public domain) cached in `data/ne_50m.geojson`, `data/ne_110m.geojson`. Icons are drawn in PIL (`gfx.draw_icon`: factory chip person car phone coin building wafer ship bank).

### New full-screen animated devices (scene keys, make_long.py; each 8-20 s, builds a visible change every <= ~2.6-3 s)
| Key | Spec | Notes |
|---|---|---|
| `map` | `{"view": "world\|asia\|india\|south_asia\|china\|us\|europe\|middle_east\|east_asia\|africa\|latam\|ISO3\|[lon0,lat0,lon1,lat1]", "fill": ["IND"], "pins": [["Mumbai", 72.88, 19.07]], "routes": [["TWN", [72.19, 22.25], "label"]], "zoom_to": "IND", "push": 0.15, "counter": ["12", "plants approved"], "title", "subtitle", "source"}` | Dark flat Mercator, fills light yellow one by one, pins drop with labels, routes (ISO3, pin name or [lon,lat]) draw on in 0.9 s as orange arcs with a label, counter box top-right counts up. Camera: slow push-in 1.0->1.15 (`push`) or `zoom_to` a country (country kept clear of the title band). Source bottom-left. ~6 s render per video-second. |
| `flow` | `{"nodes": ["A", {"label", "sub", "icon"}], "edges": [[0, 1, "₹30,200 cr"]], "layout": "chain\|hub\|cycle", "title", "subtitle", "source"}` | One node per step every 2-3.2 s (incoming arrows draw on, labels yellow); older steps dim to 45 %, all back to full for the final hold. Scene `"sync": true` times steps to narration sentence starts. Max 5 nodes for chain. 15-20 s typical. |
| `timeline` | `{"items": [["Jan 2022", "label"], ...], "now": idx, "title", "subtitle", "source"}` | Axis draws on, then one dated event every 1-2.6 s alternating above/below; newest in yellow; `now` pulses. 5-6 items max. |
| `icons` | `{"rows": [["factory", 12, 5, "plants in production"]], "pct": ["factory", 55, "label"], "title", "subtitle", "source"}` | Outline icons pop with stagger, the first N fill yellow with a "5 of 12" count-up; optional big icon that fills to a %. |
| `morph` | `{"bars": [["Approved", 10, 12], ...], "from": "Mar 2026", "to": "Sep 2026", "title", "subtitle", "prefix", "suffix", "source"}` (also `chart: {"type": "morph", ...}`) | Bars build to the 'from' values, hold, then ease to the 'to' values while the period badge flips; a white tick marks the old value. |
| `tilt` | scene `"tilt": true` or `{"deg": [22, 14], "drift": 0.05, "yaw": 4}` (or inside the chart dict) | 2.5D plane: tilt eases 22°->14° with ~5 % scale drift and slight yaw over a vignetted backdrop. Works on `chart` (line/bar/dots) and all devices above. |

### New scene / top-level keys
| Key | Where | What it does |
|---|---|---|
| `change_every` | top | Default 3.0. Guard: inside any footage shot, if no cut, keyword pop, punch or stat happens for more than ~3 s, the shot is split and its second half reframed (~13 % punch-in on the same clip). The render log prints `V7 longest planned no-change gap` and the measured study-3 metric (`V7 measured`). |
| `punch` | scene | Opt-in centre punch word (locked look unchanged unless used): `"PACKAGING"` or `{"word", "at": "spoken token"}`. 1.4 s, footage dimmed 40 %, scale 1.15->1.0. Use at most ~1 per 2 min. Replaces an overlapping keyword pop. |
| `breath` | top | Chapter breath (default 2.5; `false` to disable): every later agenda card is 2.5 s and is followed by a 2.5 s establishing shot with no VO and music up. Clip: scene `breath_clip`, else the agenda scene's second clip, else the next scene's first clip. Optional `breath_loc` pin. |
| `ending` | top | List of 2-3 lines (strings or `{"text", "clip"}`): verdict (<= 15 words) -> bookend callback to the cold-open number -> dated catalyst. Footage only: no cards, stats or pops, 4.5 s shots. Scene flag `"ending": true` does the same for a hand-placed scene. |
| `endscreen` | top | `{"text": spoken pitch for ONE earlier video, "video": "its title", "line": "Watch next", "clip": [...], "dur": 20}`. Dimmed footage + a 16:9 watch-next slot (left, x 170-1050, y 300-795) + a subscribe circle (right) where YouTube's end-screen elements go. |
| `sync` | scene | For `flow`/`map`/`timeline`: step times = narration sentence starts. |
| `rehook` | scene | Marks the 55-65 % re-hook scene (callback to the hook number + new reveal). The auto subscribe card goes right after it; without it, the card goes at ~60 % of the runtime excluding the end screen. |

### Automatic checks in the render log
- **Near-black guard:** any planned shot whose footage mean luma < 0.12 is swapped (scene clips, neighbours, `pool`, then a fallback list) and logged as `dark clips swapped`.
- **Density curve:** `V7 density /min` reports graphics (stats, cards, charts, devices, agenda, question, keyword pops) in the first minute (target 4-5), the middle (2.5-3) and the last 10 % (<= 1), and `V7 WARN` flags misses plus a missing map / flow / tilted chart between 15 % and 75 % of the runtime.

### Long-form thumbnail (v7, locked change approved 2026-10-29)
`python3 make_thumb_long.py '{"title": ..., "text": "3 FABS, 0 RUNNING", "clip": "hd_2381@2", "art": "<optional map/chart frame png>", "out": ".../covers/long_<date>_<slug>_thumb.jpg"}'`.
Text: 2-4 words, must contain a number or an "A vs B" contrast, must not repeat the title (the script refuses otherwise). "A, B" or "A vs B" -> A white, B yellow; plain text -> numbers yellow. Brand kept: dark footage, left gradient, Montserrat 900, yellow bar, logo + ROTATION top-left, orange rule.

### v7 script rules (weekend long-form)
10-min template: cold open 0:00-0:50 -> sting -> question -> agenda (max 4 items) -> 4-5 chapters of 1:05-2:45; chapter 2 carries a 15-20 s animated segment (flow or tilted chart); "But there's a catch" turn at ~4:30; re-hook with a callback to the hook number at 55-65 %, then the auto subscribe card; final push at 80-90 %; ending block (verdict / callback / dated catalyst, footage only); 20 s end screen pitching one earlier video. Every chapter ends on a bridge line of <= 8 words; a turn word (but / however / the problem / yet) every 30-45 s; questions optional. At least 1 `map` + 1 `flow` + 1-2 tilted charts between 15 % and 75 % of the runtime.


## v8 upgrade (user feedback on the v7 demo, 2026-10-29 23:39 IST) - SUPERSEDES anything above for long-form
User asked: different music per video, no repeated clips, higher-quality footage, no yellow (black and white), better animation, a cleaner ending. Backups of the v7 code: `make_long.bak8.py`, `gfx.bak8.py`, `opener.bak8.py`, `mixbus.bak8.py`, `make_thumb_long.bak8.py`. Shorts (`make_story.py`) are unchanged: `gfx`/`opener` keep the v7 look unless `set_theme("mono")` is called (only make_long.py does).
Demo: `long/spec_v8_demo.json` -> `out/demo_v8_long.mp4` (1440p), preview `out/demo_v8_long_preview.mp4`, thumbnail `covers/demo_v8_long_thumb.jpg`. Notes: /workspace/web/notes/adda395e-a9fe-460a-aeb7-b7f7c467f3e0/study4-v8-footage-music-endings.md.

### New top-level keys (make_long.py)
| Key | Default | What it does |
|---|---|---|
| `v8` | true | Turns on everything below. `false` = exact v7 behaviour. |
| `theme` | "mono" | Black-and-white graphics: white primary/accent, greys for secondary series, near-black panels, thin white rules. Brand logo unchanged. No yellow anywhere in long-form. |
| `res` | [2560, 1440] | Output size. Footage is scaled from the source (prefer 2160p) with lanczos; graphics are drawn at 1920x1080 and lanczos-scaled. |
| `crf` | 17 | x264 quality per scene (preset faster, GOP 60). |
| `tags` | [] | Video-wide clip tags added to every scene's tags. |
| `music` | {"moods": ["doc"]} | `{"moods": [mood for chapter 1, 2, 3...], "opener": mood, "closer": mood, "xfade": 1.6, "tracks": {mood: track_id}}`. Moods: doc / tense / light / ambient. One bed per video: chapter 1 keeps the opener's track, later chapters switch at the agenda card with a crossfade, the last track is aligned so its real ending lands on the final frame. Tracks used in the last 4 videos are skipped (music/used.json). |
| `closer` | - | `{"text": closing line (<= 20 words), "clip" or "tags"}`: ONE final shot, slow push-in 1.00->1.10, no pops/cards. Replaces the v7 `ending` block. |
| `endcard` | {"dur": 10} when `closer` is set | Minimal black end card, no VO: logo + ROTATION, thin rule, a 16:9 slot (x 250-1050, y 400-850 at 1920 scale = x 333-1400, y 533-1133 at 1440p) and a subscribe circle (centre 1470,625, r 150 at 1920 scale). Put YouTube's end-screen video element and subscribe element on them. `{"dur": 8-12, "line": "Watch next", "video": optional title}`. |
| `transitions` | true | Soft push-through (0.3-0.4 s) into every full-screen graphic: last frame of the previous scene scales up and fades while the graphic settles in. Graphic -> footage stays a hard cut. |
| `recent_videos` | 4 | Clip/music recency window. |
| `log_used` | true | Log clips to clips/used.json and tracks to music/used.json (set false for demos). |
| `ending`, `endscreen` | off | Still work if given (v7), but the v8 default ending is `closer` + `endcard`. |

### Scene keys
| Key | What it does |
|---|---|
| `tags` | Words for library picks (e.g. ["container", "port", "cranes"]). A scene with no `clip` gets clips picked from clips/index.json by tag + narration overlap. Named clips still work. |
| `clip` | Optional now. Any clip already used earlier in the video (or a Restricted-licence clip) is replaced automatically by an unused relevant clip; the render log lists `V8 clips: N unique, replaced [...]`. |

### Clip library
- `clipfetch.py` (fetch + index): `python3 clipfetch.py src mixkit,coverr "kw1,kw2" 6`, `python3 clipfetch.py nasa "kw"`, `python3 clipfetch.py stats`. Downloads the highest public resolution (2160p preferred, 1080p minimum, bitrate floor 12 Mbps 2160p / 3.8 Mbps 1080p, horizontal, >= 5 s) into clips/, records source, licence, page, tags, resolution in clips/index.json.
- Mixkit is searched through its public Algolia index (`mixkit_prod_v4`); only `licenseType: free` items are kept. Mixkit *Restricted* = personal/non-commercial only: 14 old clips are flagged `bad` and never used. Coverr (1080p, free licence) and NASA (public domain) are also wired in. Pexels/Pixabay need a free API key (not set up).
- Downloads go through clips/.tmp (not /tmp: the root disk is only ~6 GB).

### Animation (gfx v8, long-form only)
- Map: camera tour (frames each pin as it drops, each route as it draws, then pulls back to frame everything for the counter), slow push while holding, pins pulse, a ship-dot travels each finished route. Routes can be waypoint paths: `{"path": [[lon, lat], ...], "label", "color": [r,g,b], "label_at": 0.45, "label_dx", "label_dy", "dur": 1.8}` (Catmull-Rom smoothed, drawn on with a leading dot). Counter box sits bottom-right.
- Flow: arrows draw with a leading dot, then particles stream along every finished arrow; active node = white box with a soft breathing glow, others near-black with white outline.
- Timeline: a playhead glides to each new event with a white progress line.
- Bars: optional display label per bar `[label, value, "$4.67B"]`. Icons rows allow up to 25 per row (use 25 icons for exact % such as 9/25 = 36 %).
- Easing: quartic ease-out for entrances, cosine in-out for camera moves.
- Render log: `V8 measured (fine metric): longest no-visible-change gap` (>= 0.3 % of pixels changing per 0.5 s) next to the v7 metric.

### Thumbnail (v8)
`make_thumb_long.py` now renders black and white: words white, numbers (or the B side of "A vs B") as black text on a white slab, white bar, grey rule. Same rules for the text (2-4 words, number or contrast, no title repeat).


## Shorts v8 (user 2026-10-30 05:58 IST: "this video is insane yes same for shorts") - SUPERSEDES older Shorts notes
Backups of the v7 Shorts code: `make_story.bak10.py`, `gfx.bak10.py`. Demo: `demo/short_v8.json` -> `out/demo_v8_short.mp4` (Intel Q3 2026 sell-off), preview `out/demo_v8_short_preview.mp4`, stills `out/stills_v8s/`. Daily task replacement text: `daily_prompt_v8.md`.
Locked and unchanged: no top-left logo (never SHOW_BUG), captions Montserrat 700 64 px white, hook_card, outro rules, orange-slab cover.

### Top-level keys (make_story.py)
| Key | Default | What it does |
|---|---|---|
| `v8` | true | Turns on everything below. `false` = exact v7 Shorts behaviour. |
| `theme` | "mono" | Black-and-white graphics via `gfx.set_theme("mono")`: count-up stats white, pills white with dark text (any pill colour is ignored), stickers white, compare/quote/headline cards white/near-black, loc pin white, charts white + greys on near-black. Bar charts with `highlight`: highlighted bar white, the rest mid-grey (`gfx.HL_GREY`, Shorts only). No #F0B400 anywhere. Footage stays in colour. |
| `music` | {"mood": "doc"} | `{"mood": "doc\|tense\|light\|ambient"}` or `{"track": "mk_464"}`. One library track per Short from music/index.json (skips tracks used in the last 4 videos; shared music/used.json with long-form); the track's real ending lands on the last frame. mixbus rules unchanged (-24 dB under voice, HP 130, breathing dips, -14 LUFS, bt709), final fade 1.5 s. music.mp3 is no longer used by Shorts. Log line `V8 music`. |
| `tags` | [] | Story-wide clip tags added to every scene's tags. |
| `outro` | fallback line | Now also `{"text", "tags"}` with no clip: the end shot is picked from the library. |
| `res` | [1080, 1920] | Output size. Footage cropped 9:16 from the source and lanczos-scaled; overlays/charts drawn at 1080x1920 and lanczos-scaled if res is larger. |
| `crf` | 16 | x264 preset faster, high profile, GOP 60, bf 2. |
| `recent_videos` | 4 | Clip recency window for auto-picks (clips/used.json). |
| `log_used` | true | Log clips to clips/used.json and the track to music/used.json (false for demos). |

### Scene keys
| Key | What it does |
|---|---|
| `tags` | 3-5 concrete nouns for library picks. A scene with only `tags` (no `clip`) gets unused library clips (2160p first on equal relevance). |
| `clip` | Optional. Any repeat within the Short, missing, `bad` or restricted-licence clip is replaced by an unused relevant clip (scene's own clips, then tags + narration picks excluding recent videos, then any unused pick; near-black clips skipped). Log: `V8 clips: N unique, replaced [...]`. |

### Look / quality / animation
- Grade: no grain, lighter vignette (long-form v8 grade). Unsharp only on sub-2160 sources (they are upscaled ~2x after the 9:16 crop).
- Eased entrances: cards fade/settle in over 0.4 s, loc pin slides in over 0.35 s, the hook card eases out over its last 0.3 s, charts get the v8 push-through from the previous shot (`gfx.blend_in`). Stats keep the count-up + pop.
- Temp files: env `STORY_WORK=<dir>` keeps a render's scratch files (s*.mp3, o*.png, sc*.mp4, ch*, voice_cut.mp4, music_bed.wav) out of /workspace/work/yt (default unchanged).


## v9 / Study 5 upgrade (user said "fix it" to all 12 Study 5 fixes, 2026-10-30 06:59 IST) - SUPERSEDES anything above for LONG-FORM
Study: /workspace/web/notes/adda395e-a9fe-460a-aeb7-b7f7c467f3e0/study5-cnbc-wsj-vs-ours.md. Backups of the v8 code: `make_long.bak11.py`, `gfx.bak11.py`, `opener.bak11.py`, `mixbus.bak11.py`, `clipfetch.bak11.py`, `musiclib.bak11.py`, `make_story.bak11.py` (make_story/musiclib unchanged). New modules: `v9gfx.py` (overlays), `natlib.py` (ambience library, `nat/`).
Demo: `long/spec_v9_demo.json` -> `out/demo_v9_long.mp4` (Fed holds at 3.75-4%, Oct 28 2026), preview `out/demo_v9_long_preview.mp4`. Smoke test spec: `long/spec_v9_smoke.json`.
Shorts are NOT changed: every v9 behaviour is gated by `v9` in make_long.py; gfx/opener/mixbus defaults keep the Shorts look (FPS 30, no axis, box flow nodes, duck -24 dB, no nat). Re-tested 2026-10-30: demo/short_v9_regress.json renders frame-identical to demo_v8_short.

### Top-level keys (make_long.py)
| Key | Default | What it does |
|---|---|---|
| `v9` | true | Turns on everything below (needs `v8` true). `false` = exact v8. |
| `fps` | 24 | Output frame rate (film cadence of CNBC/WSJ). All graphics are rendered natively at this rate (gfx.FPS / opener.FPS); footage is resampled. |
| `match_min` | 2.0 | Subject-match gate for clip picks (see Footage). |
| `auto_inset` | true | Footage below 1000 px tall or a still photo is shown as a framed inset automatically. |
| `open_place` | - | `{"clip" or "tags", "place": "Washington, D.C.", "date": "Oct. 28, 2026", "text": optional VO, "dur": 3.5 if no text, "nat": [...]}`: first scene = establishing shot of the REAL place (slow push) + WSJ-style dateline tag top-left. Use a clip that really is that place. |
| `title_card` | - | `"Episode title"` or `{"series": "Rotation", "title", "sub", "clip" or "tags", "dur": 3.6}`: replaces the `{"sting": true}` scene (or goes before the question/agenda) with the series title card over footage: logo mark + letter-spaced series name, thin rule, big episode title (Montserrat 900, <= 2 lines), music hit, no VO. Counts as a full-screen graphic. |
| `endcard` | {"dur": 10} | v9: `bg_clip` (default = the `open_place` clip, i.e. the visual bookend) plays dimmed behind the end card; adds "Tell us what you think in the comments" under the logo rule and a 3-column credits band (sources / footage / music & voice) at the bottom. The two YouTube end-screen slots are unchanged (video x 250-1050 / y 400-850, subscribe circle 1470,625 r 150 at 1920 scale). |
| `credits` | true | Credits roll up the right side of the `closer` shot (sources, footage credits incl. every CC-BY attribution, music titles, AI-voice note, real-audio credit) + the end-card band. `false` = off. |
| `voice2` | "en-GB-SoniaNeural" | First quote voice. Each quoted speaker (`quote.who`) gets the next voice from [voice2, en-GB-RyanNeural, en-US-EmmaNeural, en-AU-NatashaNeural], never the narrator (en-US-AndrewMultilingualNeural). `rate2` (default "+6%"). |
| `music_db` | -18 | Music level under the voice (v8 was -24). Music-only stretches still open to -9. |
| `nat` | true | Natural-sound layer on/off. `nat_db` [-22, -13] = level under the voice while it speaks / in VO-free gaps. `nat_default`: ambience id or null used when a scene's tags find nothing. |
| `axis` | true | Line/bar charts get full axes (left y labels, gridlines, ticks, baseline). Per chart `"axis": false` to drop; `"y_label"`, `"axis_decimals"`. |
| `picto` | true | `flow` nodes become pictogram circles (icon auto-picked from the label; set `"icon"` per node to choose). Per flow `"style": "box"` for the old boxes. |
| `texture` | true | Very faint monochrome contour/grain texture over full-screen graphic panels (data/texture_v9.png). |
| `ai_voice_note` | true | Small "QUOTE READ BY AI VOICE" note on quote cards. |

### Scene keys
| Key | What it does |
|---|---|
| `quote` | `{"text", "who", "role", "source", "voice": optional}` - a REAL, sourced quote (copied exactly from a fetched page) read by a second AI voice on a speaker card (big quote, rule, name, role, source bottom-left) over dimmed footage. Optional scene `text` = narrator lead-in read first ("Some economists think the Fed waited too long."). Never invent or paraphrase inside quote marks. |
| `actuality` | `{"clip": id (in clips/index.json, public-domain video with audio) or "file", "ss", "dur", "who", "role", "credit", "source", "show": "inset" or "footage"}` - plays the real speaker (US government hearing / briefing / press conference, NASA...) with a WSJ-style lower third (white name tab, dark role tab, credit). Level-matched to the narrator. Low-res video is shown as an inset automatically. Find exact in/out points with faster-whisper word times + a silence check. |
| `inset` | `true` or `{"dateline": "Place|Date", "credit": "..."}` - footage in a framed inset (70 % width) over a blurred, darkened copy, dateline above the top-left corner, credit under the right corner. Automatic for sub-1000 px and still photos (dateline/credit then come from the clip's index entry). |
| `nat` | ambience id (`natlib.py list`), list of words (["city", "traffic"]), `"clip"` (use the clip's own audio when its index entry has `audio_ok`), or `false`. Default: picked from the scene tags + video tags. One segment per shot (new in-point, ±1 dB) so the bed changes on every cut; silent under full-screen graphics. |
| `fallback_text` / `fallback_sub` | Text for the designed plate used when no clip passes the match gate (default: first keyword, else the stat, else the tags). |
| `tilt` | v9: ignored on data-heavy charts (line > 3 points, bar > 3 bars, `axis`) and on devices; use `"tilt": "force"` for a single-headline graphic. Log: `V9 flat`. |

### Footage: match gate + new free sources (clipfetch.py)
- Gate: `clipfetch.match_score(meta, tags, text)` = distinct unambiguous scene-tag words found in the clip title (1.0) or the source's own tags (1.0; 0.5 if the word is only there because it was our search keyword), ambiguous words (AMBIG stoplist: vessel, container, bank, plant, chip, crane, apple, oil, gas, port, market, stock, rate, power, building, ...) +0.5 only next to an unambiguous hit, narration nouns in the title +0.5 (max 1). A multi-word tag ("gas station", "federal reserve") found as a phrase in the title scores 2.0 on its own; its words alone count half. Stock clips (Mixkit/Coverr) must name the subject in the TITLE or they cap at 1.0, so write tags as phrases where it helps. Extra shots and repeat replacements take, in order: the scene's own unused clips -> a strong library match (>= 2.5) -> holding the previous shot longer (no cut) -> a match >= `match_min` -> a designed plate (textured panel + key phrase); never a random clip. Change-guard splits without a strong match keep the shot whole. Named clips with an explicit in-point ("id@49.4") skip the dark-clip swap. Clips named anywhere in the spec are reserved for their own scene. Named clips are trusted but scored. Log: `V9 pick scene N: id score S (named/auto/replace/split/fallback-plate) title` and `V9 weak named clips`.
- `python3 clipfetch.py match "tag1,tag2" ["narration"]` lists the best matches with scores - use it before naming clips.
- Wikimedia Commons (PD / CC0 / CC BY only; BY-SA, NC, ND skipped; artist + licence stored as `attribution` for the credits): `python3 clipfetch.py wikimedia "kw1,kw2" 3 video|image`, or one exact file: `python3 clipfetch.py url "https://commons.wikimedia.org/wiki/File:<name>"`. Photos become 10 s 1080p clips with a slow push (`still: true`, auto-inset). Long videos keep the first 60 s.
- DVIDS (US military / government, public domain): site search and API are walled (HTTP 202 bot wall; API needs a key), so find a page with web_search (`dvidshub video <place/topic> B-roll`) and run `python3 clipfetch.py url "https://www.dvidshub.net/video/<id>/<slug>"`. Stores videographer credit, place + date (dateline), `audio_ok`.
- NASA (public domain) as before: `python3 clipfetch.py nasa "kw"`.
- US government video (e.g. Federal Reserve press conferences, public domain per federalreserve.gov/disclaimer.htm): download, then `clipfetch.add_local(cid, path, "fed"|"usgov", clipfetch.LIC_V9[...], page, title, tags, attribution=..., dateline="Place|Date", audio_ok=True, extra={"credit": ...})`. The Fed's player is Brightcove: policy key in players.brightcove.net/66043936001/default_default/index.min.js, sources via edge.api.brightcove.com/playback/v1/accounts/66043936001/videos/<data-video-id> (960x540 max).
- Google Earth Studio: NOT integrated. Its terms allow online video use with on-screen "Google Earth" attribution, but it needs a signed-in Chrome web app and manual export, so it cannot run in this pipeline (checked 2026-10-30).

### Audio
mixbus v9 (long-form only): music -18 dB under the voice (was -24); `nat` layer from natlib (Mixkit SFX free licence, 23 ambiences in nat/index.json: city traffic, urban day/night, office, restaurant crowd, sea waves, harbor, wind, birds, park, industrial hum, rain, airport/plane, train station, construction; no press-room/conference ambience exists on Mixkit yet) -22 dB under the voice, -13 dB in VO-free gaps, high-passed 80 Hz, 120 ms crossfades at cuts. Still -14 LUFS, HP 130 Hz music, breathing dips, voice contour.

### Render log (new lines)
`V9 graphics: full-screen X s of Y s = Z%` (+ list) and `V9 WARN` above 30 %; `V9 cold open: N s before the title card, voices [..]` (+ WARN outside 75-100 s or < 3 voices); `V9 voice relief: longest stretch without a non-narrator voice`; `V9 nat: segments, sources`; `V9 pick ...`; `V9 flat ...`.

### v9 script rules (long-form)
- Cold open 75-100 s (replaces 45-75 s): open on the real place (`open_place`, VO from frame 1 with the news + contrast), first graphic by ~0:15, at least 3 voices before the title card (narrator + 1-2 `quote` voices + public-domain `actuality` where it exists), stakes, and END on a human or emotional line (a real quote or real audio), then the `title_card`.
- A new voice every 30-60 s through the video (quote voices, actuality). Quotes: real, copied exactly from a fetched source, credited on screen; never invent, merge or "tidy" a quote.
- Full-screen graphics 20-30 % of the runtime (title card, charts, map, flow, icons, plates); prefer a stat or keyword over matching footage to a full-screen panel. One plotted chart per chapter, flat with axes.
- Footage must literally show the sentence's subject (match gate); use insets + datelines for archival / PD / low-res material; open and close on the real place.
- End: `closer` over one strong shot (credits roll on the right), then the 10 s end card over the opening place.

## Shorts v9 (user 2026-10-30 08:56 IST: "yes same extra voice and background in the short too") - SUPERSEDES older Shorts audio notes
Backups of the v8 Shorts code: `make_story.bak12.py`, `gfx.bak12.py`, `mixbus.bak12.py`, `natlib.bak12.py`, `v9gfx.bak12.py`, `make_long.bak12.py` (make_long only now takes `VOICE2` from v9gfx). Demo: `demo/short_v9.json` -> `out/demo_v9_short.mp4` (Fed holds at 3.75-4 %, Oct 28 2026; Warsh actuality + Ethan Harris quote), preview `out/demo_v9_short_preview.mp4`, stills `out/stills_v9s/`. Regression: `demo/short_v9s_regress.json` (= short_v8 spec) -> `out/v9s_regress_short.mp4`. Daily task replacement text: `daily_prompt_v9.md`.
Locked and unchanged: 1080x1920 30 fps, B/W graphics, no yellow, no top-left logo, captions Montserrat 700 64 px white at y 1360, hook_card, outro rules, orange-slab cover. Shared code: `v9gfx.QuoteVoices` / `VOICE2` (voice pool, also used by make_long), `v9gfx.quote_png_v` / `lower_third_png_v` (vertical cards), `natlib.for_scene` + `natlib.build` (nat bed), `mixbus.actuality_wav` (real-audio cut + level match), `mixbus.mix(duck_db, nat, nat_db)`, `mixbus.phone_check`.

### Top-level keys (make_story.py)
| Key | Default | What it does |
|---|---|---|
| `v9` | true | Turns on everything below (needs `v8`). `false` = exact v8 Shorts (music -24 dB, no nat, no quote/actuality scenes). |
| `music_db` | -18 | Music level under the voice (v8 Shorts: -24). Music-only gaps still open to -9. |
| `nat` | true | Natural-sound layer on/off. `nat_db` [-22, -13] = under the voice while it speaks / in VO-free gaps. `nat_default`: ambience id used when a scene's words find nothing. |
| `voice2` | "en-GB-SoniaNeural" | First quote voice; later speakers get the next of en-GB-RyanNeural, en-US-EmmaNeural, en-AU-NatashaNeural (never the narrator en-US-AndrewMultilingualNeural). Per-quote `voice` overrides (match the speaker: men en-GB-RyanNeural / en-AU-WilliamNeural, women en-GB-SoniaNeural / en-US-EmmaNeural). `rate2` default "+12%". |
| `ai_voice_note` | true | "QUOTE READ BY AI VOICE" tag on the speaker card. |
| `sources` | - | Free list of source URLs (for the description; not drawn). |

### Scene keys
| Key | What it does |
|---|---|
| `quote` | `{"text", "who", "role", "source", "voice"}` - a REAL quote copied exactly from a fetched page, read by its own AI voice. Optional scene `text` = narrator lead-in read first (0.3 s gap). Card (`v9gfx.quote_png_v`): footage dimmed + centre band darkened, big quote mark, name (76 px), role, rule, "Source: ...", boxed "QUOTE READ BY AI VOICE" (block y ~520-1250). The quote words run in the captions with curly quotes; captions never straddle the lead-in/quote boundary. Soft whoosh at the card. Footage = the scene's `clip`/`tags` as usual. |
| `actuality` | `{"clip", "ss", "dur", "who", "role", "credit", "source", "text", "words_json", "gain_db", "show"}` - public-domain real audio + its own video at the same in-point, one shot, blur-fill (sharp 16:9 band y 626-1294 over a blurred copy; `"show": "crop"` for a 9:16 crop instead). Audio band-limited 90 Hz-9 kHz and level-matched to the earlier narrator scenes; no emphasis contour, no nat. Lower third (`v9gfx.lower_third_png_v`): white name tab + dark role tab inside the band bottom-left; source (white) + credit (grey caps) above the band. Captions = `text` (the exact words, verified by whisper); timing from `words_json` (faster-whisper words of the source file, absolute seconds) when the word count matches, else spread evenly. |
| `nat` | Same as long-form: ambience id (`python3 natlib.py list`), word list (["city","traffic"], ["office"], ["airport"]...), `"clip"` (clip's own audio when `audio_ok`), or `false`. Default from scene tags + video tags. One segment per shot (new in-point, +/-1 dB), 120 ms crossfades, silent under charts and actuality. The outro dict may carry `nat`. |

### Rules
- 1-2 extra voices per Short (60-90 s): real quotes / real public-domain audio only; first one by ~40 % of the runtime; never as the first scene.
- Captions: v9 adds a soft dark halo behind the caption line (same font, size, position) and splits caption chunks at sentence ends.

### Render log (new lines)
`V9 nat: N segments, sources [...]`; `AUDIO ... duck -18.0 dB, nat on ... final I -14.0 LUFS`; `PHONE CHECK (300 Hz-7 kHz band, integrated): voice / music / nat, voice_over_music_dB, voice_over_nat_dB` (target ~12-18 dB over music, ~15-22 dB over nat); `V9 voices: N [...]`.


### Long-form thumbnail: collage style (LOCKED 2026-10-30, replaces v7/v8 make_thumb_long.py)
User rejected WSJ split (font too WSJ) and Bloomberg type-slab; locked the Bloomberg-Originals-inspired collage with own fonts.
`PYTHONPATH=/workspace/work/pylib python3 make_thumb_collage.py '{json}'`. Keys: subject (frame png or RGBA cutout; rembg u2net_human_seg auto), bg (place photo -> blue duotone, "tint" [r,g,b], "blur", "bgfx"), words (2-3, title case, Poppins ExtraBold white), text_x/text_y/text_w, subj_x/subj_h/subj_dy, disc (bool)/disc_r (orange #FA4E02), arrow {pts, w, color}, props [{img, h, x, y, rot, front}], logo_h, out. Demo covers/thumb_collage_fed2.jpg. rembg installed in /workspace/work/pylib.


## Rotation Explains (new series, demo 2026-10-30) - separate renderer, nothing above changes
New files only: `make_explain.py` (renderer) + `explain_gfx.py` (graphics). No locked file was edited (make_long, make_story, gfx, v9gfx, opener, mixbus untouched; make_explain only imports mixbus.mix / musiclib.build_bed / natlib.build / v9gfx.endcard_frames read-only).
Run: `cd /workspace/work/yt && PYTHONPATH=/workspace/work/pylib python3 make_explain.py long/spec_explain_demo.json` (background it; ~20 min for 3.5 min at 1440p on 2 cores). Env: `DRY=1` timeline + cue check only; `ONLY=3,4` re-render those segments (others reused if present); `STRICT_ONLY=1` with ONLY = render just those, no concat; `DEBUG=1` prints ffmpeg commands. Scratch: explain/work/ (seg_XX.mp4, voice.wav, music_bed.wav, nat_bed.wav, render_meta.json), TTS cache explain/tts/.
Demo: `long/spec_explain_demo.json` -> `out/demo_explain.mp4` (preview `out/demo_explain_preview.mp4`, sheet `out/demo_explain_sheet.jpg`, thumbnail `covers/thumb_explain_demo.jpg`). Topic: Alphabet Q3 2026.
Look: brand orange #FA4E02 as the only accent on cream #F8F1E4 / off-white #FAF7F2, near-black #111 text, Poppins ExtraBold/SemiBold + Montserrat; no yellow, no serif. Drawn natively at 2560x1440, 24 fps, eased (quartic out / cubic in-out / back-out pops), hard cuts.
Shape (condensed 8-9 min episode): cold open with the news + headline card + one shock number -> doc zoom of the real filing line -> "In this video we'll explain..." (agenda overlay) -> "The short version" verdict card by ~0:40 -> series title card -> 3 numbered sections (section header card each) -> bears vs bulls ("you be the judge") -> catalyst line -> one zoom-out closer -> v9 end card (10 s). Real quotes only, each speaker its own AI voice.

### Top-level keys
| Key | What it does |
|---|---|
| `output`, `fps` (24), `crf` (15) | Output path / rate / x264 quality (preset faster). Size is fixed 2560x1440. |
| `rate` ("+16%") / `rate2` ("+6%") | Narrator (en-US-AndrewMultilingualNeural) / quote-voice speaking rates. +16% lands ~170 wpm of speech. |
| `music_db` (-18), `nat_db` ([-22,-13]) | Passed to mixbus.mix (music under voice; nat under voice / in gaps). -14 LUFS master as v9. |
| `music_tracks` | Optional {mood: track_id} force for musiclib.build_bed. Moods come from scene `music` keys. |
| `endcard_bg` | Clip allowed to repeat (end card bookend over the opening shot). |
| `title`, `series`, `sources` | Metadata for the description (not drawn except via the title scene). |

### Scene keys (every scene)
| Key | What it does |
|---|---|
| `kind` | footage, closer, doc, bars, keyword, split, tiles, flow, section, title, verdict, quote, endcard. |
| `text` | Narration (narrator voice). Scene length = voice + `pre` (0.15) + `post` (0.3), or `dur` for VO-free cards (section 1.6, title 3.3, endcard 10); `min` floor. |
| `quote` | {text, who, role, source, voice}: REAL quote copied exactly from a fetched source, read by its own voice after the narrator lead-in (`text`). Quote card = `kind: quote` + `bg` clip. |
| `cues` | Timing of build steps: a word from the narration ("51.4", "Three#2" = 2nd occurrence), seconds (number) or "q" (quote start). Doc uses a dict {hl, ring, callout}. |
| `shots` | Footage: ["clip_id", "clip_id@in_point"]; cuts snap to word gaps near equal splits (2.5-4 s each). Every clip once per video. CC BY stills get an automatic "Photo: Artist / Wikimedia Commons, CC BY x" credit. |
| `bg`, `darken` | Footage under an overlay device (keyword, verdict, flow, quote, title); darken 0-0.3. |
| `overlays` | Over footage: `headline` {outlet, date, text, credit, out}, `pops` {items [[text, sub, hold_s]]}, `lower` {who, role} (exec name card, no photo unless openly licensed), `stat` {value, num, prefix, suffix, label}, `agenda` {items}; each with `cues`. |
| `music` | Mood (doc / tense / light / ambient) starting at this scene (crossfade). |
| `nat` | Ambience words for natlib (["office"], ["city","traffic"], ["industrial","hum"], ["construction"], ["wind"]). Silent under opaque graphics. |
| `sheet` | Scene-local times to grab for the contact sheet. |

### Devices (`gfx` dict)
| kind | gfx keys |
|---|---|
| `doc` | page_png (pdftoppm -r 300 of the real filing page), bbox_html (pdftotext -bbox of that page), target (exact token, e.g. "(51,355)"), extra_rings [tokens on the same row], anchor left/right/center, crop_w [start_pt, end_pt] (slow push), callout ("line 1\nline 2"), title, source, thumb_label, page_no. Whole-page thumbnail stack left with orange viewfinder + magnifier intro, zoomed page right, orange multiply highlight sweeps the row (rest of page veiled), hand-drawn orange ring(s), curved arrow + caps callout, black footer (title left, source right). |
| `bars` | title, bars [[label, value, display]], ymax, ystep, prefix, suffix, highlight (default last = orange, others near-black), annot {text} (arc + orange pill), source. Bars rise one per cue, values pop. |
| `keyword` | word, sub: huge cream word on orange (90 % over `bg` footage), caps sub-line on cue. |
| `split` | tag, left {label, pct}, right {label, pct}, source: orange share slides to its real proportion, percentages count up per cue. |
| `tiles` | title, tiles [{name, desc, vlabel, value, delta, neg}], stamp {tile, text, cue}, unfocus (cue word), ftitle, source: numbered tiles fill one by one, others dim, stamp slams on. |
| `flow` | title, nodes [{icon cash/server/down/up/chip/building/search/cloud/car, label, value, accent}], ops ["−", "="], source: white circles + drawn icons over darkened footage, curved arrows with operator badges. |
| `section` | num, text: caps header on dark, orange number badge + rule. |
| `verdict` | tag ("The short version"), lines (one per cue). |
| `title` | series ("Rotation Explains"), title: logo + letter-spaced series name, orange rule, big title over dimmed `bg`. |
| `endcard` (scene) | gfx {line, video}, credits [[heading, text] x3], bg: v9 end card (same YouTube slots) scaled to 1440p. |

### Render log
`TIMELINE`, per-segment times, `CLIPS n unique; repeats []; shots avg/min/max`, `GRAPHICS ... % (target 45-50%)`, `MUSIC`, mixbus `AUDIO ... final I -14 LUFS`, `PHONE CHECK`, `DONE`.

## Orange accent (2026-10-30, user: "yeah orange accents there too") - long-form v9 AND Shorts v9
Supersedes every "black-and-white only / pass no colours" line above and in task prompts. The look is still mono (white/greys on near-black, no yellow, no top-left logo) plus ONE brand-orange accent #FA4E02, applied automatically:
highlighted bar, first line series + end dot, stat count-up numbers, numbers inside keyword pops, map routes/pins/highlighted land, flow arrows/active node rings, timeline current event, icon fills, opener/agenda accent bars, punch-word numbers.
- spec "accent": "#FA4E02" (default) | any "#RRGGBB" | null/false = pure black-and-white (old v9).
- Code: gfx.set_theme("mono", accent) sets YEL/ORG/FILL/HLC/PAL[0]; opener.set_theme("mono", accent); make_long/make_story `_accent(spec)`. Backups *.bak13.py (pre-accent).
- Do not pass other colours. Shorts cover (orange slab) and collage thumbnails unchanged. Rotation Explains (make_explain.py) already uses orange on cream.

## Thumbnail layouts (2026-10-30, user: "don't repeat long-form video cover design, new cover each video") - weekend + Rotation Explains
Supersedes "collage only" lines. Tool: `PYTHONPATH=/workspace/work/pylib U2NET_HOME=/workspace/work/u2net python3 make_thumb_layouts.py '{json}'` (1280x720 JPG).
- "layout": "auto" (default) = one of collage/stack/slab/ui/grid/ring NOT used in the last 4 long videos (covers/cover_log.json); duotone "tint" auto-changes from the last one. Deterministic per title, so test with "log": false, then render the final once with "log": true (default) so the log records it.
- Common: subject (frame png or RGBA cut-out; isnet auto cut), out, title, words (2-4, must NOT repeat the title), subj_x, subj_h, subj_dy, flip, kicker (small caps chip, e.g. "Rotation Explains"), tint, logo_h, grain.
- collage: bg (place photo), words title-case, disc_r, arrow, props (same keys as make_thumb_collage.py).
- stack: orange band + stacked caps words (last on black slab) + dark line chart: chart [values], value ("-$9.1B" slab at the end point). Leave out years if the subject covers them.
- slab: bg, number (big, black on white slab), chip (orange label), bar_label, direction "down"|"up", words (one short caps line).
- ui: bg, brand (company name as text, no logo file), ui_hint, question (provocative line in a search/chat box), words (orange caps).
- grid: tiles [names the story touches, up to 9], words, slab_i (word on orange slab), kicker.
- ring: brand (wordmark on white slab inside rings), words, slab_i, kicker.
Reference sheet: covers/layouts/sheet.jpg (Pichai demo of all six). Always view the JPG; words never over the face, nothing clipped.

## Shorts covers (2026-10-30, user: "design new cover each short video")
make_story.py now builds the cover with make_short_covers.py: 6 layouts (slab, topbar, number, split, frame, bold), auto-picks one not used in the last 4 Shorts (covers/short_cover_log.json). Spec key "cover": {"layout": "auto", "words": [2-4 punchy words, NOT the title], "number": one real verified number like "-$42.4B", "kicker": company/place}. Without "cover" it falls back to the title. Log line: "cover <path> layout <name>". Reference sheet covers/short_layouts/sheet.jpg. Orange/cream/black only.

## Light palette C (2026-10-30, user: "use c"; Shorts added "yes shorts same") - long-form (make_long.py) AND Shorts (make_story.py) DEFAULT
Supersedes "black-and-white graphics" for long-form full-screen graphics. Full-screen charts, maps, flows, timelines, icon counts and morph bars now draw on CREAM #F8F1E4 with ink #111 text, brand ORANGE #FA4E02 as the lead colour and COBALT #1F4FD8 as the partner (comparison series, non-highlighted bars, playheads/particles, pictogram circles). Never yellow.
- spec "theme": "light" (default) | "mono" (old dark mono + orange accent). "accent" still sets the lead colour.
- Overlays on footage (keyword pops, punch words, loc tags, end screen), the logo sting, question card, agenda, title/quote cards and end card stay as before (white text on footage, dark cards).
- Bars: highlighted bar orange, others cobalt; with no highlight the last bar is orange. Line charts: series 1 orange, series 2 cobalt.
- Code: gfx.set_theme("light", accent) after set_theme("mono", accent); globals OV (overlay white), HI, BAR, BOX, MAPSRC, PIC_ON/OFF, TL_DIM. Backups gfx.bak14.py, make_long.bak14.py. Test sheet covers/palettes/light_c_long.jpg.
- Shorts and Rotation Explains unchanged.

## UPLOAD FIX (2026-10-31, supersedes the upload step's session name and file in every task prompt)
- Long-form uploads of 150-900 MB crashed the YouTube Studio tab in session "youtube-rotationnews" (4 times). What worked: a FRESH browser session "youtube-rotationnews-2" + a 1080p ~90 MB upload copy:
  ffmpeg -i <final>.mp4 -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset fast -b:v 1250k -maxrate 1500k -bufsize 3000k -r 24 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart /tmp/up.mp4 && cp /tmp/up.mp4 out/<name>_90.mp4 (write to /tmp first; writing straight to /workspace failed once)
- Paste the description TEXT into the browser task's context (the browser cannot read workspace .txt files); thumbnail/video files by absolute path are fine.
- If session youtube-rotationnews-2 crashes too, retry in a new session name (youtube-rotationnews-3, ...).

## Shorts covers OFF (2026-10-31)
User: "don't use cover on shorts". No "cover" key in Shorts specs, no custom thumbnail upload; YouTube default frame. Supersedes "Shorts covers" section above.

## Viewer-review rules (2026-10-31)
Long videos (weekend + Explains) follow rotation-video-craft "Feedback rules": price vs fair-value line chart when a premium exists, animated route/chokepoint map with ship-dots, macro-to-micro flow chain, one sourced opposing view, plain one-line jargon explanations.
