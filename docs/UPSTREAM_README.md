# Drift-Sense — Navigation-Error Recovery

Localize a high-magnification **reference** wafer image inside a wide, noisier
**search** image (where the reference appears shrunk ~10×), and report the
center `(x, y)` of the match. Built for Applied Materials' *Navigation-Error
Recovery* problem (SEMICON India Hackathon 2026).

The approach is **classical, multi-scale, multi-rotation normalized
cross-correlation (NCC)** — no training, no GPU, no model weights.

---

## Contents

| File | Purpose |
|------|---------|
| `dataset_generator.py` | Generates synthetic DRAM/FinFET reference+search pairs with SEM-realistic noise and augmentation. Records ground-truth centers. |
| `inference.py` | **The script to be scored.** Takes a reference and a search image, prints the predicted center `(x, y)`. |
| `evaluate.py` | Runs `inference.py` over a generated dataset, reports accuracy + timing, saves overlay images. |
| `CITATIONS.md` | References justifying every noise / augmentation choice. |
| `requirements.txt` | Pinned dependencies (numpy, Pillow, OpenCV). |

---

## Setup (local machine)

Requires Python 3.9+.

```bash
git clone https://github.com/<your-username>/drift-sense.git
cd drift-sense
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Quickstart

**1. Generate a sample dataset** (30 DRAM pairs + `ground_truth.csv`):

```bash
python dataset_generator.py --style dram --num-pairs 30 --out dataset --seed 0
```

Use `--style finfet` for the FinFET layout. Each pair is written as
`<style>_<idx>_ref.png` and `<style>_<idx>_search.png`, and every true center is
recorded in `dataset/ground_truth.csv`.

**2. Run localization on a single pair** (this is the scored entry point):

```bash
python inference.py dataset/dram_0000_ref.png dataset/dram_0000_search.png
```

Output (the final line is machine-readable — a single coordinate):

```
predicted center (x, y) = (735.00, 585.00)
735.00,585.00
```

**3. Evaluate accuracy and timing over the whole dataset:**

```bash
python evaluate.py dataset
```

Prints accuracy at several pixel tolerances, median/mean error, and per-pair
timing, and writes overlay images to `dataset/overlays/` (including
`_SLIDE_success.png` and `_SLIDE_failure.png`).

---

## Inference contract

`inference.py` is the file Applied Materials runs on the hidden test set:

- **Inputs:** `python inference.py <reference_image_path> <search_image_path>`
- **Output:** the predicted center as the final stdout line, `x,y` (floats).
- Runs with **no manual edits**; grayscale 1000×1000 PNG inputs.
- If several regions match (periodic array), returns the one **closest to the
  center** of the search image.

To call it from your own code:

```python
import cv2, inference
ref = cv2.imread("ref.png", cv2.IMREAD_GRAYSCALE)
search = cv2.imread("search.png", cv2.IMREAD_GRAYSCALE)
x, y = inference.locate(ref, search)
```

---

## How it works

**Dataset generator.** One high-resolution "truth canvas" (10000×10000, 1 nm/px)
is drawn once per pair; the reference is a 1000×1000 crop of it and the search is
the whole canvas downsampled 10× to 1000×1000. Ground truth is therefore exact:
`(crop_center_x / 10, crop_center_y / 10)`. Each capture then gets SEM-realistic
effects applied independently: Poisson shot noise (lower dose → the search is
noisier), Gaussian read noise, edge-brightening, charging blooms, blur, and
(reference-only) small rotation and scaling. See `CITATIONS.md`.

**Localizer.** The reference is shrunk ~10× into a small template, expanded into a
bank of scales (±20%) and rotations (±3°). Each candidate is matched against the
search with normalized cross-correlation (`cv2.TM_CCOEFF_NORMED`); the best peak
is selected, ties among near-equal peaks are broken toward the search center, and
a parabolic fit gives a sub-pixel center.

---

## Results (30 self-generated DRAM pairs)

| Metric | Value |
|--------|-------|
| Accuracy within 1 px | 96.7% (29/30) |
| Median error | 0.1 px |
| Mean time per 1000×1000 pair | ~1.4 s (CPU) |

The single failure is an honest periodic lock-on: inside a perfectly repeating
patch the match snapped to an identical cell far from the true site. Full
discussion is on the results slide of the presentation.

---

## Notes

- Classical method: **no model weights and no training notebook** are included,
  by design. This keeps the repository fully reproducible on a CPU.
- `requirements.txt` is pinned; regenerate with `pip freeze > requirements.txt`
  from your own environment if you change dependencies.
