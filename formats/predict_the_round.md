# Format 4 — PREDICT THE ROUND

**Promise:** "Who wins this?" — the video stops at the decisive moment, the viewer comments a prediction, then the outcome.
**Why it works:** two comment moments (prediction + "I knew it"), strong completion.
Series tag: `PREDICT THE ROUND · #N`.

## Section plan
| # | section | content |
|---|---|---|
| 1 | `cold_open` | `title3d` = "1 V 3" / "4 HP", `punch_text` = "WHO WINS?" |
| 2 | `rewind` | – |
| 3 | `context` | `score` → `lineup` → `alarm` (what's at stake) |
| 4 | `radar` `"scene": "r1"` | the round up to the decisive moment (stop BEFORE the outcome) |
| 5 | `predict` | `question` "WHO WINS?", `options` [{label: hero name, color: hero}, {label: opponents, color: opp}] |
| 6 | `radar` `"scene": "r1"` | same scene, continues: the outcome (kills, defuse, etc.) — events reference this section's lines |
| 7 | `cards` | result card ("HE DID IT" / "SO CLOSE"), then outro "Did you call it? ▼" |

## Rules
- The predict freeze must land on a real 50/50 moment (2v2 timer, 1v3 with the bomb planted…).
- Both radar sections share one `scene`: map, entities and event list live in the first radar section; the second only has `lines` (+ `"lead": 0.3`).
  Put all `events` in the first section but reference lines from either section (the engine maps time across the pause).
