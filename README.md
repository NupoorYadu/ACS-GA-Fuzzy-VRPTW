# Enhancements-for-Dynamic-Vehicle-Routing-Problems

This repository contains an Ant Colony System (ACS) implementation for the Solomon VRPTW instances, an experiment runner, a GA tuner, plotting utilities and an analysis pipeline. It also includes supporting scripts and analysis used for the paper/figures.

Quick layout
- src/aco/acs.py — ACS solver with q0, candidate lists, tau0 init, q0 annealing and 2-opt local search.
- scripts/run_acs.py — run single instance or batch over parsed Solomon JSONs. Writes per-instance JSON and PNG and a summary CSV.
- src/ga/optimizer.py + scripts/run_ga.py — DEAP-based tuner; scripts/run_ga_simple.py is a no-dependency fallback.
- scripts/analyze_results.py — compute group stats, novelty scoring, plots and a short PDF report.
- scripts/aggregate_repeats.py — aggregate repeated-run outputs into summaries used by analysis.
- esults/ — experiment outputs. Common subfolders:
  - esults/aco/ — current experiment (single-run summaries)
  - esults/aco_baseline/ — baseline experiment
  - esults/aco_repeats/ — repeated-run raw outputs
  - esults/analysis/ — analysis outputs (instance_features.csv, plots, stat_tests.json, report.pdf)

Reproduce the final aggregated analysis (example steps):

1) Run 5 repeats for the current configuration (example):

`powershell
for (=1;  -le 5; ++) { python scripts\run_acs.py --instance data\solomon_dataset\parsed\R1\R101.json --batch-root data\solomon_dataset\parsed --out-dir results/aco_repeats\current\repeat_ --ants 6 --iters 12 --capacity 200 --q0 0.9 --q0-decay 0.01 --q0-min 0.2 }
`

2) Run 5 repeats for the baseline configuration:

`powershell
for (=1;  -le 5; ++) { python scripts\run_acs.py --instance data\solomon_dataset\parsed\R1\R101.json --batch-root data\solomon_dataset\parsed --out-dir results/aco_repeats\baseline\repeat_ --ants 6 --iters 12 --capacity 200 --q0 0.0 }
`

3) Aggregate repeats (writes aggregated summaries used by the analysis):

`powershell
python scripts\aggregate_repeats.py
`

4) Run analysis (creates esults/analysis/):

`powershell
python scripts\analyze_results.py
`

5) Run unit tests (manual runner):

`powershell
python tests\run_tests_manual.py
`

Notes & recommendations
- For rigorous statistical comparisons, run multiple independent repeats (5+ recommended) and aggregate as shown.
- To produce reproducible debug runs add a seed option (I can add this) and pin minimal equirements.txt in the repo.
- The novelty scoring weights can be configured in config/novelty_config.json (the script falls back to built-in defaults if this file is absent).

If you'd like, I can (A) add deterministic seed support to the runner, (B) add CI to run tests automatically, or (C) extend the PDF report with textual summaries and top-N instance thumbnails.

## Hybrid ACO-GA-Fuzzy VRPTW

Project scaffold for Hybrid Ant Colony System (ACS) + Genetic Algorithm + Fuzzy logic for Dynamic VRPTW.

Quick start:
1. Create and activate virtual env
2. Install dependencies (see equirements.txt)
3. Run smoke test: python main.py --mode smoke

Place Solomon instances into data/solomon/.
