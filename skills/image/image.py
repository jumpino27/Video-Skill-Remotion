#!/usr/bin/env python3
"""
image.py — generate / edit / animate images with the OpenAI Images API
(model: gpt-image-2), then auto-chain transparent assets to the /crop skill.

Modes (auto-detected):
  GENERATE  prompt only                  -> images.generate
  EDIT      --image <path> + prompt       -> images.edit
  ANIMATE   --frames N (+ prompt)          -> one in-image SHEET (default) with
            uniform chroma gutters, OR --separate frame-by-frame via edits that
            feed the previous frame for character consistency.

Key rules baked in:
  * QUALITY GATE: refuses to run without --quality (low|medium|high); prints the
    price menu so the caller (or the skill) can ask the user first.
  * SIZE: only 1024x1024 / 1024x1536 / 1536x1024; any other ratio maps to nearest.
  * CHROMA: transparent-bound assets are rendered on a flat solid color chosen to
    be ABSENT from the subject (never blindly green), injected into the prompt,
    and passed downstream to /crop --chroma <hex>.

API key (OPENAI_API_KEY): read from the environment, then from a .env (skill
folder, the shared skills .env, ~/.claude/.env, or SKILL_ENV_FILE). Never hardcoded.

Usage:
  python image.py "<prompt>" --quality medium
  python image.py "<prompt>" --image in.png --quality high            # edit
  python image.py "<prompt>" --frames 6 --quality low --transparent   # sheet
  python image.py "<prompt>" --frames 6 --separate --quality medium   # frame-by-frame
"""

import argparse
import base64
import datetime as _dt
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

# ----------------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent          # <skill>/image
SKILLS_DIR = HERE.parent                          # parent of all skills (e.g. ~/.claude/skills)
MODEL = "gpt-image-2"

# approximate per-image prices (USD) by quality tier
PRICES = {"low": 0.006, "medium": 0.053, "high": 0.211}

VALID_SIZES = ("1024x1024", "1024x1536", "1536x1024")  # square, portrait, landscape

# vivid chroma candidates, name -> RGB. Green is LAST on purpose (it shows up on
# foliage/clothing/eyes far too often and ruins the key).
CHROMA_CANDIDATES = [
    ("magenta",       (255, 0, 255)),
    ("electric blue", (0, 90, 255)),
    ("hot pink",      (255, 20, 147)),
    ("cyan",          (0, 255, 255)),
    ("orange",        (255, 122, 0)),
    ("yellow",        (255, 225, 0)),
    ("purple",        (138, 43, 226)),
    ("green",         (0, 255, 0)),   # last resort
]

CROP_PY = Path(__file__).resolve().parent.parent / "crop" / "crop.py"


def log(msg):
    print(msg, flush=True)


def err(msg):
    print(msg, file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------
# api key
# ----------------------------------------------------------------------------
def _env_files():
    """.env files to search, in order. Override with SKILL_ENV_FILE."""
    home = Path.home()
    files = []
    if os.environ.get("SKILL_ENV_FILE"):
        files.append(Path(os.environ["SKILL_ENV_FILE"]))
    files += [
        HERE / ".env",                  # skill-local .env
        SKILLS_DIR / ".env",            # shared .env next to the skills folder
        home / ".claude" / ".env",      # user-global Claude .env
        home / "Documents" / ".env",    # legacy fallback
    ]
    return files


def load_api_key():
    # 1) process env var wins
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    # 2) walk the candidate .env files (manual parse — no hard dependency on dotenv)
    for envp in _env_files():
        try:
            if not envp.exists():
                continue
        except OSError:
            continue
        for line in envp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "OPENAI_API_KEY":
                v = v.strip().strip("'\"")
                if v:
                    return v
    err("ERROR: OPENAI_API_KEY not found. Set it in the environment or add it to a .env "
        "(skill folder, ~/.claude/.env, or point SKILL_ENV_FILE at one).")
    raise SystemExit(2)


# ----------------------------------------------------------------------------
# color helpers / chroma selection
# ----------------------------------------------------------------------------
def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def sample_image_colors(path, n=16):
    """Return a list of dominant RGB colors from an image (edit mode)."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((128, 128))
    pal = im.quantize(colors=n, method=Image.MEDIANCUT).convert("RGB")
    arr = list(pal.getdata())
    # unique-ish
    seen, out = set(), []
    for c in arr:
        key = (c[0] // 16, c[1] // 16, c[2] // 16)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def color_present_in_image(path, rgb, thr=70, frac_limit=0.004):
    """True if `rgb` occupies more than frac_limit of the image's pixels."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((160, 160))
    px = list(im.getdata())
    hits = sum(1 for c in px if _dist(c, rgb) <= thr)
    return (hits / max(1, len(px))) > frac_limit


def pick_chroma(subject_rgbs, image_path=None):
    """Pick the vivid candidate maximally distant from every subject color and
    verified absent from the subject. Returns (name, rgb, hex)."""
    best, best_score = None, -1.0
    for name, rgb in CHROMA_CANDIDATES:
        if image_path and color_present_in_image(image_path, rgb):
            continue  # appears on the subject -> unusable
        dmin = min((_dist(rgb, s) for s in subject_rgbs), default=441.7)
        if subject_rgbs and dmin < 80:
            continue  # too close to a subject color
        score = dmin - (80 if name == "green" else 0)  # demote green
        if score > best_score:
            best, best_score = (name, rgb), score
    if best is None:
        best = ("magenta", (255, 0, 255))  # safe fallback
    name, rgb = best
    return name, rgb, rgb_to_hex(rgb)


# ----------------------------------------------------------------------------
# size mapping
# ----------------------------------------------------------------------------
def resolve_size(requested, animate):
    """Map a requested size/ratio onto one of the 3 supported sizes."""
    if requested is None:
        return ("1536x1024" if animate else "1024x1024"), False
    r = requested.lower().strip()
    if r in VALID_SIZES:
        return r, False
    # parse WxH or W:H
    m = re.match(r"^(\d+)[x:](\d+)$", r)
    if not m:
        return ("1536x1024" if animate else "1024x1024"), True
    w, h = int(m.group(1)), int(m.group(2))
    ratio = w / h
    if ratio > 1.15:
        mapped = "1536x1024"
    elif ratio < 0.87:
        mapped = "1024x1536"
    else:
        mapped = "1024x1024"
    return mapped, (mapped != r)


# ----------------------------------------------------------------------------
# prompt augmentation
# ----------------------------------------------------------------------------
def chroma_clause(color_name, hexv):
    return (f"Place the subject on a solid uniform flat {color_name} ({hexv}) "
            f"background — no gradient, no shadows cast on the background, no "
            f"rim-light, reflections, or props in that color; this exact color "
            f"must appear NOWHERE on the subject.")


def sheet_clause(frames, cols, rows, color_name, hexv):
    layout = (f"a single horizontal row of {frames} frames" if rows == 1
              else f"a {cols}x{rows} grid of {frames} frames")
    return (f"Render an animation sprite sheet as {layout}. Leave clear, uniform "
            f"empty SPACING (gutters) between every frame, and fill those gutters "
            f"with the same flat {color_name} ({hexv}) background color so the "
            f"frames can be sliced apart cleanly without bleeding into each other. "
            f"Keep the subject at an identical scale and on a shared baseline in "
            f"every frame; only the animated motion changes between frames.")


# ----------------------------------------------------------------------------
# OpenAI calls
# ----------------------------------------------------------------------------
def get_client(api_key):
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def _save_b64(b64, path):
    path.write_bytes(base64.b64decode(b64))


def api_generate(client, prompt, size, quality, n=1):
    resp = client.images.generate(model=MODEL, prompt=prompt, size=size,
                                  quality=quality, n=n)
    return [d.b64_json for d in resp.data]


def api_edit(client, image_path, prompt, size, quality):
    with open(image_path, "rb") as f:
        resp = client.images.edit(model=MODEL, image=f, prompt=prompt,
                                   size=size, quality=quality, n=1)
    return resp.data[0].b64_json


# ----------------------------------------------------------------------------
# crop chaining
# ----------------------------------------------------------------------------
def build_crop_cmd(target, hexv, frames=None, cols=None, rows=None,
                   spritesheet=False, size=None, anchor=None):
    cmd = ["python", str(CROP_PY), str(target), "--chroma", hexv]
    if frames:
        cmd += ["--frames", str(frames)]
    if cols:
        cmd += ["--cols", str(cols)]
    if rows:
        cmd += ["--rows", str(rows)]
    if spritesheet:
        cmd += ["--spritesheet"]
    if size:
        cmd += ["--size", size]
    if anchor:
        cmd += ["--anchor", anchor]
    return cmd


def run_crop(cmd):
    log("\n>>> auto-chaining to /crop:\n    " + " ".join(cmd))
    if not CROP_PY.exists():
        err(f"WARN: crop.py not found at {CROP_PY}; skipping auto-crop. "
            f"Run the command above once /crop is installed.")
        return None
    return subprocess.run(cmd).returncode


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def slugify(text, maxwords=6):
    words = re.findall(r"[A-Za-z0-9]+", text.lower())[:maxwords]
    return "_".join(words) or "image"


def quality_menu():
    return ("Quality is unspecified. Choose a tier (pass via --quality):\n"
            f"  low     ~${PRICES['low']:.3f}/image   (drafts / iteration)\n"
            f"  medium  ~${PRICES['medium']:.3f}/image  (general work)\n"
            f"  high    ~${PRICES['high']:.3f}/image  (final assets)")


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="OpenAI gpt-image-2 generate/edit/animate -> /crop")
    ap.add_argument("prompt", help="text prompt / description")
    ap.add_argument("--quality", choices=["low", "medium", "high"],
                    help="REQUIRED price/quality tier (gate asks if omitted)")
    ap.add_argument("--image", help="input image path -> EDIT mode")
    ap.add_argument("--frames", type=int, help="frame count -> ANIMATE mode")
    ap.add_argument("--separate", action="store_true",
                    help="animate frame-by-frame (one file per frame) instead of one sheet")
    ap.add_argument("--cols", type=int, help="sheet columns (default: single row)")
    ap.add_argument("--rows", type=int, help="sheet rows (default 1)")
    ap.add_argument("--size", help="1024x1024 | 1024x1536 | 1536x1024 (other ratios map to nearest)")
    ap.add_argument("--transparent", dest="transparent", action="store_true",
                    help="asset is meant to be keyed transparent -> apply chroma + auto-crop")
    ap.add_argument("--opaque", dest="transparent", action="store_false",
                    help="force NO chroma / no crop chaining")
    ap.set_defaults(transparent=None)
    ap.add_argument("--chroma", help="explicit chroma hex (else auto-picked, subject-aware)")
    ap.add_argument("--subject-colors", help="comma-sep hex list of subject colors (generate mode hint)")
    ap.add_argument("--n", type=int, default=1, help="number of images (generate mode only)")
    ap.add_argument("--outdir", default=".", help="output directory")
    ap.add_argument("--name", help="output base name (default: slug of prompt)")
    ap.add_argument("--anchor", choices=["auto", "center", "bottom", "preserve"],
                    help="forward frame alignment to /crop (default: /crop auto-detects motion)")
    ap.add_argument("--no-crop", action="store_true", help="do not auto-run /crop")
    args = ap.parse_args()

    # ---- QUALITY GATE (first thing) ----
    if not args.quality:
        log(quality_menu())
        choice = None
        if sys.stdin.isatty():
            try:
                choice = input("quality [low/medium/high]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = None
        if choice in PRICES:
            args.quality = choice
        else:
            err("\nAborting: re-run with --quality low|medium|high "
                "(ask the user to pick a tier first).")
            raise SystemExit(2)

    # ---- mode detection ----
    animate = bool(args.frames and args.frames > 1)
    edit = bool(args.image) and not animate
    mode = "animate" if animate else ("edit" if args.image else "generate")

    # ---- transparency default by mode ----
    transparent = args.transparent
    if transparent is None:
        transparent = animate or bool(args.chroma)  # sprites default to transparent

    # ---- size ----
    size, mapped = resolve_size(args.size, animate)
    if mapped:
        log(f"NOTE: requested size '{args.size}' is not supported; mapped to nearest -> {size}")

    # ---- layout for animation ----
    cols = args.cols
    rows = args.rows
    if animate and not args.separate:
        if not cols and not rows:
            cols, rows = args.frames, 1
        elif cols and not rows:
            rows = -(-args.frames // cols)
        elif rows and not cols:
            cols = -(-args.frames // rows)

    # ---- chroma selection (subject-aware) ----
    chroma_name = chroma_hex = None
    if transparent:
        if args.chroma:
            chroma_hex = "#" + args.chroma.lstrip("#").upper()
            chroma_name = "specified"
        else:
            subj = []
            if args.subject_colors:
                subj = [hex_to_rgb(c) for c in args.subject_colors.split(",") if c.strip()]
            img_for_sampling = args.image if (edit or (animate and args.image)) else None
            if img_for_sampling:
                subj += sample_image_colors(img_for_sampling)
            chroma_name, _rgb, chroma_hex = pick_chroma(subj, img_for_sampling)
        log(f"Chroma background: {chroma_hex}" + (f" ({chroma_name})" if chroma_name else ""))

    # ---- build prompt ----
    prompt = args.prompt
    if transparent:
        if animate and not args.separate:
            prompt = (f"{prompt}\n\n{sheet_clause(args.frames, cols, rows, chroma_name, chroma_hex)}"
                      f"\n{chroma_clause(chroma_name, chroma_hex)}")
        else:
            prompt = f"{prompt}\n\n{chroma_clause(chroma_name, chroma_hex)}"

    # ---- run ----
    api_key = load_api_key()
    client = get_client(api_key)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    base = args.name or slugify(args.prompt)

    log(f"\nMode: {mode}  |  model: {MODEL}  |  size: {size}  |  quality: {args.quality}")
    outputs = []
    count = 0

    try:
        if mode == "generate":
            b64s = api_generate(client, prompt, size, args.quality, n=args.n)
            count = len(b64s)
            if count == 1:
                p = outdir / f"{base}.png"
                _save_b64(b64s[0], p)
                outputs.append(p)
            else:
                for i, b in enumerate(b64s, 1):
                    p = outdir / f"{base}_{i:02d}.png"
                    _save_b64(b, p)
                    outputs.append(p)

        elif mode == "edit":
            b64 = api_edit(client, args.image, prompt, size, args.quality)
            count = 1
            p = outdir / f"{base}_edited.png"
            _save_b64(b64, p)
            outputs.append(p)

        elif mode == "animate" and not args.separate:
            # one IN-IMAGE sheet
            b64s = api_generate(client, prompt, size, args.quality, n=1)
            count = 1
            p = outdir / f"{base}_sheet.png"
            _save_b64(b64s[0], p)
            outputs.append(p)

        elif mode == "animate" and args.separate:
            # frame-by-frame; frame 1 generated, 2..N edited from previous
            frame_dir = outdir / f"{base}_frames"
            frame_dir.mkdir(parents=True, exist_ok=True)
            base_prompt = args.prompt
            chroma_tail = ("\n\n" + chroma_clause(chroma_name, chroma_hex)) if transparent else ""
            f1 = api_generate(client, f"{base_prompt}\n\nAnimation frame 1 of {args.frames}."
                              + chroma_tail, size, args.quality, n=1)[0]
            prev = frame_dir / "frame_001.png"
            _save_b64(f1, prev)
            outputs.append(prev)
            count = 1
            for i in range(2, args.frames + 1):
                fb = api_edit(client, prev,
                              f"{base_prompt}\n\nThis is animation frame {i} of {args.frames}; "
                              f"keep the SAME character, identical scale and baseline as the "
                              f"provided previous frame, advance the motion by one step."
                              + chroma_tail,
                              size, args.quality)
                cur = frame_dir / f"frame_{i:03d}.png"
                _save_b64(fb, cur)
                outputs.append(cur)
                prev = cur
                count += 1
    except Exception as e:
        err(f"\nERROR: OpenAI Images API call failed: {e}")
        raise SystemExit(1)

    # ---- summary ----
    est = PRICES[args.quality] * count
    log("\n" + "=" * 60)
    log("IMAGE SUMMARY")
    log("=" * 60)
    log(f"  size used     : {size}")
    log(f"  quality tier  : {args.quality}  (~${PRICES[args.quality]:.3f}/image)")
    log(f"  images billed : {count}")
    log(f"  est. cost     : ~${est:.3f}")
    log(f"  chroma hex    : {chroma_hex if transparent else '(opaque - no chroma)'}")
    log("  outputs:")
    for o in outputs:
        log(f"    {o}")

    # ---- auto-chain to /crop ----
    crop_cmd = None
    if transparent and outputs:
        if mode == "animate" and not args.separate:
            crop_cmd = build_crop_cmd(outputs[0], chroma_hex, frames=args.frames,
                                      cols=cols, rows=rows, spritesheet=True, anchor=args.anchor)
        elif mode == "animate" and args.separate:
            crop_cmd = build_crop_cmd(outputs[0].parent, chroma_hex, spritesheet=True,
                                      anchor=args.anchor)
        else:
            crop_cmd = build_crop_cmd(outputs[0], chroma_hex, anchor=args.anchor)

    if crop_cmd:
        log("\n  /crop command:")
        log("    " + " ".join(crop_cmd))
        if not args.no_crop:
            run_crop(crop_cmd)
            log("\n  NOTE: now VIEW the checkerboard composites /crop wrote "
                "(its gate_dir) to confirm clean cutouts before using the assets.")
    elif transparent:
        log("\n  (no crop command built)")

    raise SystemExit(0)


if __name__ == "__main__":
    _ = _dt  # reserved for future timestamped names
    main()
