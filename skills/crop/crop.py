#!/usr/bin/env python3
"""
crop.py — cut subjects out of generated images and turn them into clean
transparent PNGs or aligned sprite sequences.

Pipeline per run:
  1. RESOLVE INPUT  -> single image | folder of frames | one sheet/strip image
  2. SLICE          -> if a sheet, detect uniform gutters and slice into cells
  3. CUTOUT         -> rembg (birefnet-general) + optional chroma key + optional
                       Grounded-SAM-2 prompt routing
  4. VALIDATE       -> 5 per-frame gates (alpha, single blob, no clip, clean key,
                       checkerboard composite for the visual gate)
  5. CONSISTENCY    -> flag frames that deviate >12% from the set median
  6. PLACE          -> trim to alpha bbox, center on a shared transparent canvas
  7. OUTPUT         -> <name>_cropped.png / frame_NNN.png (+ optional spritesheet)

Usage:
  python crop.py <input(file|dir|sheet)> [--prompt "..."] [--chroma "#RRGGBB"]
       [--frames N] [--cols C] [--rows R] [--size 1024x1024] [--pad 0.08]
       [--auto-redo] [--spritesheet]

Deps:  rembg (model birefnet-general), Pillow, numpy.
Optional precision tier (NOT auto-installed): Grounded-SAM-2 for --prompt routing.
"""

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

# ----------------------------------------------------------------------------
# constants / tunables
# ----------------------------------------------------------------------------
DEFAULT_MODEL = "birefnet-general"
ALPHA_FG_THRESH = 128          # alpha value above which a pixel counts as foreground
COVERAGE_MIN = 0.03            # foreground must cover >= 3% of the frame
COVERAGE_MAX = 0.95            # ... and <= 95%
SPECK_FRACTION = 0.01          # components smaller than 1% of fg area are "specks"
CONSISTENCY_TOL = 0.12         # 12% deviation from the median flags a frame
CHROMA_DIST = 60               # RGB euclidean distance treated as "the key color"
CHROMA_EDGE_RESIDUAL_MAX = 0.04  # fraction of edge pixels allowed near the key hue
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

TMPDIR = Path(tempfile.gettempdir()) / "crop_skill"


def log(msg):
    print(msg, flush=True)


def warn(msg):
    print(f"WARN: {msg}", file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------
# rembg session (lazy, cached)
# ----------------------------------------------------------------------------
_REMBG_SESSION = None


def get_rembg_session(model=DEFAULT_MODEL):
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        try:
            from rembg import new_session
        except ImportError as e:
            log("ERROR: rembg is not installed. Install with: pip install rembg")
            raise SystemExit(2) from e
        _REMBG_SESSION = new_session(model)
    return _REMBG_SESSION


def rembg_cutout(img_rgb, model=DEFAULT_MODEL):
    """Run rembg and return an RGBA PIL image."""
    from rembg import remove
    out = remove(img_rgb.convert("RGB"), session=get_rembg_session(model))
    return out.convert("RGBA")


# ----------------------------------------------------------------------------
# chroma key
# ----------------------------------------------------------------------------
def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"bad hex color: {h!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def chroma_mask(img_rgb, key_rgb, dist=CHROMA_DIST):
    """Boolean array, True where a pixel is within `dist` of the key color."""
    arr = np.asarray(img_rgb.convert("RGB"), dtype=np.int16)
    diff = arr - np.array(key_rgb, dtype=np.int16)
    d = np.sqrt((diff.astype(np.float32) ** 2).sum(axis=2))
    return d <= dist


def apply_chroma(rgba, img_rgb, key_rgb, dist=CHROMA_DIST):
    """Zero alpha wherever the source pixel matches the key color.

    Used as a clean fallback/refinement when the background was generated as a
    known flat color by the /image skill.
    """
    keyed = chroma_mask(img_rgb, key_rgb, dist)
    arr = np.array(rgba)
    arr[..., 3][keyed] = 0
    return Image.fromarray(arr, "RGBA")


# ----------------------------------------------------------------------------
# Grounded-SAM-2 (optional precision tier)
# ----------------------------------------------------------------------------
def grounded_sam_cutout(img_rgb, prompt):
    """Route through Grounded-SAM-2 to isolate a specific prompted object.

    This is the optional precision tier and is NOT auto-installed. If the
    integration is not wired up locally we return None so the caller can fall
    back to rembg (+ chroma). See SKILL.md for how to install/wire GSAM-2.

    To enable: put a `grounded_sam2_shim.py` on PYTHONPATH exposing
        segment(image_rgb: np.ndarray, text_prompt: str) -> np.ndarray  # HxW mask
    """
    try:
        from grounded_sam2_shim import segment  # user-provided shim
    except Exception:
        return None
    try:
        rgb = np.asarray(img_rgb.convert("RGB"))
        mask = segment(rgb, prompt)
        alpha = (np.asarray(mask) > 0).astype(np.uint8) * 255
        arr = np.dstack([rgb, alpha])
        return Image.fromarray(arr, "RGBA")
    except Exception as e:
        warn(f"Grounded-SAM-2 failed ({e}); falling back.")
        return None


# ----------------------------------------------------------------------------
# connected components (numpy-only, union-find on a downscaled mask)
# ----------------------------------------------------------------------------
def _downscale_mask(mask, max_dim=256):
    h, w = mask.shape
    scale = max(h, w) / max_dim
    if scale <= 1:
        return mask
    nh, nw = max(1, int(h / scale)), max(1, int(w / scale))
    img = Image.fromarray((mask * 255).astype(np.uint8)).resize((nw, nh), Image.NEAREST)
    return np.asarray(img) > 127


def label_components(mask):
    """Return (labels, sizes_dict) using 4-connectivity. numpy/stdlib only."""
    small = _downscale_mask(mask)
    h, w = small.shape
    labels = np.zeros((h, w), dtype=np.int32)
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    nxt = 1
    for y in range(h):
        for x in range(w):
            if not small[y, x]:
                continue
            up = labels[y - 1, x] if y > 0 else 0
            left = labels[y, x - 1] if x > 0 else 0
            if up and left:
                labels[y, x] = min(up, left)
                union(up, left)
            elif up:
                labels[y, x] = up
            elif left:
                labels[y, x] = left
            else:
                labels[y, x] = nxt
                parent[nxt] = nxt
                nxt += 1

    sizes = {}
    nz = np.argwhere(labels > 0)
    for y, x in nz:
        r = find(int(labels[y, x]))
        sizes[r] = sizes.get(r, 0) + 1
    return labels, sizes


# ----------------------------------------------------------------------------
# geometry helpers
# ----------------------------------------------------------------------------
def alpha_bbox(rgba):
    """(left, top, right, bottom) of the alpha>thresh region, or None if empty."""
    a = np.asarray(rgba)[..., 3]
    ys, xs = np.where(a > ALPHA_FG_THRESH)
    if xs.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def frame_metrics(rgba):
    a = np.asarray(rgba)[..., 3]
    fg = a > ALPHA_FG_THRESH
    coverage = float(fg.mean())
    bb = alpha_bbox(rgba)
    if bb is None:
        return {"coverage": 0.0, "bbox": None, "w": 0, "h": 0, "cx": 0, "cy": 0}
    l, t, r, b = bb
    return {
        "coverage": coverage,
        "bbox": bb,
        "w": r - l,
        "h": b - t,
        "cx": (l + r) / 2.0,
        "cy": (t + b) / 2.0,
    }


# ----------------------------------------------------------------------------
# sheet slicing — detect uniform gutters
# ----------------------------------------------------------------------------
def _background_mask(img_rgb, chroma_rgb):
    """Per-pixel 'is background' mask: chroma color if given, else a near-uniform
    background color estimated from the 1px border."""
    if chroma_rgb is not None:
        return chroma_mask(img_rgb, chroma_rgb)
    arr = np.asarray(img_rgb.convert("RGB"), dtype=np.int16)
    border = np.concatenate([
        arr[0, :, :], arr[-1, :, :], arr[:, 0, :], arr[:, -1, :]
    ], axis=0)
    bg = np.median(border, axis=0)
    d = np.sqrt(((arr - bg).astype(np.float32) ** 2).sum(axis=2))
    return d <= CHROMA_DIST


def _gutter_runs(is_bg_line, min_run):
    """Given a 1-D boolean array (True = mostly-background line), return the
    [start, end) index ranges of background runs long enough to be gutters."""
    runs = []
    n = len(is_bg_line)
    i = 0
    while i < n:
        if is_bg_line[i]:
            j = i
            while j < n and is_bg_line[j]:
                j += 1
            if j - i >= min_run:
                runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def _cells_from_runs(length, runs):
    """Convert gutter runs into content spans (the gaps between gutters)."""
    spans = []
    prev = 0
    for s, e in runs:
        if s > prev:
            spans.append((prev, s))
        prev = e
    if prev < length:
        spans.append((prev, length))
    return [(a, b) for a, b in spans if b - a > 1]


def detect_grid(img_rgb, chroma_rgb, line_bg_frac=0.92):
    """Detect column/row content spans from uniform gutters.

    A column/row counts as a 'gutter line' if >= line_bg_frac of it is
    background. Returns (col_spans, row_spans); either may be one full span.
    """
    bg = _background_mask(img_rgb, chroma_rgb)
    h, w = bg.shape
    col_bg = bg.mean(axis=0) >= line_bg_frac
    row_bg = bg.mean(axis=1) >= line_bg_frac
    min_gut_w = max(2, int(w * 0.01))
    min_gut_h = max(2, int(h * 0.01))
    col_runs = _gutter_runs(col_bg, min_gut_w)
    row_runs = _gutter_runs(row_bg, min_gut_h)
    col_spans = _cells_from_runs(w, col_runs) or [(0, w)]
    row_spans = _cells_from_runs(h, row_runs) or [(0, h)]
    return col_spans, row_spans


def slice_sheet(img, chroma_rgb, frames, cols, rows):
    """Return a list of (index, PIL crop). Try gutter detection first; fall back
    to an even grid (cols/rows or derived from frames) with a WARN."""
    img_rgb = img.convert("RGB")
    col_spans, row_spans = detect_grid(img_rgb, chroma_rgb)
    detected = len(col_spans) * len(row_spans)

    # Prefer gutter detection unless the user pinned an explicit grid via
    # --cols/--rows, or gave --frames that disagrees with what we detected.
    use_detection = detected > 1
    if (cols or rows):
        use_detection = False
    elif frames and detected != frames:
        use_detection = False

    if use_detection:
        log(f"  gutter detection: {len(col_spans)} col(s) x {len(row_spans)} row(s) "
            f"= {detected} cell(s)")
        cells, idx = [], 0
        for (t, b) in row_spans:
            for (l, r) in col_spans:
                idx += 1
                cells.append((idx, img.crop((l, t, r, b))))
        return cells

    # ---- fallback: even grid ----
    w, h = img.size
    if not cols and not rows:
        if frames:
            cols, rows = frames, 1
        else:
            warn("could not detect gutters and no --frames/--cols/--rows given; "
                 "treating the whole image as a single frame.")
            return [(1, img)]
    if not cols:
        cols = int(np.ceil(frames / rows)) if (frames and rows) else 1
    if not rows:
        rows = int(np.ceil(frames / cols)) if (frames and cols) else 1
    warn(f"gutter detection unavailable/ambiguous; falling back to an even "
         f"{cols}x{rows} grid split (cells may capture slivers of neighbors).")
    cw, ch = w / cols, h / rows
    cells, idx = [], 0
    for ry in range(rows):
        for cx in range(cols):
            idx += 1
            if frames and idx > frames:
                break
            box = (int(cx * cw), int(ry * ch), int((cx + 1) * cw), int((ry + 1) * ch))
            cells.append((idx, img.crop(box)))
    return cells


# ----------------------------------------------------------------------------
# cutout dispatch
# ----------------------------------------------------------------------------
def make_cutout(img, prompt, chroma_rgb, model=DEFAULT_MODEL):
    img_rgb = img.convert("RGB")
    rgba = None
    if prompt:
        rgba = grounded_sam_cutout(img_rgb, prompt)
        if rgba is None:
            warn(f"--prompt given but Grounded-SAM-2 not wired up; using rembg"
                 f"{' + chroma' if chroma_rgb is not None else ''} for: {prompt!r}")
    if rgba is None:
        rgba = rembg_cutout(img_rgb, model)
    if chroma_rgb is not None:
        rgba = apply_chroma(rgba, img_rgb, chroma_rgb)
    return rgba


# ----------------------------------------------------------------------------
# validation gates
# ----------------------------------------------------------------------------
def edge_chroma_residual(rgba, img_rgb, chroma_rgb):
    """Fraction of just-inside-the-edge foreground pixels that still match the
    key hue (the signature of a colored halo). Lower is better."""
    from PIL import ImageFilter
    a = np.asarray(rgba)[..., 3] > ALPHA_FG_THRESH
    if a.sum() == 0:
        return 0.0
    am = Image.fromarray((a * 255).astype(np.uint8))
    eroded = np.asarray(am.filter(ImageFilter.MinFilter(5))) > 127
    edge_band = a & ~eroded
    if edge_band.sum() == 0:
        return 0.0
    keyed = chroma_mask(img_rgb, chroma_rgb)
    return float((edge_band & keyed).sum() / edge_band.sum())


def make_checkerboard(size, square=16):
    w, h = size
    c = np.zeros((h, w, 3), dtype=np.uint8)
    xi = (np.arange(w) // square)[None, :]
    yi = (np.arange(h) // square)[:, None]
    c[((xi + yi) % 2 == 0)] = 200
    c[((xi + yi) % 2 == 1)] = 120
    return Image.fromarray(c, "RGB").convert("RGBA")


def validate_frame(rgba, idx, chroma_rgb, img_rgb, gate_dir):
    """Run the 5 gates. Returns (ok: bool, issues: list[str], checker_path)."""
    issues = []
    a = np.asarray(rgba)[..., 3]
    fg = a > ALPHA_FG_THRESH

    # 1. alpha exists + coverage band
    if rgba.mode != "RGBA":
        issues.append("no alpha channel")
    cov = float(fg.mean())
    if cov < COVERAGE_MIN:
        issues.append(f"coverage {cov:.1%} < {COVERAGE_MIN:.0%} (subject too small/empty)")
    elif cov > COVERAGE_MAX:
        issues.append(f"coverage {cov:.1%} > {COVERAGE_MAX:.0%} (background not removed?)")

    # 2. exactly one dominant connected component
    if fg.sum() > 0:
        _, sizes = label_components(fg)
        total = sum(sizes.values())
        big = [s for s in sizes.values() if s >= SPECK_FRACTION * total]
        if len(big) == 0:
            issues.append("no solid component found")
        elif len(big) > 1:
            issues.append(f"{len(big)} dominant components (expected 1; fragmented cutout)")

    # 3. subject must not run along all four borders (a clipped silhouette, or
    #    background that was never removed). We measure foreground *along* each
    #    edge rather than bbox extent: a cleanly-sliced subject only touches its
    #    crop edges tangentially (a few px), so its min edge-coverage is tiny;
    #    a clipped/uncut subject has long foreground runs on every border.
    if fg.sum() > 0:
        edge_cov = [fg[0, :].mean(), fg[-1, :].mean(), fg[:, 0].mean(), fg[:, -1].mean()]
        # A cleanly-cut subject only touches its edges tangentially (low coverage
        # on at least one side). Heavy foreground on ALL FOUR borders means the
        # subject runs to every edge — uncut background or a boxed/clipped subject.
        if min(edge_cov) > 0.6:
            issues.append(f"subject runs along all four borders "
                          f"(min edge coverage {min(edge_cov):.0%}; clipped or uncut)")

    # 4. chroma edge residual
    if chroma_rgb is not None and fg.sum() > 0:
        res = edge_chroma_residual(rgba, img_rgb, chroma_rgb)
        if res > CHROMA_EDGE_RESIDUAL_MAX:
            issues.append(f"chroma halo: {res:.1%} of edge near key color "
                          f"(> {CHROMA_EDGE_RESIDUAL_MAX:.0%})")

    # 5. visual gate artifact: composite on checkerboard, save for review
    checker = make_checkerboard(rgba.size)
    comp = Image.alpha_composite(checker, rgba)
    gate_dir.mkdir(parents=True, exist_ok=True)
    checker_path = gate_dir / f"gate_frame_{idx:03d}.png"
    comp.convert("RGB").save(checker_path)

    return (len(issues) == 0), issues, str(checker_path)


# ----------------------------------------------------------------------------
# cross-frame consistency
# ----------------------------------------------------------------------------
def consistency_flags(metrics):
    """Return (set of flagged indices, detail dict). A frame is flagged if its
    size/coverage/center deviates > CONSISTENCY_TOL from the set median."""
    if len(metrics) < 2:
        return set(), {}

    def med(key):
        vals = [m[key] for m in metrics if m["bbox"] is not None]
        return float(np.median(vals)) if vals else 0.0

    medians = {k: med(k) for k in ("w", "h", "cx", "cy", "coverage")}
    flagged, detail = set(), {}
    for i, m in enumerate(metrics):
        if m["bbox"] is None:
            flagged.add(i)
            detail[i] = ["empty frame"]
            continue
        devs = []
        for k in ("w", "h", "coverage"):
            base = medians[k] or 1e-6
            dev = abs(m[k] - medians[k]) / base
            if dev > CONSISTENCY_TOL:
                devs.append(f"{k} off {dev:.0%}")
        span = max(medians["w"], medians["h"], 1.0)
        for k in ("cx", "cy"):
            dev = abs(m[k] - medians[k]) / span
            if dev > CONSISTENCY_TOL:
                devs.append(f"{k} shifted {dev:.0%}")
        if devs:
            flagged.add(i)
            detail[i] = devs
    return flagged, detail


# ----------------------------------------------------------------------------
# placement onto a shared transparent canvas
# ----------------------------------------------------------------------------
def place_on_canvas(rgba, size, pad):
    bb = alpha_bbox(rgba)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    if bb is None:
        return canvas
    cut = rgba.crop(bb)
    cw, ch = cut.size
    target_w = size[0] * (1 - 2 * pad)
    target_h = size[1] * (1 - 2 * pad)
    scale = min(target_w / cw, target_h / ch)  # preserve aspect, never stretch
    nw, nh = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    cut = cut.resize((nw, nh), Image.LANCZOS)
    ox = (size[0] - nw) // 2
    oy = (size[1] - nh) // 2
    canvas.alpha_composite(cut, (ox, oy))
    return canvas


# ----------------------------------------------------------------------------
# motion-aware sequence placement
# ----------------------------------------------------------------------------
def cell_relative_metrics(results):
    """Per-frame subject position WITHIN its own cell (cell coords), so we can
    tell how the subject moves/resizes across the sequence."""
    metas = []
    for r in results:
        cut = r["cutout"]
        W, H = cut.size
        bb = alpha_bbox(cut)
        if bb is None:
            metas.append(None)
            continue
        l, t, rr, b = bb
        metas.append({"W": W, "H": H, "l": l, "t": t, "r": rr, "b": b,
                      "cx": (l + rr) / 2 / W, "cy": (t + b) / 2 / H,
                      "by": b / H, "ty": t / H,
                      "w": (rr - l) / W, "h": (b - t) / H})
    return metas


def choose_anchor(metas):
    """Analyze the sequence and pick a placement mode.

    center   subject barely moves/resizes -> shape-only or code-driven motion
    bottom   bottom edge stays put while size/top vary -> grounded squash/stretch
    preserve subject translates across frames -> airborne motion (bounce/jump)
    Returns (mode, human_reason).
    """
    m = [x for x in metas if x]
    if len(m) < 2:
        return "center", "single subject"

    def spread(k):
        v = [x[k] for x in m]
        return max(v) - min(v)

    d_cy, d_cx, d_bottom = spread("cy"), spread("cx"), spread("by")
    hs = sorted(x["h"] for x in m)
    med_h = hs[len(hs) // 2] or 1e-6
    d_size = (max(hs) - min(hs)) / med_h

    if d_cy < 0.06 and d_cx < 0.06 and d_size < 0.12:
        return "center", f"subjects near-static (d_cy={d_cy:.0%}, d_size={d_size:.0%})"
    if d_bottom < 0.05 and (d_size >= 0.12 or d_cy >= 0.06):
        return "bottom", (f"bottom edge stable (d_bottom={d_bottom:.0%}) while size/top "
                          f"vary (d_size={d_size:.0%}) -> grounded squash/stretch")
    return "preserve", (f"subject translates (d_cy={d_cy:.0%}, d_cx={d_cx:.0%}) "
                        f"-> preserving in-frame motion")


def place_sequence(results, size, pad, anchor):
    """Place every frame on the shared canvas per `anchor`. For bottom/preserve a
    SINGLE shared scale is used across all frames so squash/stretch survives
    (centering uses an independent per-frame fit, which is correct for it)."""
    if anchor == "center":
        return [place_on_canvas(r["cutout"], size, pad) for r in results]

    metas = cell_relative_metrics(results)
    inner_w = size[0] * (1 - 2 * pad)
    inner_h = size[1] * (1 - 2 * pad)

    if anchor == "preserve":
        # scale the whole cell -> canvas (one shared scale: cells are uniform),
        # keeping each subject's in-cell position and relative size intact.
        max_w = max(r["cutout"].size[0] for r in results)
        max_h = max(r["cutout"].size[1] for r in results)
        s = min(inner_w / max_w, inner_h / max_h)
        out = []
        for r in results:
            cut = r["cutout"]
            nw, nh = max(1, round(cut.size[0] * s)), max(1, round(cut.size[1] * s))
            cell = cut.resize((nw, nh), Image.LANCZOS)
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            canvas.alpha_composite(cell, ((size[0] - nw) // 2, (size[1] - nh) // 2))
            out.append(canvas)
        return out

    # anchor == "bottom": shared scale from the largest subject, baseline-aligned
    subs = [(m["r"] - m["l"], m["b"] - m["t"]) for m in metas if m]
    max_sw = max(w for w, h in subs)
    max_sh = max(h for w, h in subs)
    s = min(inner_w / max_sw, inner_h / max_sh)
    baseline = int(size[1] - pad * size[1])
    out = []
    for r, m in zip(results, metas):
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        if m is None:
            out.append(canvas)
            continue
        sub = r["cutout"].crop((m["l"], m["t"], m["r"], m["b"]))
        nw, nh = max(1, round((m["r"] - m["l"]) * s)), max(1, round((m["b"] - m["t"]) * s))
        sub = sub.resize((nw, nh), Image.LANCZOS)
        ox = (size[0] - nw) // 2
        oy = max(0, baseline - nh)
        canvas.alpha_composite(sub, (ox, oy))
        out.append(canvas)
    return out


# ----------------------------------------------------------------------------
# spritesheet packing
# ----------------------------------------------------------------------------
def pack_spritesheet(frames, gap=None):
    if not frames:
        return None
    fw, fh = frames[0].size
    gap = gap if gap is not None else max(2, fw // 32)
    n = len(frames)
    sheet = Image.new("RGBA", (n * fw + (n + 1) * gap, fh + 2 * gap), (0, 0, 0, 0))
    x = gap
    for f in frames:
        sheet.alpha_composite(f, (x, gap))
        x += fw + gap
    return sheet


# ----------------------------------------------------------------------------
# input resolution
# ----------------------------------------------------------------------------
def list_frame_files(d):
    return sorted(p for p in Path(d).iterdir()
                  if p.suffix.lower() in IMG_EXTS and p.is_file())


def resolve_inputs(input_path, frames, cols, rows, chroma_rgb):
    """Return (mode, items) where items is [(index, label, PIL RGBA)].
    mode in {'single', 'folder', 'sheet'}."""
    p = Path(input_path)
    if not p.exists():
        log(f"ERROR: input not found: {input_path}")
        raise SystemExit(2)

    if p.is_dir():
        files = list_frame_files(p)
        if not files:
            log(f"ERROR: no images in folder: {input_path}")
            raise SystemExit(2)
        items = [(i + 1, f.name, Image.open(f).convert("RGBA")) for i, f in enumerate(files)]
        return "folder", items

    img = Image.open(p).convert("RGBA")

    # A single image is sliced as a sheet ONLY when an explicit slicing hint is
    # given (--frames/--cols/--rows). Without a hint we never auto-split, so a
    # lone subject can't be mistaken for a multi-frame sheet.
    if frames or cols or rows:
        cells = slice_sheet(img, chroma_rgb, frames, cols, rows)
        return "sheet", [(i, f"cell_{i:03d}", c.convert("RGBA")) for i, c in cells]

    return "single", [(1, p.stem, img)]


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def parse_size(s):
    try:
        w, h = s.lower().split("x")
        return int(w), int(h)
    except Exception:
        raise argparse.ArgumentTypeError(f"bad --size {s!r}; expected WxH e.g. 1024x1024")


def main():
    ap = argparse.ArgumentParser(
        description="Cut subjects to transparent PNGs / aligned sprites.")
    ap.add_argument("input", help="image file, folder of frames, or one sheet/strip image")
    ap.add_argument("--prompt", help="isolate this specific object via Grounded-SAM-2 (optional tier)")
    ap.add_argument("--chroma", help="known flat background color to also key out, e.g. #00FF00")
    ap.add_argument("--frames", type=int, help="expected number of frames in a sheet")
    ap.add_argument("--cols", type=int, help="grid columns for sheet fallback split")
    ap.add_argument("--rows", type=int, help="grid rows for sheet fallback split")
    ap.add_argument("--size", type=parse_size, default=(1024, 1024),
                    help="output canvas WxH (default 1024x1024)")
    ap.add_argument("--pad", type=float, default=0.08,
                    help="padding fraction around subject (default 0.08)")
    ap.add_argument("--auto-redo", action="store_true",
                    help="re-run flagged frames (separate-file mode only)")
    ap.add_argument("--spritesheet", action="store_true",
                    help="also pack frames into one horizontal sheet")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help=f"rembg model (default {DEFAULT_MODEL})")
    ap.add_argument("--anchor", choices=["auto", "center", "bottom", "preserve"],
                    default="auto",
                    help="multi-frame alignment: auto analyzes the motion (default); "
                         "center = each frame centered; bottom = baseline-aligned "
                         "(grounded squash/stretch); preserve = keep in-frame motion")
    ap.add_argument("--outdir", help="output directory (default: alongside input)")
    args = ap.parse_args()

    chroma_rgb = hex_to_rgb(args.chroma) if args.chroma else None

    in_path = Path(args.input)
    outdir = Path(args.outdir) if args.outdir else (
        in_path if in_path.is_dir() else in_path.parent)
    outdir.mkdir(parents=True, exist_ok=True)
    gate_dir = TMPDIR / "gates"

    log(f"Input: {args.input}")
    if chroma_rgb:
        log(f"Chroma key: #{args.chroma.lstrip('#').upper()} -> {chroma_rgb}")
    if args.prompt:
        log(f"Prompt: {args.prompt!r} (Grounded-SAM-2 tier)")

    mode, items = resolve_inputs(args.input, args.frames, args.cols, args.rows, chroma_rgb)
    log(f"Mode: {mode}  |  frames: {len(items)}")
    sliced_sheet = (mode == "sheet")

    # ---- cutout + validate ----
    results = []
    for idx, label, src in items:
        cutout = make_cutout(src, args.prompt, chroma_rgb, model=args.model)
        ok, issues, checker = validate_frame(
            cutout, idx, chroma_rgb, src.convert("RGB"), gate_dir)
        results.append({
            "idx": idx, "label": label, "src": src, "cutout": cutout,
            "metrics": frame_metrics(cutout), "ok": ok, "issues": issues, "checker": checker,
        })

    # ---- consistency ----
    metrics = [r["metrics"] for r in results]
    flagged, detail = consistency_flags(metrics)

    # ---- auto-redo (separate-file modes only) ----
    if args.auto_redo and flagged and not sliced_sheet:
        log("Auto-redo: re-running flagged frames with tightened params...")
        for i in sorted(flagged):
            r = results[i]
            redo = rembg_cutout(r["src"].convert("RGB"), model=args.model)
            if chroma_rgb is not None:
                redo = apply_chroma(redo, r["src"].convert("RGB"), chroma_rgb,
                                    dist=CHROMA_DIST + 25)
            ok, issues, checker = validate_frame(
                redo, r["idx"], chroma_rgb, r["src"].convert("RGB"), gate_dir)
            r.update(cutout=redo, metrics=frame_metrics(redo),
                     ok=ok, issues=issues, checker=checker)
        metrics = [r["metrics"] for r in results]
        flagged, detail = consistency_flags(metrics)
    elif args.auto_redo and flagged and sliced_sheet:
        warn("--auto-redo cannot re-run individual cells of a sliced sheet. "
             "Reporting which frame indices /image should regenerate (see summary).")

    # ---- place on shared canvas (motion-aware for sequences) + write outputs ----
    multi = len(results) > 1
    anchor = "center"
    anchor_reason = ""
    if multi:
        anchor = args.anchor
        if anchor == "auto":
            anchor, anchor_reason = choose_anchor(cell_relative_metrics(results))
        placed = place_sequence(results, args.size, args.pad, anchor)
    else:
        placed = [place_on_canvas(r["cutout"], args.size, args.pad) for r in results]

    written = []
    if multi:
        for r, canvas in zip(results, placed):
            outp = outdir / f"frame_{r['idx']:03d}.png"
            canvas.save(outp)
            written.append(outp)
    else:
        outp = outdir / f"{results[0]['label']}_cropped.png"
        placed[0].save(outp)
        written.append(outp)

    sheet_path = None
    if args.spritesheet and placed:
        sheet = pack_spritesheet(placed)
        if sheet is not None:
            sheet_path = outdir / "spritesheet.png"
            sheet.save(sheet_path)

    # ---- summary ----
    log("\n" + "=" * 64)
    log("VALIDATION + CONSISTENCY SUMMARY")
    log("=" * 64)
    n_pass = sum(1 for r in results if r["ok"])
    for i, r in enumerate(results):
        status = "PASS" if r["ok"] else "FAIL"
        flag = "  <FLAG: consistency>" if i in flagged else ""
        m = r["metrics"]
        log(f"  frame {r['idx']:03d} [{r['label']}]: {status}{flag}  "
            f"cov={m['coverage']:.1%} bbox={m['w']}x{m['h']}")
        for iss in r["issues"]:
            log(f"        - {iss}")
        if i in flagged:
            for d in detail.get(i, []):
                log(f"        - consistency: {d}")
    log("-" * 64)
    log(f"  gates: {n_pass}/{len(results)} passed   |   consistency-flagged: "
        f"{sorted(r['idx'] for i, r in enumerate(results) if i in flagged)}")
    if multi:
        log(f"  alignment: {anchor}" + (f"  (auto: {anchor_reason})" if anchor_reason else ""))
        if anchor in ("bottom", "preserve") and flagged:
            log("  note: this is a MOTION sequence - position/size 'consistency' flags "
                "above are likely the intended animation, not bad cutouts.")
    log(f"  checkerboard composites (VIEW THESE for the visual gate): {gate_dir}")

    if flagged:
        regen = sorted(results[i]["idx"] for i in flagged)
        if sliced_sheet:
            log(f"  ACTION: ask /image to REGENERATE these frame indices: {regen}")
        elif not args.auto_redo:
            log(f"  HINT: re-run with --auto-redo to retry flagged frames {regen}")

    log("\nWrote:")
    for w_ in written:
        log(f"  {w_}")
    if sheet_path:
        log(f"  {sheet_path}  (horizontal spritesheet)")

    # ---- machine-readable block (parse this programmatically) ----
    import json
    flagged_1based = sorted(results[i]["idx"] for i in flagged)
    report = {
        "mode": mode,
        "frames": len(results),
        "gates_passed": n_pass,
        "all_passed": n_pass == len(results),
        "size": list(args.size),
        "anchor": anchor,
        "anchor_reason": anchor_reason,
        "gate_dir": str(gate_dir),
        "outputs": [str(w_) for w_ in written],
        "spritesheet": str(sheet_path) if sheet_path else None,
        "per_frame": [
            {"index": r["idx"], "label": r["label"], "ok": r["ok"],
             "coverage": round(r["metrics"]["coverage"], 4),
             "bbox_wh": [r["metrics"]["w"], r["metrics"]["h"]],
             "checker": r["checker"], "issues": r["issues"]}
            for r in results
        ],
        "flagged_1based": flagged_1based,
        # for sliced sheets, flagged cells can't be re-run in place — regenerate them
        "regenerate_1based": flagged_1based if sliced_sheet else [],
    }
    log("\n=== JSON ===")
    log(json.dumps(report))

    # exit nonzero if any gate failed, so callers can detect failure
    raise SystemExit(0 if n_pass == len(results) else 1)


if __name__ == "__main__":
    main()
