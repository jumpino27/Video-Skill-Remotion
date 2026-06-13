---
name: crop
description: >-
  Cut subjects out of generated images and turn them into clean transparent PNGs
  or aligned sprite sequences. Use when the user wants to remove/knock out a
  background, make something transparent, isolate or "crop out" a subject,
  chroma-key a flat background, slice a sprite sheet / frame strip into frames,
  or prep cutouts/sprites that line up. Pairs with the /image skill (which is
  told to render subjects on a flat keyable background with gutters between
  frames). Runs rembg (birefnet-general) + Pillow + numpy, validates every frame,
  and produces a checkerboard composite for a visual gate.
---

# crop

Background removal + sprite-sheet slicing + per-frame validation, in one script.
`crop.py` does the pixel work; **you** perform the visual gate by viewing the
checkerboard composites it writes.

## When to use
- "make this transparent", "remove the background", "knock out / cut out X"
- "isolate the <object>" → use `--prompt "<object>"` (precision tier)
- "the background is a flat green/#00FF00" → use `--chroma "#00FF00"`
- "slice this sprite sheet / frame strip into frames"
- "give me aligned sprite frames" / "pack a spritesheet"

## Setup (first run)
```bash
pip install "rembg[cpu]" pillow numpy
```
The default model `birefnet-general` downloads automatically on first run.
GPU users can `pip install "rembg[gpu]"`. On this Windows box, call the script with
`python crop.py ...` (or `py crop.py ...`).

## Usage
```bash
python crop.py <input(file|dir|sheet)> [--prompt "..."] [--chroma "#RRGGBB"] \
    [--frames N] [--cols C] [--rows R] [--size 1024x1024] [--pad 0.08] \
    [--auto-redo] [--spritesheet]
```

`INPUT` is one of:
- **one image** → `<name>_cropped.png`
- **a folder of frames** → `frame_001.png … frame_NNN.png` (sorted by filename)
- **one sheet/strip image holding many frames** → sliced, then `frame_001.png …`

A single image is treated as a **sheet** only when you pass a slicing hint
(`--frames`, `--cols`, or `--rows`). Otherwise it's a single cutout.

### Flags
| flag | meaning |
|------|---------|
| `--prompt "red car"` | route through Grounded-SAM-2 to isolate that object (precision tier; degrades to rembg if not installed) |
| `--chroma "#RRGGBB"` | ALSO chroma-key this exact flat color — a clean fallback/refinement that kills colored halos. Use the same color the /image skill was told to render |
| `--frames N` | number of frames in a sheet (assumes a horizontal strip if no `--cols/--rows`) |
| `--cols C` / `--rows R` | explicit grid for a sheet |
| `--size 1024x1024` | output canvas per frame (default 1024×1024) |
| `--pad 0.08` | padding fraction inside the canvas (~8%) |
| `--anchor auto` | multi-frame alignment: `auto` (default) analyzes the motion and picks; `center` (each frame centered); `bottom` (baseline-aligned grounded squash/stretch); `preserve` (keep in-frame motion like a bounce/jump) |
| `--auto-redo` | re-run rembg/keying (alpha-matting on) for flagged frames — **separate-file/dir mode only** |
| `--spritesheet` | also pack cropped frames into one horizontal sheet with uniform spacing |
| `--model NAME` | override rembg model (default `birefnet-general`) |
| `--outdir DIR` | output directory (default: next to the input) |

## What the script does (per frame)
1. **Cutout** — rembg `birefnet-general` → RGBA. If `--chroma`, also key that color.
   If `--prompt`, route through Grounded-SAM-2 first.
2. **Sheet slicing** (sheet input) — detect uniform gutters (rows/cols of near-constant
   background or `--chroma` color) and cut on them. This relies on the spacing the
   /image skill adds so one frame's cutout can't grab a sliver of its neighbor. If
   gutters can't be confirmed it falls back to an even `--cols/--rows` grid and **WARNs**.
3. **Validation** (every frame must pass):
   1. alpha exists; foreground covers ~3–95% of pixels
   2. exactly one dominant connected component (tiny specks ignored)
   3. subject bbox does **not** touch all four edges (would mean clipped)
   4. if `--chroma`: residual chroma-hue pixels along the cutout edge are below a
      small threshold (confirms a clean key, no colored halo)
4. **Cross-frame consistency** (multi-frame) — per frame: bbox (w,h), center, coverage.
   Any frame deviating **>12%** from the set median is flagged (the signature of a bad
   lasso that would make a sprite jitter). With `--auto-redo` it re-runs the flagged
   frames (separate-file mode); for sliced sheets it instead reports exactly which
   frame indices `/image` should regenerate.
5. **Placement (motion-aware)** — every frame is composited onto the **same** fully
   transparent canvas at `--size` (aspect preserved, never stretched, `--pad` margin) so
   the sequence stays aligned. For multi-frame sets, `--anchor auto` inspects how the
   subject moves/resizes across frames and picks:
   - **center** — subject barely moves → shape-only or code-driven motion; each frame
     centered (independent fit). Best when your game sets the sprite's position.
   - **bottom** — bottom edge stays put while size/top vary → grounded squash/stretch;
     baseline-aligned with a **shared scale** so the squash survives. Best for
     feet-on-ground / platformer sprites.
   - **preserve** — subject translates across frames → airborne motion (bounce/jump);
     keeps each frame's in-frame position + relative size (shared scale). Best when the
     vertical/positional motion IS the animation.
   Force a specific mode with `--anchor center|bottom|preserve`. In `bottom`/`preserve`
   mode, the cross-frame consistency flags are downgraded to advisory (position/size
   changes are the intended motion, not bad cutouts).

## VISUAL GATE — you must do this (validation step 5)
The script composites each cutout onto a generated checkerboard and writes it to the
system temp dir — `<temp>/crop_skill/gates/gate_frame_NNN.png` — printing that path
(also in the JSON `gate_dir` / per-frame `checker`). After running, **Read those images**
and confirm by eye:
- correct subject is kept,
- no background halo / colored fringe,
- no clipped limb or edge,
- **no fragment of a neighboring frame leaked in** (sheet slicing).

Only report success once the composites look clean. If a frame looks wrong, re-run with
`--chroma`, `--auto-redo`, or a tighter grid — or (sheets) ask `/image` to regenerate the
flagged indices.

## Output & exit code
- `<name>_cropped.png` (single) or `frame_001.png…` (sequence), next to the input
  (or in `--outdir`)
- `spritesheet.png` with `--spritesheet`
- checkerboard composites in `<temp>/crop_skill/gates/gate_frame_NNN.png`
- a human PASS/FAIL + consistency summary, then a `=== JSON ===` block (parse this for
  `flagged_1based` / `regenerate_1based` / per-frame `checker` paths)
- exit `0` if all frames pass their gates, `1` if any frame fails a gate,
  `2` on setup/usage errors (missing input, rembg not installed)

## Precision tier — Grounded-SAM-2 (optional, document don't hard-install)
For pinpoint isolation of a *specific* object via `--prompt`, install
[Grounded-SAM-2](https://github.com/IDEA-Research/Grounded-SAM-2) (heavy: PyTorch +
GroundingDINO + SAM-2 checkpoints; not a clean pip package). `crop.py` looks for a
user-supplied shim module `grounded_sam2_shim` on `PYTHONPATH` exposing:
```python
def segment(image_rgb: "np.ndarray", text_prompt: str) -> "np.ndarray":  # HxW bool mask
    ...
```
If the shim is absent, `--prompt` degrades gracefully to rembg and warns — the rest of
the pipeline (chroma key, validation, placement) is unaffected.

## Examples
```bash
# single subject, generated on flat magenta
python crop.py hero.png --chroma "#FF00FF"

# 8-frame horizontal walk strip -> aligned 512px frames + a packed sheet
python crop.py walk_strip.png --frames 8 --size 512x512 --spritesheet --chroma "#00FF00"

# 4x2 grid sheet, auto-detect gutters, report any inconsistent cells to regenerate
python crop.py sheet.png --cols 4 --rows 2 --chroma "#00FF00"

# folder of separately-rendered frames, auto-fix the jittery ones
python crop.py ./frames --auto-redo --size 1024x1024

# isolate one object out of a busy scene
python crop.py scene.png --prompt "the red sports car"
```
