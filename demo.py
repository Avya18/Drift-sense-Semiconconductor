"""Generate a reproducible synthetic example and a labeled README preview.

Run from the repository root: python demo.py
Generated dataset stays in out_demo/; docs/demo.png is suitable for sharing.
"""
import json
from pathlib import Path

import cv2
import numpy as np

from dataset_generator import generate_dataset
from evaluate import overlay
from inference import locate


def main():
    import csv
    root = Path(__file__).resolve().parent
    output = root / 'out_demo'
    generate_dataset('dram', 1, str(output), seed=0)
    with open(output / 'ground_truth.csv') as handle:
        row = next(csv.DictReader(handle))
    reference = cv2.imread(str(output / row['reference']), 0)
    search = cv2.imread(str(output / row['search']), 0)
    truth = (float(row['x_true']), float(row['y_true']))
    predicted = locate(reference, search)
    error = float(np.hypot(predicted[0] - truth[0], predicted[1] - truth[1]))
    panels = [cv2.cvtColor(reference, cv2.COLOR_GRAY2BGR),
              cv2.cvtColor(search, cv2.COLOR_GRAY2BGR),
              overlay(search, truth, predicted, error, 'Prediction')]
    canvas = np.full((470, 1200, 3), 245, dtype=np.uint8)
    for i, (panel, title) in enumerate(zip(panels, ['Reference (high magnification)', 'Search (wide field)', 'Green: true / Red: predicted'])):
        canvas[50:450, i * 400:(i + 1) * 400] = cv2.resize(panel, (400, 400))
        cv2.putText(canvas, title, (i * 400 + 8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.53, (30, 30, 30), 1)
    target = root / 'docs/demo.png'
    target.parent.mkdir(exist_ok=True)
    if not cv2.imwrite(str(target), canvas):
        raise OSError(f'Could not write {target}')
    metrics = {'style': 'dram', 'seed': 0, 'pairs': 1, 'true_center': truth,
               'predicted_center': predicted, 'error_px': error,
               'note': 'Synthetic smoke test; not a real SEM benchmark.'}
    (root / 'docs/demo-result.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(json.dumps(metrics, indent=2))
    print(f'Preview saved to {target}')


if __name__ == '__main__':
    main()
