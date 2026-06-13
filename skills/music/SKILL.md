---
name: music
description: Generate full original songs or instrumentals with ElevenLabs Music (Eleven Music). Use when the user wants to create/make/generate a song, track, beat, theme, jingle, background music, or game music. ALWAYS interviews the user first to gather genre/mood/vocals/structure, web-searches any referenced artist's STYLE (never names the artist in the prompt — copyright), then crafts a masterpiece prompt (or a composition_plan for precise section/lyric control) and renders the audio.
---

# /music — ElevenLabs Music Song Generator

Create studio-quality original songs and instrumentals with **Eleven Music**.
Your job is to be a great music producer: **interview first, then craft a world-class prompt
(or composition plan), then render.**

## Where things live (for the user)
- **Skill folder:** wherever this skill is installed (e.g. `~/.claude/skills/music/`)
- **API key:** `ELEVEN_LABS`, resolved in order from the env var, then a `.env` in the skill
  folder, the shared `.env` next to the skills folder, `~/.claude/.env`, or `~/Documents/.env`
  (point `SKILL_ENV_FILE` at any `.env` to override). An env var of the same name always wins.
- **Generator script:** `generate_music.py` (ElevenLabs `/v1/music`)
- **Legacy fallback:** `generate_music_lyria.py` (Google Lyria 3 via OpenRouter — only if
  ElevenLabs is down/out of credits)
- **Output:** saved to a `music_output/` folder in the current working directory by default.

## Capabilities & cost
- One model, **3 s – 10 min** per track (`--length-ms 3000..600000`; omit to let the model pick).
- Vocals or instrumental; **`--instrumental` guarantees no vocals** (`force_instrumental`).
- Custom lyrics, multilingual lyrics, multiple vocalists, timed structure.
- Billing is **credit-based on the ElevenLabs account** (length-proportional). No fixed
  per-track price — for drafts, generate a short 30 s version first, then the full length.

---

## STEP 1 — ALWAYS interview first (do NOT generate yet)

Never jump straight to generation. Ask the user the questions below (use the AskUserQuestion
tool when it fits, or just ask conversationally — be warm and quick). Skip any the user already
answered. Gather:

1. **Vocals?** — Instrumental only, or sung? (If sung: language? who sings — e.g. female alto,
   male baritone, gravelly rocker, two singers harmonizing?)
2. **Topic / vibe** — what's the song about, or what feeling/scene?
3. **Genre + era** — e.g. "80s synth-pop", "early-90s boom-bap", "cinematic orchestral", "lo-fi".
4. **Mood** — energetic, nostalgic, dark, dreamy, aggressive, triumphant…
5. **Reference artist/style?** — "in the style of X" (handle per the copyright rule below).
6. **Length** — 30 s draft first, or straight to a full ~2–3 min song? (3 s–10 min supported.)
7. **Any specifics?** — BPM, key, instruments, structure, a moment ("drop at 0:12",
   "lyrics begin at 15 seconds"), or their own lyrics.

If the user already gave a rich description, just confirm the 1–2 missing essentials
(vocals? length?) and go.

## STEP 2 — 🚫 COPYRIGHT-SAFE ARTIST STYLE (critical rule)

If the user references a real artist ("in the style of Eminem", "sounds like Billie Eilish"):

1. **WebSearch that artist's musical style** — tempo, genre, vocal delivery, instrumentation,
   production traits, era, signature techniques.
2. **Translate that into descriptive musical attributes** in the prompt.
3. **NEVER put the artist's name (or song titles / copyrighted lyrics) into the prompt.**
   Describe the *style*, not the *person*.
   - ❌ "a rap song like Eminem"
   - ✅ "an aggressive horror-core hip-hop track ~88 BPM, fast double-time male rap flow with a
     nasal mid-range timbre, intricate internal rhymes, dark minor-key piano loop, gritty
     boom-bap drums, distorted 808s"

Briefly tell the user which stylistic traits you pulled so they can tweak.

## STEP 3 — Craft the prompt (be a masterpiece producer)

Write ONE rich prompt following the Eleven Music guide (below). For instrumentals, pass
`--instrumental` AND say "instrumental only" in the prompt. For precise section/lyric placement
use a **composition plan** instead (also below). Show the user the final prompt before spending
(a quick one-liner confirm is fine).

## STEP 4 — Generate

Default output dir = `music_output/` in the cwd. Write the prompt to a file (handles long
prompts / special chars), then run:

```bash
mkdir -p music_output
# <skill> = this skill's folder, e.g. ~/.claude/skills/music
python "<skill>/generate_music.py" \
  --prompt-file music_output/prompt.txt \
  --out music_output/<short-name>.mp3 \
  --length-ms 120000            # optional; omit to let the model size it
  # add --instrumental to guarantee no vocals
  # or:  --plan-file music_output/plan.json   (instead of --prompt-file)
```

The script prints JSON with the final file path, byte size, mode and format. It auto-corrects
the file extension to the real audio format.

## STEP 5 — Deliver

- Report the saved file path + length + mode.
- Offer to: open/play it, render a longer/full version (if they drafted short), make variations
  (each generation bills credits again), or tweak the prompt / plan.
- Note: results are non-deterministic — same prompt can differ each run; offer re-rolls.

---

# 📖 Eleven Music Prompting Guide (official best practices)

**Concise and evocative beats long and rambling** — prompt length does not correlate with
quality. Lead with genre + mood, then the details that matter.

**Genre & mood** — abstract descriptors work ("eerie", "triumphant"), and so does detailed
musical language ("dissonant violin over pulsing sub-bass"). Add an era for flavor
("early-90s boom-bap", "80s synthwave").

**Instrumentation** —
- Precede an instrument with **"solo"** to feature it: "solo electric guitar".
- Use **"a cappella"** before vocal descriptions for unaccompanied vocals: "a cappella female vocals".
- Include **key, BPM and tone** for tighter control: "130 BPM, in A minor, warm analog texture".

**Vocals** — describe the singer(s): gender, timbre, range, delivery ("raw", "live",
"aggressive", "breathy"). Multiple vocalists: "two singers harmonizing in C". Specify lyric
language, or switch with a follow-up ("make it Japanese").

**Structure & timing** — state the length ("60 seconds") or pass `--length-ms`. Use timing
cues inside the prompt: "lyrics begin at 15 seconds", "instrumental only after 1:45",
"build to a drop at 0:30".

**Custom lyrics** — include them in the prompt with section tags
(`[Verse 1] [Pre-chorus] [Chorus] [Bridge] [Outro]`) for creative control.

**Instrumental** — say "instrumental only" in the prompt AND pass `--instrumental`
(`force_instrumental=true` guarantees it).

**High-level intent works** — "ad for a sneaker brand", "peaceful meditation with voiceover"
will shape tone, structure and content appropriately.

**Example prompts**
- "A 30-second lofi hip hop beat, dusty vinyl crackle, mellow Rhodes chords, slow boom-bap
  drums at 85 BPM, jazzy upright bass. Instrumental only."
- "An upbeat feel-good pop song in G major at 120 BPM, bright acoustic strumming, claps, warm
  female vocal harmonies about a summer road trip. Chorus kicks in at 0:22."
- "Dark atmospheric trap at 140 BPM, heavy 808s, eerie pads, sharp hi-hats, in D minor.
  A whispered male vocal sample repeats through the bridge."

## Composition plans (precise control)

For exact section structure, per-section styles, lyric placement, or multi-vocalist
arrangements, send a **composition plan** (`--plan-file plan.json`) instead of a prompt
(the API forbids combining them). Shape:

```json
{
  "positive_global_styles": ["synthwave", "80s", "driving", "118 BPM", "analog warmth"],
  "negative_global_styles": ["acoustic", "lo-fi", "muddy low end"],
  "sections": [
    {
      "section_name": "Intro",
      "positive_local_styles": ["filtered arpeggio builds", "no drums"],
      "negative_local_styles": ["vocals"],
      "duration_ms": 12000,
      "lines": []
    },
    {
      "section_name": "Verse 1",
      "positive_local_styles": ["punchy drums enter", "male baritone vocal"],
      "negative_local_styles": [],
      "duration_ms": 25000,
      "lines": ["Neon rivers running through the night", "Chasing echoes in the satellite"]
    },
    {
      "section_name": "Chorus",
      "positive_local_styles": ["anthemic", "layered harmonies", "wide synths"],
      "negative_local_styles": [],
      "duration_ms": 22000,
      "lines": ["We are the light", "Burning through the static of the night"]
    }
  ]
}
```

- `lines` = the lyrics for that section (empty array = instrumental section).
- Section `duration_ms` values sum to the song length. (The API's
  `respect_sections_durations` flag controls strictness — leaving it off lets the model
  flex sections slightly for better quality while preserving total duration.)
- Build the plan FROM the interview: hook the chorus lyric, map energy per section.

## Limitations
- Generation is single-turn (no iterative editing of an existing track) — re-roll instead.
- Non-deterministic: identical prompts produce different takes.
- Safety filters block artist-voice & copyrighted-lyric requests (hence the style rule).
- Commercial use requires a paid ElevenLabs tier.

## Fallback — Google Lyria 3 (legacy)
If ElevenLabs is unavailable: `generate_music_lyria.py --prompt-file p.txt --out s.mp3
--model clip|pro` (needs `OPENROUTER_API_KEY` in the skill `.env`; clip = 30 s $0.04,
pro = full song $0.08). The old Lyria prompting guide lives in that script's docstring era —
the prompt style above works for it too.
