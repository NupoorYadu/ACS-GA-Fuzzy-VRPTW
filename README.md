# ACS–GA–Fuzzy VRPTW

Hybrid Ant Colony System (ACS) + Genetic Algorithm (GA) + Fuzzy logic framework for the Solomon Vehicle Routing Problem with Time Windows (VRPTW).

The goal of this project is to provide a **reproducible, extensible experimental scaffold** for studying modern ACS design choices on Solomon VRPTW instances, with:

- An enhanced ACS solver with $q_0$ annealing, $\tau_0$-based pheromone initialization, candidate customer lists, and 2‑opt local search.
- A GA-based tuner for key ACS parameters \(([\alpha, \beta, \rho, q_0])\).
- A fuzzy service-quality analysis that evaluates time-window satisfaction using a simple membership function.
- A full experiment pipeline: repeated runs, aggregation, statistical comparison, novelty scoring, and plotting.
- A complete paper in `paper/paper.md` describing the methodology, experiments, results, and practical implications.

If you just want to **reproduce the main results and figures**, see the "End-to-end reproduction" section below.

---

## 1. Repository layout

Core components:

- `src/aco/acs.py` — ACS solver for Solomon VRPTW with:
  - $q_0$ annealing (exploitation–exploration schedule),
  - $\tau_0$ pheromone initialization via nearest-neighbor tour,
  - candidate lists of nearest customers,
  - optional 2‑opt local search on routes.
- `scripts/run_acs.py` — experiment runner:
  - single-instance runs via `--instance`,
  - batch runs via `--batch-root`,
  - writes per-run JSON result files, route PNGs, and summary CSVs.
- `src/ga/optimizer.py`, `scripts/run_ga.py`, `scripts/run_ga_simple.py` — GA-based parameter tuner for ACS.
  - `run_ga.py`: DEAP-based GA.
  - `run_ga_simple.py`: no-dependency fallback GA.
- `scripts/aggregate_repeats.py` — aggregates repeated runs into instance-level summary CSVs.
- `scripts/analyze_results.py` — analysis and plotting pipeline:
  - reads aggregated summaries,
  - computes novelty scores,
  - generates plots and `report.pdf` under `results/analysis/`.
- `scripts/summarize_ga_eval.py` — summarizes GA evaluation runs (mean best cost per instance/variant).
- `scripts/fuzzy_service_quality.py` — computes fuzzy time-window satisfaction metrics for selected instances.
- `config/novelty_config.json` — configuration for novelty feature weights.
- `paper/paper.md` — full report (Introduction, Methodology, Experiments, GA tuning, fuzzy analysis, Discussion, Conclusion, Reproducibility).

Data and results:

- `data/solomon_dataset/` — raw Solomon instances and parsed JSONs.
- `results/aco/` — ACS runs for the current configuration (single-run summaries).
- `results/aco_baseline/` — ACS runs for the baseline configuration (e.g., $q_0 = 0$).
- `results/aco_repeats/` — repeated-run raw outputs (current and baseline).
- `results/ga_eval/` — GA evaluation runs for representative instances.
- `results/analysis/` — analysis outputs (summary CSVs, plots, `stat_tests.json`, `report.pdf`).

CI and tests:

- `.github/workflows/tests.yml` — GitHub Actions workflow that runs the manual test suite.
- `tests/run_tests_manual.py` — smoke tests and basic regression checks.

---

## 2. Setup

From the project root on Windows:

```powershell
cd "C:\Fall_Sem_25-26\SoftComputing\Project"
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Parse the Solomon instances (once):

```powershell
python main.py --mode import_all --instance data/solomon_dataset
```

Run a quick smoke test to verify that imports and basic plotting work:

```powershell
python main.py --mode smoke
```

---

## 3. Running ACS experiments

### 3.1 Single-instance run

Example: run ACS on a single C101 instance with the current configuration:

```powershell
python scripts\run_acs.py `
  --instance data\solomon_dataset\parsed\C1\C101.json `
  --ants 6 --iters 12 --capacity 200 `
  --q0 0.9 --q0-decay 0.01 --q0-min 0.2 `
  --seed 1
```

Outputs (under `results/aco/` by default):

- `*_acs_result.json` — JSON with best cost, routes, metadata, and seed.
- `*_acs_routes.png` — route plot for the best solution.

### 3.2 Repeated experiments (current configuration)

Run repeated experiments (e.g., 5 repeats) across all parsed instances under a root directory:

```powershell
for ($i = 1; $i -le 5; $i++) {
  python scripts\run_acs.py `
    --instance data\solomon_dataset\parsed\R1\R101.json `
    --batch-root data\solomon_dataset\parsed `
    --out-dir results\aco_repeats\current\repeat_$i `
    --ants 6 --iters 12 --capacity 200 `
    --q0 0.9 --q0-decay 0.01 --q0-min 0.2 `
    --seed $i
}
```

### 3.3 Repeated experiments (baseline configuration)

Baseline configuration example: $q_0 = 0$ (no exploitation branch):

```powershell
for ($i = 1; $i -le 5; $i++) {
  python scripts\run_acs.py `
    --instance data\solomon_dataset\parsed\R1\R101.json `
    --batch-root data\solomon_dataset\parsed `
    --out-dir results\aco_repeats\baseline\repeat_$i `
    --ants 6 --iters 12 --capacity 200 `
    --q0 0.0 `
    --seed $i
}
```

### 3.4 Aggregate repeats and analyze

Aggregate repeated runs into summary CSVs:

```powershell
python scripts\aggregate_repeats.py
```

Run the analysis pipeline:

```powershell
python scripts\analyze_results.py
```

This creates:

- `results/analysis/instance_features.csv` — per-instance metrics and novelty scores.
- `results/analysis/stat_tests.json` — results of statistical tests.
- `results/analysis/*.png` — plots (mean cost by set, violin plots, radar plots, scatter plots).
- `results/analysis/report.pdf` — multi-page summary report.

---

## 4. GA-based parameter tuning

The GA tuner optimizes ACS parameters \(([\alpha, \beta, \rho, q_0])\) for specific instances under a limited evaluation budget.

Run GA tuning for C101 using the DEAP-based tuner:

```powershell
python scripts\run_ga.py --instance C101
```

This writes GA logs (best individuals and fitness evolution) to `results/ga_C101.txt` (and similarly for other instances).

To summarize GA evaluation runs for the default ACS parameters (stored under `results/ga_eval/`):

```powershell
python scripts\summarize_ga_eval.py
```

The output is a small CSV printed to stdout with columns like:

- `Instance, Variant, N, MeanBestCost`.

These numbers match the GA-tuning table described in Section 4.4 of `paper/paper.md`.

---

## 5. Fuzzy service-quality analysis

The fuzzy analysis evaluates how well service start times respect customer time windows using a simple membership function:

$$
L_i = \max(0, s_i - l_i), \quad
\mu_i =
\begin{cases}
1, & s_i \le l_i, \\
\max\{0, 1 - L_i / T\}, & s_i > l_i,
\end{cases}
$$

where $[e_i, l_i]$ is the time window, $s_i$ is the service start time, and $T$ is a tolerance parameter.

To compute fuzzy satisfaction for representative instances (C101, R101, RC101):

```powershell
python scripts\fuzzy_service_quality.py
```

This script prints lines of the form:

```text
Instance,Class,BestCost,AvgFuzzy,MinFuzzy
C101,C,1833.399,0.650,0.000
...
```

These values correspond to the fuzzy service-quality table in Section 4.5 of the paper.

---

## 6. End-to-end reproduction of main results

To roughly reproduce the main aggregated results and plots used in the paper:

1. **Prepare environment and data**

   ```powershell
   .venv\Scripts\activate
   python main.py --mode import_all --instance data/solomon_dataset
   ```

2. **Run repeated ACS experiments (current + baseline)**

   Use the loops from Sections 3.2 and 3.3 to generate `results/aco_repeats/current` and `results/aco_repeats/baseline`.

3. **Aggregate repeats and analyze**

   ```powershell
   python scripts\aggregate_repeats.py
   python scripts\analyze_results.py
   ```

4. **Run GA evaluation and summarize** (optional for GA-tuning section)

   ```powershell
   python scripts\run_ga.py --instance C101
   python scripts\run_ga.py --instance R101
   python scripts\run_ga.py --instance RC101
   python scripts\summarize_ga_eval.py
   ```

5. **Run fuzzy service-quality analysis**

   ```powershell
   python scripts\fuzzy_service_quality.py
   ```

The numerical values you obtain should be close to those reported in `paper/paper.md`, up to randomness and run budgets.

---

## 7. Notes & recommendations

- For **statistical robustness**, use 5–10 repeats per configuration per instance when possible.
- Always set `--seed` to make experiments **reproducible**. The seed is stored in per-run JSON and summary CSV files.
- Adjust ACS parameters (`--ants`, `--iters`, `--q0`, decay, etc.) depending on your available compute budget.
- You can customize novelty scoring by editing `config/novelty_config.json`.

---

## 8. Reproducibility & automation

- `scripts/run_acs.py` seeds both Python and NumPy RNGs using the provided `--seed` and records this seed in outputs.
- The GitHub Actions workflow `.github/workflows/tests.yml` runs:

  ```powershell
  python tests\run_tests_manual.py
  ```

  on each push/PR, helping to prevent regressions in the solver and plotting utilities.

---

## 9. Tests

To run the manual test suite locally:

```powershell
python tests\run_tests_manual.py
```

This checks core ACS functionality, basic plotting logic, and some wrappers. For deeper validation, you can compare fresh results with those under `results_backup_*/` if present.
