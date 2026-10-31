# Troubleshooting

| Symptom | Action |
| --- | --- |
| Missing numpy, PIL or cv2 | Activate the virtual environment and run `python -m pip install -r requirements.txt`. |
| OpenCV cannot load libGL on a server | Use an environment with OpenCV system dependencies, or install the headless OpenCV variant in a separate environment. |
| Inference reports unreadable images | Check both paths and verify that the files are valid images. |
| Evaluation cannot find ground_truth.csv | Generate a dataset first, then pass that directory to evaluate.py. |
| Evaluation fails on empty results | Generate at least one pair; zero-pair datasets are not supported by the evaluator. |
| Generation is slow or memory-intensive | Start with one pair; each generation step allocates a 10000 × 10000 truth canvas. |
| Prediction jumps to a repeating cell | Inspect overlays; periodic patterns can produce ambiguous NCC matches. |
| Dataset files and CSV disagree after regeneration | Generate into a new output directory to avoid leftover images. |

The default CLI loads images as grayscale. Python callers must supply valid 2-D arrays. The localizer assumes the reference appears about ten times smaller in the search; arbitrary magnification ratios and very small input images are outside the documented workflow.
