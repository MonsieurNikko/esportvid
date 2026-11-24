---
name: esport-studio
description: Make faceless esports/gaming shorts in Duy's fixed house style (3D intro + tactical radar + voice) from a clip analysis — Guess the Pro, Play That Changed, Scandals, Predict, Top 3.
---

# esport-studio

Turns a pro play (CS2 / CS:GO / VALORANT / LoL / Overwatch) into a 65–90 s vertical short for TikTok, YouTube Shorts and Reels,
always in the same channel style. Everything is automated by one engine driven by a `spec.json`.
Engine repo: `https://github.com/MonsieurNikko/esportvid` (private). On Windows it lives in `%USERPROFILE%\esportvid`.

## Sub-skills (what the user can ask)
| ask | do |
|---|---|
| "new episode / fais une vidéo sur <clip>" (+ format) | the full pipeline below |
| "ideas / idées" | propose 5 subjects for the chosen format and game, with why each will hook (stakes, fame, controversy) |
| "research <moment>" | steps 1–2 only: brief.md with sourced facts |
| "script" | step 3 only: lines with timing intent, ready for review |
| "render" / "preview" | steps 5–6 on an existing spec |
| "publish kit" | titles, description, hashtags, pinned comment from `publish.md` |
| "fix the voice at 0:42" | find the line at that time in `build/timeline.txt`, rewrite its `say`, rebuild (only that line is re-synthesized) |

Formats (read the guide before writing the script): `formats/guess_the_pro.md`, `formats/play_that_changed.md`,
`formats/esports_scandals.md`, `formats/predict_the_round.md`, `formats/top3.md`. Default = Guess the Pro.

## 0. Setup (first time, or if the folder is missing)
```
cd %USERPROFILE%
git clone https://github.com/MonsieurNikko/esportvid.git
cd esportvid && python setup.py --gpu
```
Otherwise `git pull` in the folder. Needs Python 3.10+, ffmpeg in PATH (`winget install --id Gyan.FFmpeg -e`), Node not required.

## Pipeline
1. **Ingest.** Input is a clip URL, the user's analysis (fiche), or both. If only a URL: use the `/watch` skill (claude-video)
   to extract frames + transcript, then write the analysis: event, date, stage, teams/rosters, map (+ version), score and round,
   positions, every kill in order (killer, victim, weapon, HS/wallbang), HP changes, objective, outcome, what it changed.
2. **Research and fact-check** with the sources in `games/<game>.json` (`sources_hint`). Every claim the video makes must have a
   source; write them in `episodes/<NN>_<slug>/brief.md` and later in `spec.sources`. Ambiguous points are narrated vaguely or cut
   ("two shots, no kill" — not "two misses" if the victim was damaged). Stakes must be exact (series vs map vs round).
   Find the **map radar** (callout map of the version played at the time). If you cannot get an image, ask the user for one.
3. **Script** from the format guide: second person "you" (Guess the Pro / Predict) or third person (Play That Changed /
   Scandals), ≤ 12 words per line, one idea per line, 65–90 s total. `say` = spoken spelling ("Get Right", "Forest",
   "sixteen to fourteen"), `cap` = written form ("GeT_RiGhT", "16–14"). Never a one-word line, never a line starting with "…".
   **Direct the voice** on every line (`docs/voice.md`): `emo` (calm/serious/tense/excited/shock/hype) and optional `intensity`
   0–1, plus at most one reaction tag like `[sigh]` or `[gasp]` where a human narrator would react. Rising intensity across
   the kills, `tense` before the reveal, `hype` on the answer. The user can edit these fields directly.
   Show the script (with emo/intensity) to the user before rendering when they are present.
4. **Spec.** Copy the closest example (`examples/*/spec.json`) into `episodes/<NN>_<slug>/spec.json` and edit it
   (reference: `docs/spec_schema.md`). Trace the radar: lanes, covered areas, bomb/objective zones, crates, labels in the
   radar image's pixel coordinates, then set `map.transform` so the action fills the panel. All event times are refs to
   lines (`"B8+0.8"`), never absolute seconds.
5. **Check timing and look:**
   `python -m engine.cli timeline episodes\<ep>\spec.json` → total must be **> 61 s** (TikTok Creator Rewards); adjust `gap`/`hold`.
   `python -m engine.cli build episodes\<ep>\spec.json --stills 2,8,15,30,45,60,70` → open the stills, check: nothing cropped,
   no text over text, names readable, kill feed correct, captions on ≤ 2 lines. Fix the spec, repeat.
6. **Render:** `python -m engine.cli build episodes\<ep>\spec.json` → `<out>.mp4` + `publish.md` in the episode folder.
   Voice-only tweaks afterwards: edit the lines, then `... build spec.json --audio-only` (re-mixes without re-rendering frames).
7. **Deliver:** the mp4, the publish kit (2–3 titles "[what happened] [game]", description with a question, hashtags, pinned
   comment), and the sources. Update `episodes/index.md` (number, subject, format, game, date) so episode numbers never repeat.

## Locked style (do not change per episode)
`engine/style.py` (palette, Anton/Inter fonts, caption look, chips), the series tag on top, the 3D stage look, the radar look,
the signature score "theme C" (`engine/music.py`: same A-minor bell motif in every video, logo sting at 0 s, build in the
context, full theme in the action, 0.4 s silence then the motif on the reveal, hard cut that loops), music ~15–20 % of the voice,
voice engine Chatterbox (`python setup.py --gpu`) with Kokoro fallback. A new idea = a new spec or a new format guide, not new
colours. If the user asks for a style change, change it in the engine for every future episode and say so.

## Platform and monetization rules
- > 61 s for TikTok Creator Rewards; 1080×1920; first 2 s = the most striking moment (cold open), question asked in the first second.
- Original animation only: never broadcast footage, stream VODs or casters' audio (Content ID + "reused content" policies).
- Each episode must carry real research and a story (YouTube demonetizes generic, repetitive, mass-produced videos).
- The 3D/radar is not realistic AI imagery → TikTok AI label not needed; turn it on if realistic AI visuals are ever added.
- Scandals: documented facts and official rulings only, neutral wording, sources listed.
- Comment prompts: guess before the reveal, predict before the freeze, "fair or not?" for scandals.

## Troubleshooting
- 3D stage black or slow on Windows: `set ESPORT_CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe` and retry.
- `ffmpeg not found`: install it and open a new terminal.
- Voice sounds odd on a line: rewrite that `say` (shorter, no ellipsis, names spelled phonetically) and rebuild.
- `[voice check] … words/s` warning: listen to that line, it may be glitched.
