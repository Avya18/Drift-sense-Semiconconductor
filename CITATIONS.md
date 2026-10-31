# Citations

References justifying the structural, noise, and augmentation choices in
`dataset_generator.py`. This list is kept identical to the References slide of
the presentation.



## Semiconductor layout / structure (organizer-provided)

- IRDS 2024 *More Moore* roadmap — periodic word-line / bit-line pitch and
  contact-array structure used for the DRAM layout.
- EE Times, "Hynix DRAM layout, process integration adapt to change" — DRAM
  word-line / bit-line grid appearance.
- TI patent EP0780901A2 — bit-line layout geometry.

## SEM imaging: noise and edge effect

- L. Reimer, *Scanning Electron Microscopy: Physics of Image Formation and
  Microanalysis* — secondary-electron **edge effect** (edge-brightening) and
  **shot noise** from electron counting.
- J. Goldstein et al., *Scanning Electron Microscopy and X-ray Microanalysis* —
  SEM image formation, detector (read) noise, and charging artifacts.

## Localization method

- J. P. Lewis, "Fast Normalized Cross-Correlation" (1995) — normalized
  cross-correlation as a brightness/contrast-invariant template matcher.

## Mapping: choice → justification

| Choice in generator | Justified by |
|---------------------|--------------|
| DRAM word-line/bit-line grid + contacts | IRDS 2024; EE Times Hynix; TI EP0780901A2 |
| Poisson shot noise (dose-driven) | Reimer |
| Gaussian read noise | Goldstein et al. |
| Edge-brightening | Reimer |
| Charging blooms | Goldstein et al. |
| NCC localizer | Lewis (1995) |
