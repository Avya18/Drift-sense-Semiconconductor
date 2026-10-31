"""
Drift-Sense localization inference (Applied Materials - Navigation-Error Recovery).

Given a high-magnification REFERENCE image and a wide SEARCH image, find where the
reference pattern appears inside the search image and print its center (x, y).

Method: multi-scale, multi-rotation normalized cross-correlation (NCC).
  - The reference always appears ~10x smaller in the search, so we build templates
    around a 0.1 scale, spanning a range to absorb the +-20% scale augmentation.
  - We also rotate the template over a small bank to absorb the 1-3 deg rotation.
  - NCC (TM_CCOEFF_NORMED) is used because it is invariant to brightness/contrast
    offsets and robust to the independent sensor noise on the two captures.
  - Periodicity tie-break: among near-equal-scoring peaks we return the one closest
    to the center of the search image, as the challenge specifies.
  - A parabolic fit around the winning peak gives a sub-pixel center.

Usage (runs with no manual edits):
  python inference.py <reference_image> <search_image>
Prints the predicted center as the final line:  x,y
"""

import sys
import numpy as np
import cv2

SCALE = 10                       # reference appears ~10x smaller in the search
SCALES = np.linspace(1 / SCALE * 0.82, 1 / SCALE * 1.22, 6)   # absorb +-20% scale
ROTATIONS = np.linspace(-3.0, 3.0, 5)                          # absorb 1-3 deg rot
CROP = 0.82                       # keep this central fraction after rotating (drops fill corners)


def _template(ref, scale, angle):
    """Build one candidate template: shrink the reference, rotate, center-crop."""
    t = cv2.resize(ref, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    if abs(angle) > 1e-6:
        h, w = t.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        t = cv2.warpAffine(t, M, (w, h), flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_REFLECT)
    h, w = t.shape
    ch, cw = int(h * CROP), int(w * CROP)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return t[y0:y0 + ch, x0:x0 + cw]


def _subpixel(resp, x, y):
    """Parabolic sub-pixel refinement of a correlation peak at integer (x, y)."""
    dx = dy = 0.0
    if 0 < x < resp.shape[1] - 1:
        l, c, r = resp[y, x - 1], resp[y, x], resp[y, x + 1]
        d = l - 2 * c + r
        if abs(d) > 1e-9:
            dx = 0.5 * (l - r) / d
    if 0 < y < resp.shape[0] - 1:
        u, c, dn = resp[y - 1, x], resp[y, x], resp[y + 1, x]
        d = u - 2 * c + dn
        if abs(d) > 1e-9:
            dy = 0.5 * (u - dn) / d
    return dx, dy


def locate(ref, search):
    """Return (x, y) center of the reference pattern within the search image."""
    ref = ref.astype(np.float32)
    search = search.astype(np.float32)
    sh, sw = search.shape
    center = np.array([sw / 2.0, sh / 2.0])

    best = None   # (score, resp, peak_x, peak_y, tw, th)
    for scale in SCALES:
        for angle in ROTATIONS:
            t = _template(ref, scale, angle)
            if t.shape[0] >= sh or t.shape[1] >= sw:
                continue
            resp = cv2.matchTemplate(search, t, cv2.TM_CCOEFF_NORMED)
            _, maxv, _, maxloc = cv2.minMaxLoc(resp)
            if best is None or maxv > best[0]:
                best = (maxv, resp, maxloc[0], maxloc[1], t.shape[1], t.shape[0])

    score, resp, px, py, tw, th = best

    # Periodicity tie-break: collect strong peaks (>= 97% of the best score) and,
    # if several are genuinely competitive, keep the one nearest the search center.
    thr = score * 0.97
    ys, xs = np.where(resp >= thr)
    cand = []
    for cx_, cy_ in zip(xs, ys):
        c = np.array([cx_ + tw / 2.0, cy_ + th / 2.0])
        cand.append((np.linalg.norm(c - center), cx_, cy_))
    if len(cand) > 1:
        cand.sort()
        px, py = cand[0][1], cand[0][2]

    dx, dy = _subpixel(resp, px, py)
    x = px + dx + tw / 2.0
    y = py + dy + th / 2.0
    return float(x), float(y)


def main():
    if len(sys.argv) != 3:
        print("usage: python inference.py <reference_image> <search_image>")
        sys.exit(1)
    ref = cv2.imread(sys.argv[1], cv2.IMREAD_GRAYSCALE)
    search = cv2.imread(sys.argv[2], cv2.IMREAD_GRAYSCALE)
    if ref is None or search is None:
        print("error: could not read one of the input images")
        sys.exit(1)
    x, y = locate(ref, search)
    print(f"predicted center (x, y) = ({x:.2f}, {y:.2f})")
    print(f"{x:.2f},{y:.2f}")   # final line: machine-readable single coordinate


if __name__ == "__main__":
    main()
