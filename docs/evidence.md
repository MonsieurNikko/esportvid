# Evidence: how to reconstruct a play before drawing it

Order of trust: **frame** (read on the clip) > **official data** (Liquipedia, HLTV, Riot/Valve data) > **written article** > **caption / commentary**.
When two disagree, the higher one wins and the brief says so.

## 1. Read the clip twice
- Pass 1, `/watch`: what it is, roughly. Its frames are 512 px wide: names, HP and sides read from them are guesses.
- Pass 2, `ffmpeg` on the downloaded file: contact sheets at native resolution, 1–2 fps over the whole clip and 6–10 fps over the action,
  plus enlarged crops of the kill feed, minimap, clock, score, HP bars and ability icons. Open every sheet.
- Sides first: team colour, weapons, who carries the objective. In CS, yellow = T and blue = CT on the HUD.

## 2. Evidence table (in `brief.md`)
One row per kill, position, dash, ability, utility, HP change, score and stake:

| clip time | who | what | evidence (frame time, or URL) | status |
|---|---|---|---|---|

`status` is **measured** (read or computed from frames), **sourced** (URL opened and read) or **inferred** (deduced).
An inferred row is labelled in the brief and, in the video, narrated vaguely or cut.
End the brief with "Not claimed": the tempting statements the evidence does not support.

## 3. Space: the real map, then projected positions
- Geometry comes from the map version played that day: official or community radar, or the game's navigation data.
  An old map differs from today's (LoL before the 2015 rework, Inferno before 2016). Name the source in the brief.
- Fixed angled camera (LoL, Overwatch spectator): convert pixels to ground coordinates from landmarks whose coordinates are known.
  LoL: pitch 56°, vertical FOV 40°, distance about 2250 units; anchor each frame on a turret still on screen.
- First-person (CS, VALORANT): use the minimap dots and the callouts visible in the frame.
- Check the result: measure the distance between two known landmarks and report the error; every point must land on walkable ground;
  a Flash, dash or blink must match its known range.
- Between two measured moments, movement is interpolated: say so.

## 4. Abilities and utilities
- Spectator side panels date them: an icon going dark = cast, to about 0.1 s. Read ultimate, Flash, Ignite, grenades, armour, item actives.
- HP: measure the bar in pixels over time; the pixel width gives the precision.
- Order the casts by measured time, even when an article says otherwise.
- Range check: is the killer in range? If not, look for a shadow, pet, trap, projectile or wallbang.
- Effects you cannot identify go under "Not identified".

## 5. Try to break it
For each key claim, write what would make it false, and look for that. Then have another agent or the user attack the brief, and check
their objections against the frames too: reviewers also get timings wrong. Finally, compare each radar still with the clip frame of the same moment.

## Worked example: Faker vs Ryu (2013)
| First draft | Evidence | Correction |
|---|---|---|
| Map drawn by eye: fight on mid lane | 2013 navigation data + 19 projected positions | at KT's base exit, between the torch wall and the jungle |
| Faker starts at 65% HP | HP bar in pixels | 100%, then 33%, then 12% |
| "Flash, Ignite" (2014 article) | icons: Ignite 7.1 s, Flash 7.7 s | "Ignite, shuriken, Flash" |
| Faker kills Ryu | Faker ~495 units away, slash radius 315 | his shadow, ~107 units away, kills Ryu |
