# Setup and usage

Use Python 3.9 or newer, with a virtual environment. Dependencies are NumPy, Pillow and OpenCV. The supplied requirements use minimum versions rather than an exact version lock.

```bash
git clone https://github.com/Avya18/Drift-sense-Semiconconductor.git
cd Drift-sense-Semiconconductor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate`.

## Generate data

Start with one pair to check the environment:

```bash
python dataset_generator.py --style dram --num-pairs 1 --out dataset --seed 0
```

For a larger evaluation, use 30 or more pairs. The generator builds a 10000 × 10000 truth canvas for each pair, so generation requires substantially more memory than inference.

```bash
python dataset_generator.py --style dram --num-pairs 30 --out dataset --seed 0
python dataset_generator.py --style finfet --num-pairs 30 --out dataset_finfet --seed 0
```

Use separate output directories for separate runs: the generator rewrites `ground_truth.csv` and can leave older images in a reused directory.

## Localize one image pair

```bash
python inference.py dataset/dram_0000_ref.png dataset/dram_0000_search.png
```

The final stdout line is `x,y`, in search-image pixels. Coordinates are the match center; x increases rightward and y downward.

## Evaluate

```bash
python evaluate.py dataset
```

This prints accuracy within 3, 5 and 10 pixels, mean/median error and timing. It writes annotated images under `dataset/overlays/`. The best and worst examples are also saved as `_SLIDE_success.png` and `_SLIDE_failure.png`; those labels describe relative ranking rather than a fixed pass/fail threshold.

To call inference from Python:

```python
import cv2
import inference

reference = cv2.imread("ref.png", cv2.IMREAD_GRAYSCALE)
search = cv2.imread("search.png", cv2.IMREAD_GRAYSCALE)
x, y = inference.locate(reference, search)
```

Supply readable, nonempty grayscale arrays and images compatible with the approximate 10× magnification relationship.
