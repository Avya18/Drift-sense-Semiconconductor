"""
Evaluation harness for Drift-Sense.

Runs the localization on every pair listed in a dataset's ground_truth.csv,
computes localization error, accuracy at several pixel tolerances, and timing,
and saves reference/search/predicted/true overlay images (including the best
success case and the worst failure case for the results slide).

Usage:
  python evaluate.py <dataset_dir>
"""

import csv
import os
import sys
import time

import numpy as np
import cv2

import inference


def overlay(search_gray, true_xy, pred_xy, err, title):
    im = cv2.cvtColor(search_gray, cv2.COLOR_GRAY2BGR)
    tx, ty = int(round(true_xy[0])), int(round(true_xy[1]))
    px, py = int(round(pred_xy[0])), int(round(pred_xy[1]))
    cv2.rectangle(im, (tx - 50, ty - 50), (tx + 50, ty + 50), (0, 200, 0), 2)   # true (green)
    cv2.drawMarker(im, (tx, ty), (0, 200, 0), cv2.MARKER_CROSS, 22, 2)
    cv2.drawMarker(im, (px, py), (0, 0, 230), cv2.MARKER_TILTED_CROSS, 22, 2)   # pred (red)
    cv2.putText(im, f"{title}  err={err:.1f}px", (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(im, "green=true  red=predicted", (10, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return im


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "dataset"
    out_dir = os.path.join(data_dir, "overlays")
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(data_dir, "ground_truth.csv")) as f:
        rows = list(csv.DictReader(f))

    errors, times, records = [], [], []
    for r in rows:
        ref = cv2.imread(os.path.join(data_dir, r["reference"]), cv2.IMREAD_GRAYSCALE)
        search = cv2.imread(os.path.join(data_dir, r["search"]), cv2.IMREAD_GRAYSCALE)
        tx, ty = float(r["x_true"]), float(r["y_true"])

        t0 = time.perf_counter()
        px, py = inference.locate(ref, search)
        dt = time.perf_counter() - t0

        err = float(np.hypot(px - tx, py - ty))
        errors.append(err)
        times.append(dt)
        records.append((r, search, (tx, ty), (px, py), err))
        print(f"  {r['search']}: pred=({px:6.1f},{py:6.1f}) true=({tx:6.1f},{ty:6.1f}) "
              f"err={err:5.1f}px  {dt*1000:5.0f} ms")

    errors = np.array(errors)
    times = np.array(times)
    print("\n================  SUMMARY  ================")
    print(f"pairs evaluated       : {len(errors)}")
    for tol in (3, 5, 10):
        acc = 100.0 * np.mean(errors <= tol)
        print(f"accuracy within {tol:2d} px : {acc:5.1f}%")
    print(f"median error          : {np.median(errors):.2f} px")
    print(f"mean error            : {errors.mean():.2f} px")
    print(f"mean time per pair    : {times.mean()*1000:.0f} ms")
    print(f"max time per pair     : {times.max()*1000:.0f} ms")

    # Save all overlays; call out the best success and worst failure for the slide.
    order = np.argsort(errors)
    best_i, worst_i = int(order[0]), int(order[-1])
    for i, (r, search, true_xy, pred_xy, err) in enumerate(records):
        tag = "SUCCESS" if i == best_i else "FAILURE" if i == worst_i else r["search"][:-4]
        img = overlay(search, true_xy, pred_xy, err, tag)
        name = r["search"].replace("_search.png", "_overlay.png")
        cv2.imwrite(os.path.join(out_dir, name), img)
    cv2.imwrite(os.path.join(out_dir, "_SLIDE_success.png"),
                overlay(records[best_i][1], records[best_i][2], records[best_i][3],
                        records[best_i][4], "SUCCESS"))
    cv2.imwrite(os.path.join(out_dir, "_SLIDE_failure.png"),
                overlay(records[worst_i][1], records[worst_i][2], records[worst_i][3],
                        records[worst_i][4], "FAILURE"))
    print(f"\noverlays saved to {out_dir}/  (see _SLIDE_success.png and _SLIDE_failure.png)")


if __name__ == "__main__":
    main()
