"""
Drift-Sense synthetic dataset generator (Applied Materials - Navigation-Error Recovery).

Generates image PAIRS for wafer-site localization:
  - Reference : 1000x1000, high-magnification ("100x", 1 nm/px) close-up of a site.
  - Search    : 1000x1000, wide ("10x", 10 nm/px) view; the reference pattern
                appears shrunk ~10x (about 100x100 px) somewhere inside it.
The true center of the reference pattern inside the search image is recorded as
ground truth so accuracy can be measured.

HOW A PAIR IS MADE (keeps ground truth exact):
  1. Draw ONE big sharp "truth canvas" (10000x10000, 1 nm/px) of the full layout
     plus a distinctive landmark.
  2. Reference = a 1000x1000 crop centered on the landmark.
  3. Search    = the whole truth canvas shrunk 10x to 1000x1000.
  4. Ground truth = (cx/10, cy/10): the landmark's position in the shrunk search.

REALISM APPLIED TO EACH CAPTURE (independent per image):
  - Edge-brightening : SEM edge effect - feature edges emit more secondary
                       electrons, so they glow. [Reimer; Goldstein et al.]
  - Charging         : occasional bright blooms where charge cannot drain.
  - Blur             : finite probe/optics blur (search a touch blurrier).
  - Shot noise       : Poisson electron-counting noise; LOW dose on the search
                       makes it noisier than the reference (physics, not a knob).
  - Read noise       : Gaussian detector hiss, equal on both (electronics, not
                       magnification).
  - Geometry (reference only): small rotation (1-3 deg) and scale (-20%..+20%)
                       so the reference is slightly mis-registered vs the search.
                       Applied to the reference so the search stays the exact
                       ground-truth frame. [augmentation ranges per challenge slide]

Dependencies: numpy + Pillow only (no scipy) for easy reproducibility.

CLI:
  python dataset_generator.py --style dram   --num-pairs 30 --out dataset --seed 0
  python dataset_generator.py --style finfet --num-pairs 30 --out dataset --seed 0
"""

import argparse
import csv
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CANVAS = 10000   # truth canvas size (10 um at 1 nm/px)
REF = 1000       # reference image size (1 um at 1 nm/px)
SCALE = 10       # search is 10x zoomed out


# --------------------------------------------------------------------------- #
# 1. Layouts (the clean structure)                                            #
# --------------------------------------------------------------------------- #
def build_truth_dram(rng, pitch=300, line_w=45, dot_r=55,
                     bg=95, line_v=165, dot_v=205):
    """DRAM-style: word-lines x bit-lines grid, a contact dot at each crossing,
    plus one distinctive landmark. Returns (uint8 array, (cx, cy))."""
    img = Image.new("L", (CANVAS, CANVAS), bg)
    d = ImageDraw.Draw(img)

    for y in range(pitch // 2, CANVAS, pitch):
        d.rectangle([0, y - line_w // 2, CANVAS, y + line_w // 2], fill=line_v)
    for x in range(pitch // 2, CANVAS, pitch):
        d.rectangle([x - line_w // 2, 0, x + line_w // 2, CANVAS], fill=line_v)
    for y in range(pitch // 2, CANVAS, pitch):
        for x in range(pitch // 2, CANVAS, pitch):
            d.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=dot_v)

    cx, cy = _snap_center(rng, pitch, pitch)
    # Landmark: dark contact block with a bright bar through it.
    d.rectangle([cx - 70, cy - 45, cx + 70, cy + 45], fill=40)
    d.rectangle([cx - 18, cy - 60, cx + 18, cy + 60], fill=225)
    return np.asarray(img), (cx, cy)


def build_truth_finfet(rng, fin_pitch=110, fin_w=42, gate_pitch=1100, gate_w=150,
                       contact_r=26, bg=90, fin_v=180, gate_v=135, contact_v=215):
    """FinFET-style: dense vertical fins crossed by horizontal gate bars, with a
    distinctive gate/fin crossing as the landmark. Returns (uint8 array, (cx, cy))."""
    img = Image.new("L", (CANVAS, CANVAS), bg)
    d = ImageDraw.Draw(img)

    for x in range(fin_pitch // 2, CANVAS, fin_pitch):            # vertical fins
        d.rectangle([x - fin_w // 2, 0, x + fin_w // 2, CANVAS], fill=fin_v)
    for y in range(gate_pitch // 2, CANVAS, gate_pitch):         # horizontal gates
        d.rectangle([0, y - gate_w // 2, CANVAS, y + gate_w // 2], fill=gate_v)
    for y in range(gate_pitch // 2, CANVAS, gate_pitch):         # contacts on gates
        for x in range(fin_pitch // 2, CANVAS, fin_pitch):
            d.ellipse([x - contact_r, y - contact_r, x + contact_r, y + contact_r],
                      fill=contact_v)

    cx, cy = _snap_center(rng, fin_pitch, gate_pitch)
    # Landmark: a wider bright gate stub + a dark contact, distinct from the array.
    d.rectangle([cx - 90, cy - 95, cx + 90, cy + 95], fill=210)
    d.rectangle([cx - 45, cy - 45, cx + 45, cy + 45], fill=45)
    return np.asarray(img), (cx, cy)


def _snap_center(rng, pitch_x, pitch_y):
    """Pick a target site away from the edges, snapped onto the layout grid."""
    cx = int(rng.integers(1500, CANVAS - 1500))
    cy = int(rng.integers(1500, CANVAS - 1500))
    cx = round((cx - pitch_x // 2) / pitch_x) * pitch_x + pitch_x // 2
    cy = round((cy - pitch_y // 2) / pitch_y) * pitch_y + pitch_y // 2
    return cx, cy


BUILDERS = {"dram": build_truth_dram, "finfet": build_truth_finfet}


# --------------------------------------------------------------------------- #
# 2. Realism effects                                                          #
# --------------------------------------------------------------------------- #
def add_edge_brightening(img, strength):
    """SEM edge effect: add brightness proportional to local gradient magnitude."""
    f = img.astype(np.float64)
    gy, gx = np.gradient(f)
    mag = np.hypot(gx, gy)
    if mag.max() > 0:
        mag /= mag.max()
    return np.clip(f + strength * 255.0 * mag, 0, 255).astype(np.uint8)


def add_charging(img, rng, max_blooms=2, strength=(25, 60), radius=(15, 40)):
    """Occasional soft bright blooms where charge cannot drain away."""
    k = int(rng.integers(0, max_blooms + 1))
    if k == 0:
        return img
    overlay = Image.new("L", (img.shape[1], img.shape[0]), 0)
    d = ImageDraw.Draw(overlay)
    for _ in range(k):
        r = int(rng.integers(*radius))
        x = int(rng.integers(r, img.shape[1] - r))
        y = int(rng.integers(r, img.shape[0] - r))
        d.ellipse([x - r, y - r, x + r, y + r], fill=int(rng.integers(*strength)))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(radius) / 2))
    out = img.astype(np.float64) + np.asarray(overlay, dtype=np.float64)
    return np.clip(out, 0, 255).astype(np.uint8)


def add_blur(img, sigma):
    if sigma <= 0:
        return img
    return np.asarray(Image.fromarray(img).filter(ImageFilter.GaussianBlur(radius=sigma)))


def add_shot_noise(img, dose, rng):
    """Poisson electron-counting noise. Lower dose = grainier (relative noise ~ 1/sqrt(dose))."""
    counts = img.astype(np.float64) / 255.0 * dose
    return np.clip(rng.poisson(counts) / dose * 255.0, 0, 255).astype(np.uint8)


def add_read_noise(img, sigma, rng):
    """Gaussian detector read noise: same faint hiss everywhere."""
    return np.clip(img.astype(np.float64) + rng.normal(0.0, sigma, img.shape),
                   0, 255).astype(np.uint8)


def augment_geometry(img, rng, max_rot=3.0, max_scale=0.20, bg=95):
    """Reference-only: small scale (-max_scale..+max_scale) then rotation
    (magnitude 1..max_rot deg, random sign). Center stays centered so the search
    ground truth is unaffected."""
    pil = Image.fromarray(img)
    s = 1.0 + rng.uniform(-max_scale, max_scale)
    ns = max(1, int(round(REF * s)))
    pil = pil.resize((ns, ns), Image.BICUBIC)
    pil = _fit_center(pil, REF, bg)
    angle = float(rng.uniform(1.0, max_rot)) * (1 if rng.random() < 0.5 else -1)
    pil = pil.rotate(angle, resample=Image.BICUBIC, fillcolor=bg)
    return np.asarray(pil)


def _fit_center(pil, size, bg):
    """Center-crop (if larger) or center-pad (if smaller) back to size x size."""
    w = pil.size[0]
    if w >= size:
        off = (w - size) // 2
        return pil.crop((off, off, off + size, off + size))
    canvas = Image.new("L", (size, size), bg)
    off = (size - w) // 2
    canvas.paste(pil, (off, off))
    return canvas


# --------------------------------------------------------------------------- #
# 3. Capture pipeline + pair assembly                                         #
# --------------------------------------------------------------------------- #
def capture(img, rng, dose, read_sigma, edge_strength, blur_sigma,
            charging=True):
    """Turn a clean image into one realistic SEM capture (physical-ish order:
    emission -> optics -> detector)."""
    out = add_edge_brightening(img, edge_strength)
    if charging:
        out = add_charging(out, rng)
    out = add_blur(out, blur_sigma)
    out = add_shot_noise(out, dose, rng)
    out = add_read_noise(out, read_sigma, rng)
    return out


def make_pair(style="dram", seed=0,
              dose_ref=200, dose_search=35, read_sigma=7,
              edge_strength=0.35, blur_ref=0.8, blur_search=1.2,
              max_rot=3.0, max_scale=0.20, charging=True, bg=95):
    """Return (reference, search, (x_true, y_true))."""
    build = BUILDERS[style]
    truth_rng = np.random.default_rng(seed)          # layout + landmark placement
    truth, (cx, cy) = build(truth_rng)

    ref_clean = truth[cy - REF // 2: cy + REF // 2, cx - REF // 2: cx + REF // 2]
    search_clean = np.asarray(
        Image.fromarray(truth).resize((CANVAS // SCALE, CANVAS // SCALE), Image.LANCZOS)
    )
    gt = (cx / SCALE, cy / SCALE)

    cap_rng = np.random.default_rng(seed + 10_000)   # capture noise (independent)
    ref = augment_geometry(ref_clean, cap_rng, max_rot, max_scale, bg)
    ref = capture(ref, cap_rng, dose_ref, read_sigma, edge_strength, blur_ref, charging)
    # Separate rng call sequence => the search noise is independent of the reference.
    search = capture(search_clean, cap_rng, dose_search, read_sigma,
                     edge_strength, blur_search, charging)
    return ref, search, gt


# --------------------------------------------------------------------------- #
# 4. Batch generation + ground-truth file                                     #
# --------------------------------------------------------------------------- #
def generate_dataset(style, num_pairs, out_dir, seed=0):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for i in range(num_pairs):
        ref, search, (x, y) = make_pair(style=style, seed=seed + i)
        ref_name = f"{style}_{i:04d}_ref.png"
        search_name = f"{style}_{i:04d}_search.png"
        Image.fromarray(ref).save(os.path.join(out_dir, ref_name))
        Image.fromarray(search).save(os.path.join(out_dir, search_name))
        rows.append([i, style, ref_name, search_name, round(x, 2), round(y, 2)])
        print(f"  [{i + 1}/{num_pairs}] {search_name}  true=({x:.1f}, {y:.1f})")

    csv_path = os.path.join(out_dir, "ground_truth.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "style", "reference", "search", "x_true", "y_true"])
        w.writerows(rows)
    print(f"Wrote {num_pairs} pairs and ground truth -> {csv_path}")
    return csv_path


def main():
    p = argparse.ArgumentParser(description="Drift-Sense synthetic dataset generator")
    p.add_argument("--style", choices=list(BUILDERS), default="dram",
                   help="architecture style to generate")
    p.add_argument("--num-pairs", type=int, default=30,
                   help="number of image pairs to generate (>= 30 recommended)")
    p.add_argument("--out", default="dataset", help="output directory")
    p.add_argument("--seed", type=int, default=0, help="base random seed")
    args = p.parse_args()
    print(f"Generating {args.num_pairs} '{args.style}' pairs into '{args.out}/'")
    generate_dataset(args.style, args.num_pairs, args.out, args.seed)


if __name__ == "__main__":
    main()
