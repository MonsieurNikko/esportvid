# spec.json reference

One `spec.json` = one episode. The engine never needs code changes for a new clip: everything is data.
Start from `examples/guess_the_pro_kennys/spec.json` and edit.

## Time references
Visual events are written relative to narration lines, never in absolute seconds:
`"B8"` (line start) · `"B8.end"` (line end) · `"B8+0.8"` / `"B8-0.3"` (offset) · `"@start+0.6"` / `"@end-1"` (section bounds).
The timeline is built from the measured voice durations, so if a line gets longer, everything after it moves with it.

## channel.json (not in the spec)
`{"handle": "@name", "name": "Channel"}` in the episode folder, the engine folder or `~/.esportvid/`. The handle is the
watermark (bottom-left of the panel). Missing → no watermark + a warning; `@yourchannel` is a placeholder to replace.

## meta
| key | meaning |
|---|---|
| `format` | `guess_the_pro`, `play_that_changed`, `esports_scandals`, `predict_the_round`, `top3` |
| `game` | file in `games/` (`cs`, `valorant`, `lol`, `overwatch`) |
| `series`, `episode` | used for file names, publish kit and episode index (nothing is drawn on screen) |
| `mood` | `default` (orange accent) or `dark` (red accent, unease drone — scandals) |
| `out` | output file name (no extension) |
| `highlight` | `{word: colour}` for captions (player names in team colour, `Kyiv` in gold…) |
| `base_hashtags` | always added to the publish kit |

`game_overrides` (top level) can swap colours, e.g. `{"hero_color": "ct", "opp_color": "t"}` when the hero is a CT.
Colours: names `t`, `ct`, `red`, `blue`, `gold`, `white`, `gray` or `[r, g, b]`.

## lines (narration)
`{"id": "B8", "say": "Get Right. Headshot.", "cap": "GeT_RiGhT. Headshot.", "gap": 0.9, "role": null}`
- `say` = what Kokoro reads (spell names/numbers the way they are spoken). `cap` = caption text (defaults to `say`).
- `gap` = silence before the line (radar default 0.9 s, others 0.15–0.3 s). Use gaps to let the action breathe.
- `role`: `punch` (big text instead of caption, cold open) · `big` (clue reveal moment) · `question` / `answer` / `cta` (reveal).
- Voice rules: no line starting with "…", no one-word lines ("And friberg." not "friberg."), ≤ 12 words per line.

## sections (in order)
| type | what it shows | keys |
|---|---|---|
| `cold_open` | 3D hero under a spotlight, opponents appearing in the fog, 3D title | `enemies` (int), `title3d`, `title_color`, `punch_text`, `you_label` (default `YOU`, empty = hidden), `lines` |
| `rewind` | 0.5 s tape-rewind effect back to the context | – |
| `context` | 3D beats, one after the other | `beats`: list of beats (below) |
| `radar` | top-down map with the action | see below |
| `cards` | 2D kinetic headline cards (aftermath, story steps, top-3 titles) | `cards`: `[{kicker, headline, sub, color, hold, lines}]` |
| `predict` | freezes the previous radar, "WHO WINS?" + 2 options + 3-2-1 | `question`, `options: [{label, color}]`, `lines` |
| `clue` | last clue, big text on the `role: big` line | `label`, `big`, `lines` |
| `reveal` | "SO… WHO ARE YOU?", 3-2-1, answer with flash | `question`, `answer`, `answer_sub`, `prompt`, `cta1`, `cta2`, `lines` |

### context beats
| kind | 3D content | keys |
|---|---|---|
| `score` | floating score + sub line behind the hero | `text3d`, `sub3d`, `color`, `chip`, `chip_color`, `lines` |
| `lineup` | opponents lined up with name labels | `names`, `long_gun` (names holding a sniper), `color`, `chip`, `facts` (strings or `{text, at}`), `lines` |
| `title` | big golden word (stakes: KYIV, MAJOR, $1,000,000) | `text3d`, `color`, `chip`, `lines` |
| `alarm` | red alarm, ghosts behind the hero, then camera rises into the radar | `text3d`, `color`, `chip`, `lines` |

### radar
```
"map": {"transform": {"x0":600,"y0":450,"sx":190,"sy":470,"k":2.0}, "title": "...",
        "lanes": [[x0,y0,x1,y1],...], "sunny": [...], "covered": [...], "walls": [[[x,y],...]], "clip": true, "zones": [{"rect":[...],"label":"A"}],
        "crates": [...], "containers": [...], "pillars": [[x,y],...], "labels": [["LONG A", x, y, angle, size], ...]},
"score": {"left","right","before","after","sub","change_at"},
"hud": {"from": ref, "hp": 50, "armor_text": "ARMOR 0", "clock": [[ref, seconds], ...]},
"duel_from": ref, "heartbeat": [ref, ref],
"you":   [{"pts": [[x,y],...], "from": ref, "to": ref}, ...],
"mates": [{"pts": [...], "from": ref, "to": ref, "die": ref, "carrier": true}],
"enemies": [{"name","appear","entry":[x,y],"final":[x,y],"move_from","arrive"(optional),"label_side":"u|d|l|r","tag",
             "path": [{"pts","from","to"}] (optional: multi-step moves, replaces entry→final; last point = death position, final ignored)}],
"events": [{"type":"kill","at":ref,"victim","weapon","tag":"WALL|HS|null"}, {"type":"shot","at","to":[x,y],"weapon"},
           {"type":"cast","at","by":"hero|<enemy>","label","from","to"}, {"type":"shadow","at","until","by","pos"},
           {"type":"aoe","at","by","pos":[[x,y],...],"r"}, {"type":"line","at","by","from","to"},   // abilities; kill takes "from" too
           {"type":"hit","at","hp"}, {"type":"pickup","at","pos":[x,y]}],
"stats": {"at": ref, "items": [{"big","label"},{"big","label"}], "note", "banner", "banner_at"},
"trackers": [{"name","by","hp":[[ref,pct],...],"items":[["R",used_ref,(off_ref)],...]}],   // spell + HP rows, replaces the kill counter
"hero_label": "???", "you_label": "YOU",   // names shown in the kill feed / on the hero dot
"lead": 1.4, "tail": 0.6, "gap": 0.9,     // timing of the section
"scene": "s1"   // two radar sections with the same scene share one clock (predict format)
```
Coordinates are pixels of the radar image you traced (e.g. a 1000×1000 callout map). `transform` maps them to the screen:
`screen = (sx + (x - x0) * k, sy + (y - y0) * k)`. With `k = 2` a 440 px wide area fills the panel; pick `x0, y0` so the
action area sits inside the panel (x 70–1010, y 466–1346).
