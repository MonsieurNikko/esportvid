# esport-studio

Faceless esports / gaming shorts in one fixed house style:
**3D stage intro** (hero under a spotlight, opponents, 3D titles, team line-up) → **tactical radar** of the play
(kill feed, HP, clock, heartbeat) → **clue / cards / predict** → **reveal**, with Kokoro narration, voice-synced captions
and synthesized sound. 1080×1920, 30 fps, 65–90 s (TikTok Creator Rewards needs > 1 min).

Formats: `guess_the_pro` · `play_that_changed` · `esports_scandals` · `predict_the_round` · `top3` (see `formats/`).
Games: `cs` · `valorant` · `lol` · `overwatch` (see `games/`).

## Setup (once)
```
git clone https://github.com/MonsieurNikko/esportvid.git
cd esportvid
python setup.py            # deps, headless Chromium, Kokoro voice model, ffmpeg check
```
Windows needs ffmpeg in PATH: `winget install --id Gyan.FFmpeg -e` (then open a new terminal).

## Make an episode
```
mkdir episodes\02_coldzera && copy examples\guess_the_pro_kennys\spec.json episodes\02_coldzera\
# edit spec.json (docs/spec_schema.md)
python -m engine.cli timeline episodes\02_coldzera\spec.json          # voice + timing check
python -m engine.cli build episodes\02_coldzera\spec.json --stills 2,15,40,70   # preview frames
python -m engine.cli build episodes\02_coldzera\spec.json            # full render -> mp4 + publish.md
```

## Layout
| path | what |
|---|---|
| `engine/style.py` | the locked house style (palette, fonts, captions, chips) — do not change per episode |
| `engine/voice.py` | Kokoro narration (speed 1.0, cached per line) |
| `engine/timeline.py` | voice-driven timeline, time refs like `B8+0.8` |
| `engine/web/stage.html` + `engine/stage.py` | 3D intro (three.js in headless Chromium) |
| `engine/radar.py` | top-down radar renderer |
| `engine/compose.py` | compositor, captions, transitions, parallel render |
| `engine/audio.py` | synthesized score + SFX + ducking |
| `engine/publish.py` | titles / description / hashtags / checklist |

Licences: code MIT-style for personal use; fonts OFL/DejaVu (see `fonts/`); three.js MIT; Kokoro Apache-2.0.
