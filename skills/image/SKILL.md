---
name: image
description: >-
  Generate, edit, and animate images with the OpenAI Images API (gpt-image-2),
  then auto-key them to transparency via the /crop skill. Use when the user wants
  to create an image from a prompt, edit/restyle an existing image, or make a
  frame-by-frame animation / sprite sheet. Always asks the user to pick a quality
  tier (low/medium/high, with prices) before spending. For transparent assets it
  renders the subject on a flat solid chroma background chosen to be ABSENT from
  the subject (never blindly green) and chains to /crop to cut it out.
---

# image

Create images with **gpt-image-2** and hand transparent assets straight to `/crop`.
`image.py` does the API calls, chroma selection, prompt-shaping, and crop chaining.
**You** (1) ask the user for a quality tier first, and (2) view `/crop`'s checkerboard
composites at the end to confirm clean cutouts.

## When to use
- "generate / make / draw an image of …" → GENERATE
- "edit / restyle / change this image" (+ a file) → EDIT
- "animate …", "walk cycle", "sprite sheet", "N frames of …" → ANIMATE
- anything that should end up transparent (logos, sprites, stickers, game assets)

## Setup
```bash
pip install openai pillow            # python-dotenv optional; rembg+numpy for /crop
```
- API key (`OPENAI_API_KEY`): read from the environment, then from a `.env` in the skill
  folder, the shared `.env` next to the skills folder, `~/.claude/.env`, or `~/Documents/.env`
  (point `SKILL_ENV_FILE` at any `.env` to override). **Never** hardcoded, never printed.
- Pairs with the `/crop` skill (`../crop/crop.py`, resolved relative to this skill) for
  keying/slicing.

## STEP 1 — QUALITY GATE (do this every run, before anything else)
If the user didn't specify a quality tier, **ask them** (use the question UI) and show prices:

| tier | ~price/image | use for |
|------|-------------|---------|
| `low` | ~$0.006 | drafts / iteration |
| `medium` | ~$0.053 | general work |
| `high` | ~$0.211 | final assets |

Then pass the choice as `--quality`. `image.py` **refuses to run without it** (prints the
menu and exits) so cost is never silently incurred.

## Usage
```bash
python image.py "<prompt>" --quality <low|medium|high> [options]
```

| flag | meaning |
|------|---------|
| `--image <path>` | EDIT mode (restyle/modify an existing image) |
| `--frames N` | ANIMATE mode — N frames |
| `--separate` | animate frame-by-frame (each frame edited from the previous for consistency) instead of one sheet |
| `--cols C` / `--rows R` | sheet layout (default: single row of N) |
| `--size WxH` | `1024x1024` / `1024x1536` / `1536x1024`; any other ratio maps to nearest (and tells you) |
| `--transparent` / `--opaque` | force chroma+crop on/off (sprites default to transparent) |
| `--chroma "#RRGGBB"` | explicit chroma color (else auto-picked, subject-aware) |
| `--subject-colors "#a,#b"` | GENERATE-mode hint: the subject's likely colors, so chroma avoids them |
| `--n N` | number of images (GENERATE only) |
| `--outdir DIR` / `--name BASE` | output location / base filename |
| `--no-crop` | generate only; print the `/crop` command but don't run it |

## SIZE
Only three sizes exist: **1024×1024** (square), **1024×1536** (portrait), **1536×1024**
(landscape). Other ratios are mapped to the nearest by aspect ratio and the choice is
reported. Animations default to landscape (good for a row of frames).

## CHROMA BACKGROUND RULE (any transparent-bound asset)
gpt-image-2 cannot output transparency, so the subject is rendered on a **flat solid
color** that `/crop` keys out. The color must appear **nowhere** on the subject:
1. **Subject colors** — EDIT/separate-from-image: `image.py` samples the input image's
   palette. GENERATE: pass `--subject-colors` (you infer them from the prompt).
2. **Pick maximally-distant vivid color** from a candidate set (magenta, electric blue,
   hot pink, cyan, orange, yellow, purple). **Green is demoted to last** — it lands on
   foliage/clothing/eyes and destroys the key. Candidates that appear on the subject (or
   are too close to a subject color) are rejected.
3. The chosen color is injected into the prompt verbatim: *"solid uniform flat <color>
   background, no gradient, no shadows on the background, no rim-light/props in that color;
   this exact color must appear NOWHERE on the subject."*
4. The chosen hex is printed and passed downstream as `/crop --chroma <hex>`.

## THREE MODES (auto-detected)
1. **GENERATE** — prompt only → `images.generate`.
2. **EDIT** — `--image` + prompt → `images.edit`.
3. **ANIMATE** — `--frames N`:
   - **default (sheet)**: ONE image with all N frames in a row/grid, with **uniform chroma
     gutters** between frames, identical subject scale + shared baseline, frame count &
     layout stated in the prompt — so `/crop` slices cleanly with no bleed.
   - **`--separate`**: frame 1 via `images.generate`, frames 2..N via `images.edit` each
     fed the **previous frame** for character consistency (one PNG per frame).

## AUTO-CHAIN TO /crop
For transparent assets, `image.py` runs `/crop` automatically (unless `--no-crop`):
- **sheet** → `crop.py <sheet> --chroma <hex> --frames N [--cols C --rows R] --spritesheet`
- **separate** → `crop.py <frames_dir> --chroma <hex> --spritesheet`
- **single** → `crop.py <img> --chroma <hex>`

`/crop` slices on the gutters, keys the chroma, validates each frame and cross-frame
consistency, and writes transparent PNGs + checkerboard composites. **After the run, Read
those composites** (path printed by /crop) to confirm: right subject, no halo, no clipped
limb, no neighbor-fragment leak. If a frame is bad, regenerate the flagged indices.

## OUTPUT
Saved PNG(s) plus a summary: size used, quality tier, chosen chroma hex, rough cost
estimate (per-image price × count), and the exact `/crop` command run or to run next.

## Examples
```bash
# 1) draft generate, opaque (no transparency needed)
python image.py "a cozy reading nook, warm light" --quality low --opaque

# 2) final transparent product shot; subject is mostly blue/white so chroma avoids them
python image.py "a glossy blue ceramic mug, product shot" --quality high \
    --transparent --subject-colors "#1E5BFF,#FFFFFF"

# 3) restyle an existing logo to neon, keep it transparent
python image.py "make this logo glow neon at night" --image logo.png --quality medium --transparent

# 4) 6-frame walk-cycle sprite SHEET -> auto-sliced to aligned transparent frames
python image.py "pixel-art knight walk cycle, side view" --frames 6 --quality medium

# 5) 4-frame animation, frame-by-frame for tight character consistency
python image.py "a flapping cartoon bird" --frames 4 --separate --quality medium
```

## Notes
- gpt-image models always return base64; `image.py` decodes and saves PNGs.
- Cost figures are approximate per-image prices; actual billing varies with size/quality.
- Verified against the OpenAI Python SDK (`images.generate` / `images.edit`) — params:
  `model, prompt, size, quality, n` (+ `image` for edits). `gpt-image-2` is a current model.
```
