# Data and outputs

For `--style dram --num-pairs 1 --out dataset`:

```text
dataset/
├── dram_0000_ref.png
├── dram_0000_search.png
├── ground_truth.csv
└── overlays/                 # created by evaluate.py
    ├── dram_0000_overlay.png
    ├── _SLIDE_success.png
    └── _SLIDE_failure.png
```

Images are grayscale 1000 × 1000 PNGs. Pair indices start at zero with four-digit padding. FinFET filenames use the prefix `finfet`.

## Ground truth

| Column | Meaning |
| --- | --- |
| index | Zero-based pair index. |
| style | dram or finfet. |
| reference | Reference image filename, relative to the dataset directory. |
| search | Search image filename, relative to the dataset directory. |
| x_true | True center x in search pixels. |
| y_true | True center y in search pixels. |

Evaluation loads exactly the rows in `ground_truth.csv`; extra files are ignored. Green overlay markers show ground truth, red markers show predictions.

Generated datasets, virtual environments and PNG outputs are ignored by the original gitignore rules (except PNGs directly under docs). Generate data locally rather than committing it.

No real wafer dataset, presentation, pretrained model or generated benchmark artifacts are included in the upstream snapshot.
