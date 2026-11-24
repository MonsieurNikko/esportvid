# Voice: engines and emotion control

## Choose the engine (spec.voice)
```json
"voice": {"engine": "auto", "ref": "kokoro:am_fenrir"}
```
| key | values |
|---|---|
| `engine` | `auto` (Chatterbox if installed + CUDA, else Kokoro) · `chatterbox` · `kokoro` · `maya1` |
| `ref` | timbre to clone for Chatterbox: `kokoro:<voice>` (am_michael, am_fenrir, am_onyx, am_puck, bm_george, bm_lewis…) or a path to **your own** 10–15 s clean wav |
| `voice` | Kokoro voice used by the fallback |

Install Chatterbox once: `python setup.py --gpu` (NVIDIA, ~4 GB VRAM used).

## Direct the performance, line by line
```json
{"id": "B9",  "say": "Two shots. [sigh] No kill.",  "emo": "tense"},
{"id": "B12", "say": "Get Right. Headshot.",        "emo": "hype", "intensity": 0.95}
```
- `emo` → default intensity: calm 0.3 · sad 0.4 · neutral 0.45 · serious 0.5 · tense 0.6 · excited 0.75 · shock 0.85 · hype 0.95
- `intensity` (0–1) overrides it. Chatterbox maps it to `exaggeration = 0.3 + 0.7·i` and `cfg_weight = 0.5 − 0.2·i` (keeps the pace slow when dramatic).
- Reactions in brackets switch that line to **Chatterbox Turbo**: `[gasp] [sigh] [laugh] [chuckle] [groan] [sniff] [cough] [clear throat] [shush]`.
  One per line at most, never in the middle of a word. Captions never show them. Kokoro strips them.
- Direction guide: hook lines `tense 0.6–0.7`; context `serious 0.5`; each kill `excited → hype` rising; reveal question `tense`; answer `hype`.
- Only the lines you change are re-generated (cache per line). Then `python -m engine.cli build spec.json --audio-only` re-mixes without re-rendering frames.

## Finish the Maya1 backend (optional, do it on the PC)
`engine/voice.py` has a `Maya1` class stub. To wire it: read https://huggingface.co/maya-research/maya1 (prompt format with the
voice description, emotion tag syntax, SNAC decoding, sample rate), implement `synth(text, intensity)` returning `(float array, sr)`,
map `[gasp]`-style tags and `emo` to Maya1's own tags, and use `spec.voice.description` ("male, 30s, deep, documentary narrator").
Keep the same contract as `Chatterbox.synth`. Check VRAM on a 10–16 GB card.
