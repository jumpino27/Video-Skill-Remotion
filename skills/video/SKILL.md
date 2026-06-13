---
name: video
description: >-
  Produce a finished narrated video end-to-end: generate expressive ElevenLabs
  Eleven v3 voiceover with inline audio tags, transcribe it with OpenAI whisper-1
  for word-level timestamps, then build and render a Remotion video whose duration
  is driven exactly by the voice. Includes karaoke captions, animated SVG scenes
  that illustrate the script or supplied media, platform sizing for YouTube,
  Shorts, Instagram, or TikTok, and content.md social copy. Use when the user says
  "/video", asks to make a narrated video/reel/short/TikTok, or wants to turn a
  script into a video. Always interview the user first.
---

# /video — narrated video generator (TTS → timestamps → animated Remotion render)

You orchestrate the pipeline below. **Interview the user before building.** Never assume
the platform, script, or look — ask, confirm a short plan, then execute.

```
1. INTERVIEW    → platform(s), script, tone/emotion, media, accent, captions
2. VOICE        → ElevenLabs Eleven v3 (audio tags) → public/voice.mp3
3. TIMESTAMPS   → whisper-1 (word-level, OpenAI)   → public/captions.json
4. SCAFFOLD     → empty folder → create the Remotion project; else integrate  (NODE 18–22)
5. AUTHOR SCENES→ rewrite src/Scenes.tsx (⭐ prefer CINEMATIC one-world mode + /image textures)
6. ASSEMBLE     → place media + write public/props.json (dims from platform)
7. RENDER       → npx remotion render      → out/video.mp4
8. SOCIAL COPY  → write content.md (title/caption/hashtags) for the CHOSEN platform(s)
```

Skill location: wherever this skill is installed (e.g. `~/.claude/skills/video/`). Scripts
are in `scripts/`, the Remotion template in `assets/remotion-template/`, and the creator
config in `config/persona.json`. **API keys are resolved automatically** (via
`scripts/_shared.mjs`) in this order: the process env var, then `$SKILL_ENV_FILE`, then a
`.env` in the skill folder, the shared `.env` next to the skills folder, `~/.claude/.env`,
and finally `~/Documents/.env`. Keys used: `ELEVEN_LABS` (Eleven v3 TTS + Eleven Music) and
`OPENAI_API_KEY` (whisper-1 STT). An env var of the same name always overrides the file;
point `VIDEO_ENV_FILE` (or `SKILL_ENV_FILE`) at a different `.env` to override the path.

**Personalize this skill via `config/persona.json`** (copy `config/persona.example.json`):
the creator/brand name, social links, default ElevenLabs voice id + name, presenter name,
accent color, and how links should be distributed. The voice id also reads from the
`VIDEO_VOICE_ID` env var if set. When `persona.json` is absent the skill falls back to the
bundled example defaults — so the skill works out of the box and gets personal once filled in.

> ⚠️ **Node version matters.** Remotion's bundler/renderer is unstable on Node 23+ (e.g.
> Node 25 throws `WasmHash ... reading 'length'` during webpack bundling, and the FFmpeg
> stitch step can crash with `0xC0000142`). **Use Node 18–22 (Node 22 LTS recommended)** for
> `npm install` and rendering. Remotion **Studio** (`npm run dev`) usually still previews
> fine on newer Node, so you can validate visually even if headless rendering is blocked.
>
> ✅ **Tip:** if your system Node is 23+, install a portable Node 22 alongside it and prepend
> it to PATH only in the shells that run `npm install` / `npx remotion` — your system Node
> stays untouched for everything else (the TTS/STT/music scripts run fine on any Node 18+):
> ```powershell
> # download https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip, extract somewhere, then:
> $env:Path = "C:\path\to\node-v22.14.0-win-x64;" + $env:Path
> ```

---

## Stage 1 — INTERVIEW (always ask, use AskUserQuestion)

Group into one or two AskUserQuestion calls. Skip a question only if already answered.

**Brief-first rule:** Before writing any script or storyboard, determine what the video is
about and what role it should play. Ask when unclear: is this a critique/review, tutorial,
news/update, product or repo showcase, personal story, portfolio/about-me piece, ad, or
general explainer? Never assume the subject is the user or the user's profile, or
"what the user uses" unless the user explicitly says the video is about them. If the user
gives specific positioning, speaker, CTA, brand, or topic instructions, follow those over
all examples in this skill.


**Presenter rule:** If the user asks for a presenter-hosted, avatar-hosted, or lip-sync
video, use the presenter skill named in `config/persona.json` (`presenter.skill`, default
`/eve`) and refer to the presenter by `presenter.name` (default **Eve**). If that presenter
skill isn't installed, offer to build the video without an on-screen avatar instead.
1. **Platform & format** — drives dimensions and ideal length:
   | Choice | Dimensions | fps | Ideal voiced length |
   |--------|-----------|-----|---------------------|
   | YouTube (long-form) | 1920×1080 | 30 | 8–12 min |
   | YouTube Shorts | 1080×1920 | 30 | 30–60 s |
   | Instagram Reel | 1080×1920 | 30 | 7–30 s (≤90 s) |
   | TikTok | 1080×1920 | 30 | 21–34 s |
   | Instagram feed | 1080×1350 | 30 | ≤60 s |
2. **Script** — have one, or should you write it? If a topic, **write it sized to the
   platform** (~150 words/min) following the **VIRAL SCRIPT RULES** below (3-second hook,
   re-hooks, engineered CTA), and **show it for approval before TTS** — label the hook with
   its second count so the user can judge it ("0:00–0:03 HOOK: …").
   If the user's topic is broad, ask what angle to take before writing: explain, critique,
   compare, announce, demo, review, teach, persuade, or tell a story. Keep the script's
   point of view neutral or brand/subject-specific unless the user asks for first-person.
3. **Voice** — **the house voice comes from `config/persona.json` (`voice.id` / `voice.name`)
   on `eleven_v3`** (override per run with `--voice-id` or the `VIDEO_VOICE_ID` env var). If
   no persona is set, it falls back to ElevenLabs voice "Ivy" `eXO2dNYP4zo4oPWzuLta` (energetic
   young British female, good for social media). Eleven v3 speaks **70+ languages** natively.
   `generate-voice-elevenlabs.mjs` resolves the voice automatically — only ask the user about
   the voice if they want to change it.
4. **Delivery / tone (emotion)** — Eleven v3 is directed **inline, in the script itself**, with
   **audio tags** in square brackets + punctuation. You are the voice director — write the
   delivery INTO the script (see "Directing Eleven v3" below):
   - Emotion tags: `[excited] [sad] [angry] [happily] [sarcastic] [curious] [crying]
     [mischievously] [nervous] [annoyed] [thoughtful] [surprised] [tired] [calm]`
   - Reactions / non-verbal: `[laughs] [laughs harder] [starts laughing] [giggles] [chuckles]
     [wheezing] [sighs] [exhales] [exhales sharply] [inhales deeply] [clears throat] [gulps]
     [swallows] [snorts] [gasps] [happy gasp] [frustrated sigh]`
   - Delivery / pacing: `[whispers] [shouts] [pause] [short pause] [long pause] [rushed]
     [drawn out] [slowly] [dramatic tone] [interrupting] [overlapping] [professional]
     [sympathetic] [questioning] [reassuring] [deadpan] [dismissive] [singing] [woo]`
   - Accents (experimental): `[strong French accent] [strong Russian accent] [British accent]
     [Southern US accent] [pirate voice]` …
   - Sound effects (experimental, use sparingly): `[applause] [clapping] [gunshot] [explosion]`
   - Punctuation: ellipses `…` add pauses/weight; CAPITALS add emphasis; natural punctuation
     gives natural rhythm. **No SSML** — v3 ignores `<break>` tags; use tags + punctuation.
   - `--stability creative|natural|robust` (v3 is discrete): `creative` = most expressive /
     best tag response, `natural` (default) = balanced, `robust` = very stable but weak tag
     response. For tag-heavy scripts prefer `creative` or `natural`.
   - `--speed 0.7–1.2` sets pace (default `1.0`); prefer pacing tags over extreme speeds.
   - **Emotion changes mid-clip?** Just switch tags mid-script — one call handles it all. No
     more split-and-concat.
5. **Media** — image/video paths or a folder. If none, confirm **animated SVG scenes** (the
   default look — you author them from the script in Stage 5). For showcase/brand videos,
   ALSO offer **/image-generated transparent textures** (painterly strokes, particles, grain
   — things SVG can't fake) woven into the SVG world; this requires the /image **quality
   gate** (ask the tier with prices: low ~$0.006 · medium ~$0.05 · high ~$0.21 per image,
   usually 2–3 images at medium).
6. **Accent color** — hex (default from `persona.accentColor`, or `#6C5CE7`). Match it to the
   brand if there is one.
7. **Captions** — default **one-word-at-a-time karaoke** (`tiktok`); offer none.
8. **Providers** — TTS and STT are **fixed** by design; only music is a choice:
   - **TTS voice:** ElevenLabs **`eleven_v3`**, voice from `persona.voice` (default "Ivy"
     `eXO2dNYP4zo4oPWzuLta`) — `ELEVEN_LABS` key. Don't ask unless the user wants to change it.
   - **STT / captions (fixed):** OpenAI **`whisper-1`** — `OPENAI_API_KEY`. Kept on whisper-1
     **on purpose**: it returns word-level timestamps, which the one-word karaoke captions
     (and any presenter lip-sync) require. Don't ask.
   - **Background music (optional — ASK):** **none** (default) · **ElevenLabs Music**
     (`ELEVEN_LABS`, same key) · Suno (`SUNO_API`, legacy fallback). If chosen, generate a
     theme-matched track from the script's mood (Stage 6b).
   (`generate-voice.mjs` (MAI/OpenRouter) still exists in `scripts/` as a manual fallback,
   but is no longer the documented path.)

State a one-line plan (platform, dims, length, stability mode, music) and proceed.

### VIRAL SCRIPT RULES (mandatory for EVERY script you write, any topic)

Every script's job, in order: **stop the scroll → hold the watch → earn the like → convert
the approved next action.** The first 3 seconds decide whether the rest exists.

**THE HOOK — first 3 seconds (~8–12 words). Non-negotiable:**
- **Never open with** greetings ("Hey guys", "Welcome back"), introductions ("Today I'm going
  to show you…"), context, or a slow build. Open **mid-action**, as if answering a question
  the viewer already asked.
- Use ONE of these hook types (pick to fit the topic; vary across videos):
  - **Contrarian / myth-break** — "Everything you know about X is wrong."
  - **Curiosity gap** — "Nobody talks about the third one… and it's the only one that matters."
  - **Direct callout** — "If you do X every day, stop. Right now."
  - **Shock stat / specific number** — "97 percent of X fails for ONE reason."
  - **Stakes / loss** — "This mistake costs you X every single week."
  - **POV / scenario drop** — straight into a vivid moment, no setup.
  - **Result-first** — show/state the end result, then "here's how."
- The hook must **promise a specific payoff** the video actually delivers.
- **Direct the hook's delivery hardest**: strongest audio-tag contrast of the whole script
  (e.g. `[whispers]` → `[excited]`, or a cold open `[serious]` line) + the first visual beat
  landing inside the first second. The sound of the hook sells it as much as the words.

**THE BODY — retention engineering:**
- **Re-hook every ~8–10 seconds**: open loops ("but here's the part nobody mentions…",
  "wait until you see the last one"), numbered countdowns that END on the best item, or a
  mid-video twist. Never let two flat sentences sit back-to-back.
- **Hold the best payoff until ≥70% through** — tease it early, deliver it late.
- Second person ("you"), present tense, conversational. Short sentences (avg ≤12 words).
  Zero filler, zero throat-clearing, every sentence either advances or re-hooks.
- One idea per sentence; concrete > abstract (numbers, names, vivid verbs).

**THE CTA — engineered, not begged (final 2–3 seconds):**
- **ONE primary CTA per video.** Tie it to future value, never charity:
  "Follow for part two — the one trick that actually works" beats "please like and follow".
- **Resource videos (a repo, tool, product, site, article, or anything with a link):** the
  spoken CTA should match the user's distribution plan. If no plan is given, ask whether the
  link should be in the first comment, description, landing page, or omitted. Do not assume
  "my profile" or a personal profile.
- **General topic videos (no link):** use a subject-appropriate CTA: ask for a comment,
  invite a follow for more on that topic, point to a named resource only if provided, or end
  with a strong takeaway. Do not invent profile content.
- Like-bait is earned mid-video by a genuinely surprising beat, optionally cued softly
  ("if that just saved you an hour, you know what to do") — never as the closer.
- Optional **comment bait**: one easy-to-answer or mildly polarizing question ("which one are
  you, 1 or 2?") — only if comments are the goal instead of follows.

**Format check before approval:** present the script with timestamps and label the parts —
`0:00–0:03 HOOK / body beats / CTA` — so the user approves the retention structure, not just
the words.

### Directing Eleven v3 (write the performance INTO the script)
Eleven v3 takes **plain text + bracketed audio tags — no SSML** (`<break>` is unsupported).
You direct the voice like a screenwriter:
- **Place tags immediately before (or after) the phrase they modify**: `[excited] And it
  WORKED!` · `Nobody listens anymore. [sighs]`
- **Combine tags** for layered delivery (`[sighs] [tired] Fine… I'll do it.`), and switch
  freely mid-script as the emotion arcs.
- **Punctuation is part of the performance**: `…` = beat/hesitation, CAPITALS = emphasis,
  `—` = interruption/turn.
- **Match tags to the voice's character** — a calm voice won't suddenly `[shouts]` well;
  don't fight the voice.
- **Tags must describe something audible** (never `[smiling]`, `[pacing]`, `[music]`).
- Tricky names/terms: v3 natively reads **IPA between slashes** — `"/ˌbaɪoʊˈkemɪstri/"`.
- Normalize numbers/URLs/abbreviations into spoken words in the script ("$42.50" → "forty-two
  dollars and fifty cents", "elevenlabs.io" → "eleven labs dot io") — don't trust raw symbols.
- Keep each TTS call **under ~3000 chars**; chunk longer scripts and concat with ffmpeg.
- ⚠️ Audio tags produce REAL sounds (laughter, sighs) that whisper-1 will hear — after
  transcribing, skim `captions.json` and strip artifact "words" (e.g. transcribed laughter)
  if they'd look wrong as karaoke captions.

---

## Stage 2 — VOICE (ElevenLabs Eleven v3)

Work inside the project dir. Write the approved, **tag-directed** script to `script.txt`
(audio tags + punctuation already in it — that IS the emotional direction). Then:

```bash
node "<skill>/scripts/generate-voice-elevenlabs.mjs" --script-file script.txt \
  --stability natural --out public/voice.mp3
```
On Windows use full paths. Confirm `ok: true`. Defaults: model `eleven_v3`, the voice from
`config/persona.json` (or "Ivy" `eXO2dNYP4zo4oPWzuLta` as a fallback), stability `natural`
(use `creative` for maximum tag expressiveness, `robust` only when consistency beats
expressiveness — it dulls tag response). Optional: `--speed 0.7–1.2`, `--language <iso>`
(e.g. `ro`), `--seed N` for best-effort reproducibility, `--similarity 0–1`. Key:
`ELEVEN_LABS`, resolved from the `.env` search path (or `VIDEO_ENV_FILE`/`SKILL_ENV_FILE`)
— see `scripts/_shared.mjs`.

v3 is expressive but **non-deterministic** — if a take misses the mark, re-roll once or tweak
the tags/punctuation before changing settings. **Listen to (or at least spot-check) the take
before building the whole video on it.**

**Long scripts** (> ~3000 chars): split at paragraph boundaries, one call per chunk into
`public/seg1.mp3`, `seg2.mp3`, …, then concatenate:
```bash
ffmpeg -i "concat:public/seg1.mp3|public/seg2.mp3|public/seg3.mp3" -acodec copy public/voice.mp3
```
Then transcribe the final joined `voice.mp3` in Stage 3 so captions match.

## Stage 3 — TIMESTAMPS (OpenAI whisper-1 — required for word-level)

**Trim leading silence first** so captions (and any lip-sync) line up with the audio. TTS can
prepend ~0.2s of silence while whisper reports the first word at 0ms, shifting everything early:
```bash
ffmpeg -y -i public/voice.mp3 -af "silenceremove=start_periods=1:start_threshold=-38dB:start_silence=0.05" public/voice_t.mp3 && mv public/voice_t.mp3 public/voice.mp3
```
Then transcribe the trimmed file (and render that same file):
```bash
node "<skill>/scripts/transcribe-timestamps.mjs" --audio public/voice.mp3 --out public/captions.json
```
Writes word-timestamp `Caption[]` JSON (`{text," word",startMs,endMs,…}`). Note the reported
`durationSec` — that's the video length. **This stays on whisper-1 deliberately** (word-level
timestamps drive the one-word karaoke captions). Key: `OPENAI_API_KEY` from the `.env` search path.
(`scripts/transcribe-elevenlabs.mjs` remains as a manual word-timestamp fallback.)
**Skim the result:** v3 audio tags render as real sounds — whisper may emit artifact "words"
for laughter/sighs; delete those entries from `captions.json` if they'd look wrong on screen.

## Stage 4 — SCAFFOLD (handles empty folders automatically)

Decide based on the working folder:

- **Empty / new folder** → create a Remotion project. The reliable, non-interactive way is to
  **copy the bundled template in place** (it already IS a complete Remotion project with our
  components):
  ```powershell
  # <skill> = this skill's folder, e.g. ~/.claude/skills/video
  Copy-Item -Recurse "<skill>\assets\remotion-template\*" "."
  npm install
  ```
  (Equivalent official scaffolder: `npx create-video@latest` — but it is **interactive**, so
  only use it when a human can answer its prompts; for an automated `/video` run prefer the
  copy above.)
- **Already a Remotion app** (has `package.json` + `src/Root.tsx`) → integrate: copy
  `src/{Main,Scenes,Captions,Backgrounds}.tsx` from the template into `src/`, add deps
  `@remotion/captions` + `@remotion/media-utils` at the project's Remotion version, and point
  `src/Root.tsx` at the `Main` composition (one per language for multi-lang — see below).
- **Non-empty, non-Remotion folder** → copy the template into a `./remotion/` subfolder.

Then `npm install`. **Run with Node 18–22** (see warning up top). First install/render
downloads a headless Chromium (one-time) — use `run_in_background` and poll.

Reusable as-is from the template: **`Main.tsx`** (voice-driven duration + layout),
**`Captions.tsx`** (caption engine), **`Backgrounds.tsx`** (animated SVG backdrop).

---

## Stage 5 — AUTHOR THE ANIMATED SVG SCENES (`src/Scenes.tsx`)

This is the creative core. **`Scenes.tsx` is per-video — rewrite it so the visuals
illustrate THIS script.** Two modes; **prefer CINEMATIC for anything that should impress**
(product showcases, brand videos, launches). Use the simpler cut-scene mode only for quick
informational clips.

### ⭐ CINEMATIC MODE — one continuous animated world (no cuts, ever)

No scene cuts, no `<Sequence>` slicing. ONE unbroken, camera-driven animation where every
element ignites at the exact millisecond its word is spoken.

**🎨 INVENT A NEW CONCEPT FOR EVERY VIDEO — never repeat a previous one.** The continuous
craft is the constant; the world, motif and camera language must be born from THIS script's
theme. Before coding, write one sentence: *"the video is ___ traveling through ___."* Examples
of distinct concepts (pick NONE of these verbatim — derive your own from the script):
- a vertical scroll-painting the camera descends (used once: `…/Videos/impeccable-thread/` —
  a gold ink thread; study its `src/Scenes.tsx` for the CRAFT BAR, not the look)
- a continuous zoom INTO nested worlds (each beat lives inside the previous one)
- one object center-frame that never leaves but transforms per beat (a cube → blueprint →
  product → constellation), camera orbiting it
- a horizontal journey (train-window, conveyor, timeline) with beats as passing scenery
- a single line-drawing hand that sketches each beat and erases into the next
- a day-to-night light cycle where beats live at different hours; color temperature is the camera
- a growing organism (tree/city/circuit) whose new branches ARE the beats
The connective motif (the thing that travels: a thread, a spark, a hand, a train, the light)
and the camera move (descend / zoom / orbit / pan / morph) should both be DIFFERENT each video.

**Architecture (all pure functions of `frame` — no hooks in loops, no Sequences):**
1. **The world** — stations laid out along your camera's axis (vertical, horizontal, depth
   via scale, or "in place" via morphs), one per script beat, each filling one viewport.
   Long beats can use sub-stations for gentle micro-moves.
2. **The narration clock** — `const t = (frame / fps) * 1000` → everything is timed in ms
   **read directly from `captions.json` word `startMs` values**. Dump them first
   (`words.txt`) and pin every animation to its word: the element appears ON the word that
   names it. This is what makes it feel directed.
3. **The camera** — keyframes `[ms, value][]` over whatever the camera IS for this concept
   (translateY, scale+origin for zooms, rotation for orbits, a color temperature for light).
   Write a tiny `kf(tMs, keys)` interpolator that eases EACH segment with the brand's curve
   (e.g. `Easing.bezier(0.2, 0.8, 0.2, 1)`); Remotion's `interpolate` easing is global, so
   per-segment needs the helper. Hold during beats, glide between them (~1.1–1.4s).
4. **Helpers** — `seg(t, aMs, bMs, ease?)` (clamped 0..1 progress between two times) and
   `pop(p) = 1 - (1-p)^4` (soft settle, no bounce) replace `spring()` everywhere.
5. **The connective motif** — ONE element that travels the whole video and stitches it
   together. For drawn paths, sample a polyline and use the **`pathLength={1000}`
   normalization trick**: `strokeDasharray={1000}`, `strokeDashoffset={1000 * (1 - p)}` —
   progressive draw-on without measuring path length; give the tip a glow/trail. For
   non-path motifs (a hand, a vehicle, light) the same `kf()` keyframes drive it.
6. **Depth** — give the world dimensionality appropriate to the concept: parallax layers at
   different multipliers (e.g. 0.88× / 1× / 1.12×) for translations, staggered scale rates
   for zooms, foreground/background blur or opacity falloff for orbits.
7. **Generated media (USE /image + /crop)** — painterly textures SVG can't fake elevate
   everything: ink brushstrokes, gold-leaf flakes, paper grain, smoke. Ask the /image
   quality gate, generate on a subject-aware chroma, let /crop key them, **view the
   checkerboard gates**, then copy to `public/media/` and place as `<Img
   src={staticFile("media/…png")}>` **in the HTML layer of the world container** (NOT SVG
   `<image>` — Remotion's `<Img>` waits for load; SVG `<image>` can render blank). Note:
   a "fragmented cutout" FAIL from /crop is expected for scatter textures (flakes/particles)
   — the visual gate decides.
   Drift/rotate them slowly; mirror with `scaleX(-1)` to reuse one stroke twice.
8. **Micro-delights** — a 2–4 frame near-white flash for HMR/impact moments, a breathing
   glow (`1 + 0.1*sin(frame/fps*3.4)`), one playful story beat (something tries and fails).
9. **Captions clearance** — when the camera HOLDS at station S, content must sit in
   `S+250 … S+1350` (the karaoke captions own the bottom ~25% of the viewport).

**Process:** invent the concept sentence → dump word times → assign stations to beats →
write camera keys (landing slightly before each beat's first word) → build station content
with `seg()` ignitions → generate /image textures in parallel → `npx tsc --noEmit` →
**run the MANDATORY SVG self-review below (code audit + stills gate)** → fix everything →
render.
**Anti-template check:** if this video's concept sentence, motif, or camera move matches a
previous video you've made, throw it away and invent again. The reference project shows the
quality bar — copying its look means the check failed.

### 🔍 MANDATORY: SVG self-review after authoring (both modes — never skip)

After writing `Scenes.tsx`, **audit it and fix EVERYTHING before rendering.** Do both passes:

**Pass 1 — code-level audit (read your own SVG like a reviewer):**
- **Overlaps**: every panel/window/bezel vs every text, chip, diagram and animated element
  that shares its time window — compute the actual x/y extents, don't eyeball the code.
  Dive windows and host frames are the #1 offenders.
- **Caption clearance**: the karaoke pill owns roughly y 1380–1700 (bottom ~25%). NOTHING
  (labels, toasts, window bottoms) may sit there while it could be visible.
- **Text**: sizes legible at final scale AND when seen shrunk inside a parent window;
  strings actually fit their containers (estimate ~0.55×fontSize per mono char); no em
  dashes; labels anchored correctly (`start`/`middle`/`end`).
- **Timing gates vs camera**: any content gated by an opacity ramp must be visible BY the
  time the camera lands on it (gate start ≤ landing), and static "chrome" (frames, gauges,
  calendars) should be ungated so it shows as a tease through parent windows — a gated
  level reads as an ugly blank panel from outside.
- **State semantics**: resting poses must make sense before their animation fires (a gauge
  needle rests at the value the narration implies, not at zero).
- **React/SVG traps**: no hooks in loops/conditionals; HTML `<Img>` layering by DOM order,
  never negative `zIndex` (it vanishes behind the parent's background); `pathLength`
  normalization for draw-ons; unique `id`s for filters/clipPaths.

**Pass 2 — stills gate (eyes on pixels):**
render a still at EVERY beat/station midpoint plus 1–3 mid-glide frames, **view each one**,
and check: right content under the right narration word, no overlap/clipping, brand colors,
readable text, captions clear. **Fix every finding and re-render the affected stills until
all pass. Only then render the video** — and if the user is reviewing along, show the stills
and wait for their go before the final render.

### Art direction first (BOTH modes — /impeccable, required for brand work)

Before writing any SVG, invoke the **/impeccable** skill to define the visual language so the
scene looks designed, not generic — especially when matching a brand/website: fetch the site,
**extract its actual design tokens** (pull the CSS: palette with hex/OKLCH, font stacks, type
scale, easing curves — e.g. grep the stylesheet for `--*:` custom properties), typography,
layout motifs and mood; run `node ~/.claude/skills/impeccable/scripts/load-context.mjs`
if the project has PRODUCT.md/DESIGN.md; then apply the impeccable laws while authoring —
OKLCH/tinted neutrals (never `#000`/`#fff`), **no side-stripe borders, no identical card grids**
(prefer a schedule/table or annotated diagram), no gradient text, **no em dashes** in on-screen
copy. Define the tokens as named constants at the top of `Scenes.tsx` (INK / TEXT / MUTED /
accent ladder / support colors) and drive every fill/stroke from them. Even the brand's
easing curve belongs in the camera (`Easing.bezier(...)` from the site's `--ease` var).

### Cut-scene mode (simple) — per-beat `<Sequence>`s

**Method:**
1. **Split the script into beats** — one scene per sentence/idea. Give each a weight ≈ its
   spoken seconds (the timeline is divided by weight, so scenes track the narration).
2. **Pick a concrete visual metaphor per beat** and animate it with SVG. Examples:
   a typed prompt box → a spinning "system" gear; a hub with orbiting agent nodes + data
   packets; a server rack with blinking lights; project cards springing in; lightbulb →
   gear → checkmark; a domain/CTA assembling with a sweeping underline.
3. **Animate with Remotion primitives** — `useCurrentFrame()`, `interpolate()`, `spring()`;
   continuous motion via `frame/fps` (rotation, orbit, pulsing). Wrap each scene in a
   `<Sequence>` and give it an entrance/exit fade.

**Reuse these helpers from the example `Scenes.tsx`:** `useInOut(len)` (entrance/exit
opacity), `<Svg>` (a `1080×1920` viewBox layer), `<Defs accent>` (a `glow` filter +
`hubgrad`), and the `Kicker` label.

**Sync scene cuts to the voice (important):** write one scene per sentence/beat, then let
`useSceneCuts(captions, SCENE_COMPS.length)` (in `scene-sync.ts`) place the scene boundaries
on the narration's biggest pauses — so each scene appears exactly while its sentence is
spoken. `Main.tsx` passes `captions` into the scene set; the hook falls back to equal slices
if the audio has no clear pauses. (Keep ~6 short sentences for a clean 6-scene sync.)
⚠️ **With Eleven v3, in-sentence `…` pauses can be BIGGER than the beat gaps**, which makes
the pause-picker cut in the wrong places (one scene gets a tiny slice). When beats matter,
**pass explicit cuts**: read each beat's first-word `startMs` from `captions.json`, subtract
~250ms, and call `useSceneCuts(captions, N, CUT_MS)` (third arg, `N-1` entries). Verify with
stills at each scene midpoint before the full render.

**Keep it on-brand:** drive every stroke/fill from the `accent` prop; keep content in the
upper ~70% so it never collides with captions at the bottom; favor a few bold animated
shapes over clutter. Run `npx tsc --noEmit` after writing.

If the user provided **media**, you can skip custom scenes — `Main.tsx` shows the images/
videos as Ken-Burns `<Sequence>`s instead (ordered to match the narration).

---

## Stage 6 — ASSEMBLE

In `public/`: copy `voice.mp3` + `captions.json`; copy any media into `public/media/`.
Write `public/props.json` (shape in `public/props.example.json`):

```json
{ "platform":"reel","width":1080,"height":1920,"fps":30,
  "audioFile":"voice.mp3","captionsFile":"captions.json",
  "media":[], "captionStyle":"tiktok","accent":"#22D3EE","title":"" }
```
**Set `width`/`height`/`fps` from the platform table.** Leave `media:[]` to use your authored
scenes. **Do NOT set duration** — `calculateMetadata()` derives it from the real `voice.mp3`
length, so visuals always match the voice.
⚠️ **Studio reads `DEFAULT_PROPS` in `Main.tsx`, NOT `props.json`** (only the render reads
`props.json`). **Always update `DEFAULT_PROPS` to mirror `props.json`** (accent, platform,
dims, musicFile) — otherwise the user opens Studio and sees the template's purple defaults
instead of the brand look, and reports "wrong colors".

## Stage 6b — MUSIC (optional, provider per Stage 1 choice)

Only if the user chose music. Generate a theme-matched track from the script's mood into
`public/music.mp3`, then set `musicFile:"music.mp3"` (+ optional `musicVolume`) in props.
`Main.tsx` loops/crops it to length, keeps it a quiet bed, and fades it in/out.

**ElevenLabs Music** (primary — same `ELEVEN_LABS` key; pass the voice duration in ms so it fits):
```bash
node "<skill>/scripts/generate-music-elevenlabs.mjs" --prompt "<mood, genre, tempo, instrumentation>" \
  --instrumental --length-ms <voiceDurationMs> --out public/music.mp3
```
Prompt like a producer: genre + mood + key instrumentation + BPM ("warm lo-fi tech bed,
soft Rhodes, brushed drums, 80 BPM, understated"). For richer prompting (and full songs)
see the **/music** skill's Eleven Music guide.
**Suno** (legacy fallback — async: submits, polls, downloads; needs `SUNO_API`):
```bash
node "<skill>/scripts/generate-music-suno.mjs" --prompt "<mood, genre, tempo; no vocals>" \
  --instrumental --model V4_5 --out public/music.mp3
```

## Stage 7 — RENDER  (Node 18–22 — see the Node note up top)

**Validate with stills FIRST** (cheap, catches sync/layout/color bugs before a full render):
render one still at each scene's midpoint, then **Read/view them** and check: right scene
under the right narration beat, kicker text, brand colors, nothing colliding with captions.
```powershell
# if your system Node is 23+, prepend a portable Node 22 first (see the Node note up top):
# $env:Path = "C:\path\to\node-v22.14.0-win-x64;" + $env:Path
npx remotion still src/index.ts Main stills/f<N>.png --frame=<N> --props=./public/props.json
```
Then the full render:
```bash
npx remotion render src/index.ts Main out/video.mp4 --props=./public/props.json
```
Report path (`out/video.mp4`), final duration, dimensions, voice. To let the user tweak
first: `npm run dev` opens Studio at http://localhost:3000.

## Stage 8 — SOCIAL COPY  (`content.md`)

Always write a **`content.md`** next to the project with ready-to-paste title / caption /
hashtags — but **only sections for the platform(s) the user chose in Stage 1.** (Instagram-only
→ only an Instagram section; "TikTok + Instagram" → both; etc.) For multi-language videos,
write one block per language.

**⚠️ The caption is a SECOND piece of content — never a transcript.** Copy-pasting script
lines into the caption is forbidden: the viewer just HEARD the video; the caption's job is
to add a layer the video doesn't have and convert the impression. Rules:

- **Caption hook ≠ video hook.** The first line must be a *different* hook than the spoken
  one — a complementary angle on the same payoff (video: "97% of X fails for one reason" →
  caption: "I wasted 2 years before figuring this out 👇"). Same promise, fresh wording.
- **Add exclusive value** the video doesn't contain: one bonus tip, a number/detail that got
  cut, a behind-the-scenes line, or a "save this for later" utility framing — reward people
  who read captions, they're the ones who follow.
- **Open a loop only the video closes** (for feed/search viewers who read first): "the third
  one is the one nobody does" — makes the caption drive watch-through, not replace it.
- **End with comment bait**: one easy-to-answer or mildly polarizing question ("which one
  are you — 1 or 2?"). Comments are the strongest ranking signal on every platform; the
  video's CTA already owns the follow, so the caption owns the comments.
- **Keywords woven naturally** into real sentences (that's what drives discovery in 2026 —
  captions/keywords now matter more than hashtags on every platform) — never a keyword list.
- **Titles tease, never spoil**: keyword first + curiosity gap; if the title gives away the
  video's payoff, there's no reason to press play ("Why your X keeps failing" ✓ — "X fails
  because of Y" ✗).
- **CTA wording differs from the video's** so the two together feel like a campaign, not an echo.
- **First-comment block (resource videos only when appropriate):** include a ready-to-paste
  **"First comment"** section only if the user wants links posted there or the platform plan
  calls for it. Otherwise put links where the user requested (description, landing page, etc.)
  or omit them. The video's spoken CTA, caption tease, and link placement must all agree.

**2026 per-platform rules (write the copy to match):**

- **TikTok** — caption **150–300 chars**; put the hook/primary keyword in the **first ~80
  chars** (only ~100–150 show before "more"); **3–5 hashtags** (1 broad-niche, 1 mid, 1–2
  specific); **avoid #fyp/#foryou** (saturated, no benefit). No separate title.
- **Instagram (Reel/feed)** — keyword-rich caption with a strong first line; **3–5 niche
  hashtags** (Instagram caps at **5** since Dec 2025) at the end or first comment; lean on
  long-tail keywords for search. Add a short on-cover title if relevant.
- **YouTube Shorts** — **title < 60 chars with the focus keyword in the first 3 words**
  (power words: "in 60 seconds", "2026"); **150–200-word description** with keyword + variants;
  **3–5 hashtags incl. `#Shorts`** + one niche tag. (Captions are already burned in — good,
  captioned Shorts rank higher.)
- **YouTube long-form** — **title < 60 chars**, keyword first; **150–200-word description**,
  main keyword in the first **25 words**, then what they'll learn + **timestamps** + links;
  **5–10** relevant tags/hashtags.

Format each platform as its own `##` section with clear **Title / Caption / Hashtags**
sub-labels so the user can copy each piece directly.

---

## How the pieces connect (mental model)

- **Duration** — `Main.tsx` `calculateMetadata()` calls
  `getAudioDurationInSeconds(staticFile(audioFile))` → `durationInFrames = ceil(sec*fps)+tail`.
  **Voice length == video length.**
- **Captions (`Captions.tsx`)** — a custom **one-word-at-a-time karaoke** engine:
  - shows ONLY the word currently being spoken, for its exact timestamped duration, then it
    leaves (blank during real pauses); the next word appears on its own.
  - genuinely **fast** words (duration < `MIN_UNIT_MS`, e.g. a quick "I make") are shown
    together as one unit (max 2 words) so they don't flash by.
  - **fits the screen**: a too-wide pair **stacks** vertically (one word above the other); a
    too-long single word **shrinks** to fit the safe width. Highlight = accent pill, dark
    text, `spring()` pop.
  - tunables at the top of the file: `MIN_UNIT_MS`, `MAX_UNIT_WORDS`, `JOIN_GAP_MS`, `HOLD_MS`.
- **Visuals** — provided media → Ken-Burns `<Sequence>`s; otherwise your authored
  `Scenes.tsx` over a faint `AnimatedBackground` + accent vignette.
- **Audio** — one `<Audio src={staticFile(audioFile)} />`.

## Multi-language videos
To ship the same video in several languages:
1. Translate the script natively per language (keep `…` pauses + the audio tags + the domain;
   tags stay in English brackets - v3 understands them in any script language). Keep it
   in the point of view the user approved. Use third person about the subject by default
   ("the tool does...", "the founder explains..."), and use first person only when the user
   says the video is about them or provides an approved first-person script. Eleven v3
   covers 70+ languages; pass `--language <iso>` to pin it (e.g. `--language ro`).
2. For each `<lang>` generate the voice + timestamps into `public/voice_<lang>.mp3` /
   `public/captions_<lang>.json`.
3. Extend the `L10N` map in `Scenes.tsx` (`en/de/it/ro`) so the kickers, typed prompt, project
   subtitles and CTA localize from the `lang` prop.
4. **Register one `<Composition>` per language in `src/Root.tsx`** (id = `EN`/`DE`/…), each with
   `defaultProps` = `{...DEFAULT_PROPS, lang, audioFile:"voice_<lang>.mp3",
   captionsFile:"captions_<lang>.json"}`, wrapped in a `<Folder>`. They then each show in the
   Studio sidebar to preview/export individually, and render by id:
   `npx remotion render src/index.ts <ID> out/video_<lang>.mp4` (no `--props` needed).

Durations differ per language — the scenes auto-stretch to each voice's length.

## Customizing further
- Background music: drop a track at `public/music.mp3` and set `musicFile` (+ optional
  `musicVolume`, default 0.28) in the props/defaultProps. `Main.tsx` loops it, auto-crops to
  the video length, and applies a **low→normal fade-in** at the start and **normal→low
  fade-out** at the end (narration sits on top). Generate via ElevenLabs Music (Stage 6b,
  `ELEVEN_LABS` key) — ask first; otherwise hand the user a generation prompt.
- Long scripts: keep TTS input under ~3000 chars/call; chunk + concatenate for long videos.

## Troubleshooting
- **No API key** → add `ELEVEN_LABS` (TTS/music) and `OPENAI_API_KEY` (STT) to a `.env` on the
  search path (skill folder, shared skills `.env`, or `~/.claude/.env`), or point
  `VIDEO_ENV_FILE`/`SKILL_ENV_FILE` at your `.env`.
- **TTS 401/quota error** → check the `ELEVEN_LABS` key is valid and the account has credits
  (v3 bills per character). If the `.env` key is valid but calls still 401: a **stale
  `ELEVENLABS_API_KEY`/`XI_API_KEY` env var** may shadow it for that name — key names resolve
  in priority order (`ELEVEN_LABS` first, env-then-file per name), so check
  `Get-ChildItem env: | Where-Object Name -match 'ELEVEN'` and remove leftovers.
- **Audio tags have no effect** → stability is too high (`robust` dulls tags — use `creative`
  or `natural`), or the tag fights the voice's character. Reword the tag (e.g. `[whispers]`
  vs `[WHISPER]`), add punctuation cues, or re-roll — v3 is non-deterministic.
- **Weird extra noises / hallucinated sounds** → `creative` stability + heavy tagging can
  hallucinate; switch to `natural`, trim tag density, or re-roll (optionally with `--seed`).
- **A name/term is mispronounced** → use inline IPA between slashes (`"/ˈnoʊkiə/"`) or a
  phonetic respelling.
- **`WasmHash ... reading 'length'` during Bundling, or FFmpeg `0xC0000142` at stitch** →
  Node too new. **Use Node 18–22** (`nvm install 22 && nvm use 22`, delete `node_modules`,
  reinstall). Studio (`npm run dev`) still previews on newer Node.
- **No word timestamps** → STT must be `whisper-1`; MAI-Transcribe-1.5 has none.
- **Remotion version mismatch** → every `@remotion/*` + `remotion` must share one version.
- **Captions out of sync** → `captions.json` must come from the SAME `voice.mp3` you render.
- **Scenes collide with captions** → keep scene content in the upper ~70% of the frame.
- **TTS/STT scripts need Node 18+** (global `fetch`, `FormData`, `Blob`).
```


