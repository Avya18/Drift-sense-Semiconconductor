# Architecture

## Pipeline

```text
Synthetic truth canvas
    ├── high-magnification crop → reference capture
    └── downsampled canvas     → search capture
                                 ↓
                         multi-scale/rotation NCC
                                 ↓
                         predicted center (x, y)
                                 ↓
                   evaluation against ground_truth.csv
```

## Dataset generator

`dataset_generator.py` draws DRAM or FinFET layouts with a distinctive landmark. It extracts a 1000 × 1000 reference crop and downsamples the 10000 × 10000 truth canvas to a 1000 × 1000 search image. Ground truth is the crop center divided by ten.

The reference gets geometry augmentation. Each capture gets edge brightening, charging, blur, Poisson shot noise and Gaussian read noise. Seeds control layout and capture random-number streams. [CITATIONS.md](../CITATIONS.md) preserves upstream explanations of these modeling choices.

## Inference

`inference.py` builds 30 candidate templates: six scales from 0.082 to 0.122 and five rotations from −3° to +3°. Templates retain their central 82% after transformation. OpenCV normalized cross-correlation selects the highest-scoring template.

Within the winning response map, peaks at least 97% of its best score compete by proximity to the search center. Parabolic peak refinement then produces a floating-point center.

No training stage, learned weights or GPU is required. Repetitive patterns can produce ambiguous matches; proximity to the image center does not guarantee the physically correct site.

## Evaluation

`evaluate.py` imports `inference`, reads pairs from the CSV, measures Euclidean center error and localization time, and saves overlays. Timing covers localization, excluding image loading and overlay writing.

The implementation assumes a nonempty dataset and readable input images. It reports results to stdout and writes PNG overlays; it does not export a separate metrics CSV.
