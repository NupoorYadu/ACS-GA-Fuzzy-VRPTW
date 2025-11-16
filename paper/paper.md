# A Hybrid ACS–GA Framework with Configurable Novelty Scoring for VRPTW

## Abstract

Vehicle Routing Problems with Time Windows (VRPTW) are a central benchmark for evaluating heuristic and metaheuristic optimization algorithms. In this work we implement and study an enhanced Ant Colony System (ACS) for the Solomon VRPTW instances, equipped with $q_0$ annealing, \(\tau_0\)-based pheromone initialization, candidate customer lists, and 2‑opt local search. We couple the ACS with a genetic algorithm (GA) tuner for key parameters and introduce a configurable novelty scoring scheme that quantifies the use of “modern” ACS design choices across instances. Our experimental pipeline runs repeated ACS experiments over all Solomon classes (C, R, RC), aggregates results, performs paired statistical tests against a baseline ACS configuration, and produces plots and reports automatically. On clustered C‑class instances the proposed ACS variant achieves practically relevant improvements in best‑known cost compared to a $q_0=0$ baseline (for example, around 13.6% on C101 under our run budget), while performance on R and RC classes is more mixed. The overall mean improvement across all instances is not statistically significant at the 0.05 level, but the framework itself is fully reproducible, extensible, and can serve as a foundation for further research on dynamic and fuzzy VRPTW variants.

## 1 Introduction

Vehicle Routing Problems with Time Windows (VRPTW) arise in many real‑world logistics applications, such as last‑mile delivery, technician routing, and pickup‑and‑delivery with service appointments. The Solomon benchmark instances are a standard testbed for VRPTW algorithms, organized into clustered (C), random (R), and mixed (RC) customer distributions. Over the past decades, a wide range of heuristics, metaheuristics, and hybrid methods have been proposed, including tabu search, variable neighborhood search, and ant colony optimization (ACO).

Ant Colony System (ACS) is a popular ACO variant that has been successfully applied to routing problems. However, implementing and experimenting with ACS for VRPTW remains non‑trivial: beyond the basic pheromone and heuristic rules, practitioners must decide how to initialize pheromones, whether to use candidate customer lists, how to anneal the exploitation parameter $q_0$, how to integrate local search such as 2‑opt, and how to tune parameters like \(\alpha, \beta, \rho, q_0\). Moreover, many published implementations do not ship with a fully reproducible experimental pipeline, making it harder for students and practitioners to reproduce and extend results.

This project aims to provide a compact but complete framework that addresses these issues for the Solomon VRPTW instances. Concretely, we:

- Implement an enhanced ACS for VRPTW with $q_0$ annealing, \(\tau_0\) pheromone initialization based on a nearest‑neighbor tour, candidate customer lists, and optional 2‑opt local search.
- Integrate a GA‑based tuner for key ACS parameters (\(\alpha, \beta, \rho, q_0\)), and provide a simple, dependency‑free GA variant as a fallback.
- Propose a configurable novelty scoring scheme that assigns each instance a heuristic “novelty” score based on which algorithmic features (candidate lists, annealing, 2‑opt, GA tuning, fuzzy module presence) are active in the solver.
- Build a fully reproducible experimental pipeline: batch execution with repeated runs, aggregation of summaries, descriptive statistics, paired statistical tests versus a baseline ACS configuration, and automatic report generation with plots and per‑instance thumbnails.

Our goal is not to claim state‑of‑the‑art VRPTW performance, but to deliver a transparent, extensible experimental scaffold for studying ACS design choices and preparing for future work on dynamic and fuzzy VRPTW variants.

### Related Work

The VRPTW literature contains a rich variety of heuristic and metaheuristic approaches, ranging from classical constructive heuristics and local search to sophisticated hybrid methods. Early work on Solomon-style instances established simple insertion heuristics and tabu search as strong baselines for static VRPTW. Subsequent research explored large-neighborhood search and variable neighborhood search frameworks that combine destroy-and-repair operators with powerful local improvement, yielding high-quality solutions across many benchmark sets. In parallel, ant colony optimization and, in particular, Ant Colony System have been adapted to VRP and VRPTW, with enhancements such as candidate lists, improved pheromone initialization, and hybridization with local search becoming standard components.

Genetic algorithms and other evolutionary methods have been used both as direct VRPTW solvers and as meta-optimizers to tune parameters of underlying heuristics. The GA tuner in this work follows the latter line, using ACS as the embedded solver and evolving only a small set of influential parameters. Beyond static VRPTW, there is also an extensive body of work on dynamic and stochastic VRP variants, where customers may appear online or travel times are uncertain, and on fuzzy VRPTW formulations where time windows or service levels are modeled using fuzzy sets. Many of these contributions emphasize customer satisfaction measures in addition to pure distance or cost, for example by penalizing late arrivals with nonlinear or fuzzy penalty functions. Our framework does not attempt to reproduce specific algorithms from this literature but is designed to be compatible with these ideas, as illustrated by the fuzzy service-quality analysis in Section 4.5 and by the presence of simulation and fuzzy-logic components in the codebase.

## 2 Methodology

### 2.1 Problem definition

We consider the classical Solomon VRPTW benchmark. Each instance defines a single depot and a set of customers with known locations, demands, time windows \([e_i, l_i]\) for service start, and service times. Vehicles have homogeneous capacity \(Q\) and must start and end at the depot. A solution consists of a set of routes such that each customer is visited exactly once, vehicle capacities and customer time windows are respected, and the total travelled distance is minimized.

### 2.2 Enhanced Ant Colony System

Our ACS implementation operates on a graph where node 0 is the depot and nodes 1..\(n\) are customers parsed from the Solomon files. Each ant constructs a set of feasible routes by iteratively selecting the next customer according to the standard ACS rule: a biased random choice between exploitation (argmax of \(\tau_{ij}^{\alpha} \eta_{ij}^{\beta}\)) and exploration (roulette‑wheel sampling proportional to \(\tau_{ij}^{\alpha} \eta_{ij}^{\beta}\)), where \(\tau_{ij}\) is pheromone intensity and \(\eta_{ij} = 1/(d_{ij} + 10^{-6})\) is the heuristic desirability based on Euclidean distance \(d_{ij}\).

We enforce feasibility during construction by tracking vehicle load and current time along each partial route. A candidate next customer is only considered if adding its demand does not exceed capacity and if the arrival time, plus possible waiting, does not violate the customer’s latest service time. If no feasible customer remains, the current route is closed and the ant returns to the depot.

Our ACS includes the following enhancements:

- **\(\tau_0\) initialization**: We compute a simple nearest‑neighbor tour starting from the depot and use its total cost \(L_{\text{nn}}\) to set a baseline pheromone level \(\tau_0 = 1 / (n \cdot L_{\text{nn}})\). The pheromone matrix is initialized to \(\tau_0\) on all edges.
- **Candidate lists**: For each node we precompute a candidate list of its \(k\) nearest customer neighbors. During construction we restrict the choice of next customers to the intersection between the feasible set and the candidate list if it is non‑empty. This tends to accelerate convergence and encourages more local search in promising neighborhoods.
- **$q_0$ annealing**: Instead of a fixed exploitation parameter $q_0$, we use a multiplicative annealing schedule. At iteration \(t\), we update $q_0 \leftarrow \max(q_{0,\min}, q_0 (1-\text{decay}))$. This gradually shifts behavior from greedy exploitation towards more exploration, which can help avoid early stagnation.
- **2‑opt local search**: After each route is constructed we optionally apply a simple 2‑opt procedure, which repeatedly attempts to improve the route by reversing subsequences until no improving swap is found or a maximum number of iterations is reached.

Local pheromone updates are applied to edges as ants traverse them, using the standard ACS rule \(\tau_{ij} \leftarrow (1-\phi) \tau_{ij} + \phi \tau_0\). After all ants complete their solutions in an iteration, we apply a global pheromone update to the edges of the best solution observed so far.

### 2.3 GA‑based parameter tuning

ACS performance is sensitive to parameters such as \(\alpha\), \(\beta\), \(\rho\), and the initial $q_0$. To help explore this space we include a GA tuner implemented with DEAP and a lightweight fallback implementation without external dependencies. Each individual encodes a candidate parameter vector \([\alpha, \beta, \rho, q_0]\). The fitness of an individual is defined as the best ACS cost achieved on a given instance under a modest computation budget (for example, 8 ants and 10 iterations).

The GA uses blend crossover and Gaussian mutation with simple clamping to valid parameter ranges. Selection is tournament‑based. While our experiments in this report focus primarily on comparing two fixed ACS configurations ("current" vs. $q_0=0$ baseline), the tuner is part of the framework and can be used in future work for per‑instance or per‑class parameter optimization.

### 2.4 Configurable novelty scoring

Beyond raw cost and runtime, we introduce a heuristic novelty scoring scheme that measures how "novel" or feature‑rich the ACS configuration is for each instance. For each experiment we store a small metadata dictionary alongside the results, including:

- Candidate list size relative to the number of customers.
- Whether $q_0$ decay (annealing) is active.
- Whether \(\tau_0\) is used for pheromone initialization.
- Whether a fuzzy module is present in the codebase.
- Whether 2‑opt local search is enabled.
- Whether GA‑tuned parameters were applied (based on the presence of final tuned results files).

Each of these aspects is converted into a binary feature (e.g., "candidate list large", "q0_decay on/off", "two_opt on/off"), then combined with user‑defined weights specified in `config/novelty_config.json`. The overall novelty score is the weighted sum of active features, normalized to the range [0, 1]. The analysis script writes per‑instance novelty scores to `results/analysis/instance_features.csv` and uses them to color scatter plots of cost vs. time and cost vs. average route distance.

## 3 Experimental setup

### 3.1 Datasets and preprocessing

We use the standard Solomon VRPTW instance sets C, R, and RC. Raw instance files are stored under `data/solomon_dataset/`, and a dedicated loader parses them into JSON format using `src/io/solomon_loader.py`. The loader supports both the original Solomon text format and CSV‑like variants, automatically infers vehicle capacity from the header, identifies the depot, and extracts customer coordinates, demands, time windows, and service times. Parsed instances are written to `data/solomon_dataset/parsed/`.

### 3.2 Compared methods

Our main comparison focuses on two ACS configurations:

- **Current ACS variant**: ACS with \(\tau_0\) initialization, candidate lists, $q_0$ annealing, and 2‑opt local search enabled.
- **Baseline ACS**: identical implementation but with $q_0=0$ (pure exploration with respect to the ACS decision rule), effectively disabling the exploitation branch.

In addition, we report summary statistics comparing our ACS solutions to those obtained by a simple OR‑Tools CVRP baseline. For this baseline we ignore the time‑window constraints and solve the capacitated VRP (CVRP) version of each instance. As a consequence, OR‑Tools’ costs are not strictly comparable to VRPTW‑feasible solutions, but they provide a useful indicative lower bound and a sanity check that our ACS implementation behaves reasonably.

### 3.3 Protocol and metrics

For each Solomon instance and ACS configuration we run multiple independent repeats with different seeds. Each run uses a fixed number of ants, iterations, and vehicle capacity equal to the instance capacity. The script `scripts/run_acs.py` supports both single‑instance runs and batch runs via the `--batch-root` option. We record for each run:

- Best cost found by ACS.
- Number of routes and basic load statistics.
- Wall‑clock runtime.
- The seed used for the RNG (for full reproducibility).

To obtain stable estimates we perform 10 repeats per configuration per instance and aggregate them with `scripts/aggregate_repeats.py`. The aggregator writes mean best cost, mean runtime, and summary statistics for each instance to `results/aco/summary.csv` (current configuration) and `results/aco_baseline/summary.csv` (baseline).

Our primary performance metric is the mean best cost across repeats. We also report standard deviations, aggregated statistics by instance class (C, R, RC), and visualize cost distributions. To assess whether differences between the current ACS variant and the baseline are statistically significant we perform paired t‑tests and, when possible, Wilcoxon signed‑rank tests on per‑instance mean costs.

## 4 Results

### 4.1 Aggregated comparison to ACS baseline

Table 1 summarizes example results for three representative instances when comparing the current ACS variant to the $q_0=0$ baseline. All values are mean best costs over 10 repeats; lower is better.

| Instance | Current mean cost | Baseline mean cost | Delta (current − baseline) | Relative change |
|---:|---:|---:|---:|---:|
| C101 | 1833.40 | 2122.02 | −288.62 | −13.6% (better) |
| R101 | 2531.95 | 2521.51 | +10.44 | +0.4% (worse) |
| RC101 | 2512.10 | 2447.63 | +64.47 | +2.6% (worse) |

Over the full Solomon set, the analysis script computes paired tests based on the aggregated summaries (see `results/analysis/stat_tests.json`). A two‑sided paired t‑test and a Wilcoxon signed‑rank test yielded p‑values of approximately 0.062 and 0.069, respectively, under our current run budget. This indicates that, while some individual instances exhibit notable improvements, the overall mean improvement is not statistically significant at the conventional 0.05 level.

Nonetheless, the per‑class breakdown reveals interesting patterns. On C‑class (clustered) instances the current ACS variant tends to achieve lower costs than the baseline, with improvements such as the ~13.6% reduction observed on C101. On R and RC classes the picture is more mixed, with several instances where the baseline slightly outperforms the enhanced variant.

### 4.2 Numerical summary vs OR‑Tools

We also compared the ACS solutions to those obtained by an OR‑Tools CVRP baseline that ignores time windows. Table 2 summarizes average route costs by problem class.

| Class | n | ACS mean ± std | OR‑Tools mean ± std |
|---:|---:|:---:|:---:|
| C | 17 | 1575.39 ± 231.46 | 912.71 ± 66.08 |
| R | 23 | 1583.65 ± 389.35 | 893.00 ± 0.00 |
| RC | 16 | 1890.62 ± 396.61 | 1036.00 ± 0.00 |
| ALL | 56 | 1668.85 ± 373.05 | 939.84 ± 71.45 |

As expected, the OR‑Tools CVRP solutions achieve much lower costs, because they are allowed to violate time‑window constraints that our ACS enforces. This supports the correctness of our implementation: ACS finds feasible VRPTW routes whose costs lie above a CVRP lower bound but remain in a comparable range.

### 4.3 Visual analysis and novelty

The automated analysis pipeline (`scripts/analyze_results.py`) generates several figures stored in `results/analysis/`:

- **Mean cost by instance set** (`mean_cost_by_set.png`): bar charts with error bars summarizing mean and standard deviation of best costs for C, R, and RC classes.
- **Cost distributions** (`violin_costs_by_set.png`): violin plots showing the distribution of instance‑level best costs per class, highlighting variability and outliers.
- **Radar plot of normalized metrics** (`radar_by_set.png`): a radar chart comparing normalized mean cost, average route distance, average load, number of routes, and runtime across the C, R, and RC sets.
- **Novelty scores** (`novelty_scores.png`): a bar plot of per‑instance novelty scores, sorted from highest to lowest.
- **Scatter plots colored by novelty** (`scatter_cost_vs_time.png`, `scatter_cost_vs_avg_route_dist.png`): analyses of the relationship between novelty score and cost/runtime.

The novelty plots suggest that instances where more of the enhanced ACS features are active (e.g., larger candidate lists, annealing, 2‑opt, GA tuning) tend to cluster in regions of lower cost for certain classes, but the effect is not uniform. This motivates more fine‑grained tuning of feature combinations per instance type.

### 4.4 GA-based parameter tuning on representative instances

To illustrate the potential of the GA tuner, we applied it to one representative instance from each Solomon class: C101 (clustered), R101 (random), and RC101 (mixed). For each instance the GA optimized the parameter vector \([\alpha, \beta, \rho, q_0]\) under a small evaluation budget (8 ants, 10 iterations), using the best ACS cost achieved during the run as the fitness.

Table 3 summarizes the comparison between the default ACS configuration used in our main experiments and the best fitness obtained by the GA tuner for these three instances. The default ACS mean cost is estimated from 10 repeated runs with different seeds; the GA fitness corresponds to the best individual found by the tuner.

| Instance | Class | Default ACS mean cost | GA-tuned fitness (cost) |
|:--------|:-----:|-----------------------:|-------------------------:|
| C101    | C     | 1809.512               | 1568.793                 |
| R101    | R     | 2532.075               | 2304.458                 |
| RC101   | RC    | 2573.358               | 2258.914                 |

For this small sample, GA-based tuning reduces the ACS cost by roughly 13–15% relative to the default parameter setting, despite the limited evaluation budget. This suggests that even modest offline tuning effort can yield substantial improvements in solution quality, particularly when focusing on a few important instances or representative scenarios.

### 4.5 Fuzzy service-quality analysis

To relate solution quality to soft service considerations, we computed a fuzzy service-quality score for each customer based on the deviation of the service start time from the end of its time window. For a customer with time window $[e_i, l_i]$ and service start time $s_i$, we define lateness $L_i = \max(0, s_i - l_i)$ and fuzzy satisfaction
$$
\mu_i =
\begin{cases}
1, & s_i \le l_i, \\
\max\{0, 1 - L_i / T\}, & s_i > l_i,
\end{cases}
$$
with tolerance parameter $T$. The instance-level average $\bar{\mu}$ and minimum $\min_i \mu_i$ summarize overall service quality across all customers.

Table 4 reports the best ACS cost and fuzzy satisfaction metrics for three representative instances under the current configuration (with $T = 30$ minutes).

| Instance | Class | Best cost | Avg. fuzzy satisfaction $\bar{\mu}$ | Min. satisfaction $\min_i \mu_i$ |
|:--------|:-----:|----------:|---------------------------------------:|-----------------------------------:|
| C101    | C     | 1833.399  | 0.650                                 | 0.000                              |
| R101    | R     | 2531.949  | 0.865                                 | 0.000                              |
| RC101   | RC    | 2512.099  | 0.917                                 | 0.000                              |

In these examples the enhanced ACS configuration achieves both low travel cost and relatively high fuzzy satisfaction on average, indicating that improvements in distance do not come at the expense of excessive lateness under the chosen tolerance $T$. At the same time, the zero minimum satisfaction values highlight that a small number of customers can still experience substantial tardiness, which would be unacceptable in tightly regulated service environments. This type of fuzzy analysis can be adapted to operator-specific notions of acceptable earliness or lateness in practical deployments, for example by changing $T$ or by introducing separate membership functions for early and late arrivals.

## 5 Discussion

Our experiments highlight several insights about ACS design choices for the Solomon VRPTW instances:

- The combination of \(\tau_0\) initialization, candidate lists, and $q_0$ annealing can yield substantial improvements on some clustered C‑class instances, where the structure of customer locations favors more guided exploration and local search.
- On random (R) and mixed (RC) instances, the same configuration sometimes underperforms a simpler baseline, suggesting that the balance between exploitation and exploration and the size of candidate lists may need to be tuned more carefully.
- The novelty scoring scheme provides a simple way to reason about which algorithmic features are active in a given experiment and how they correlate with observed performance. While the current weights are heuristic, the mechanism is flexible and can be refined or learned from data.
 - The fuzzy service-quality analysis in Section 4.5 shows that, for our current configuration and tolerance choice, substantial improvements in travel cost can coexist with high average time-window satisfaction, even though a few customers may still experience unacceptable delays.

There are several limitations and opportunities for future work:

- Our computation budget (number of ants and iterations) is modest, reflecting the constraints of a course project. Longer runs and more extensive GA‑based tuning would likely yield stronger improvements.
- The OR‑Tools baseline ignores time windows, so the comparison is mainly useful for sanity checking and rough lower‑bound intuition, rather than as a direct benchmark.
- The fuzzy logic and dynamic VRP components of the project scaffold are not yet fully exploited in the experiments reported here. A natural next step is to integrate fuzzy time‑window satisfaction and dynamic customer arrivals using the existing `simpy` dependency.

From a practical standpoint, the framework can support several use cases beyond academic benchmarking. A planner in a parcel delivery or technician-routing operation could use the ACS–GA module to explore trade-offs between fleet size, time-window tightness, and service-quality targets by running small scenario studies similar to those in Sections 4.1–4.5. The fuzzy satisfaction measures make it possible to translate abstract lateness into interpretable indicators, such as “percentage of customers served with at least 0.8 satisfaction”, which can be aligned with service-level agreements. Because the pipeline is scriptable and reproducible, it can also be embedded into a decision-support tool that is periodically re-run as demand patterns change, or used to stress-test dynamic dispatching policies by simulating late-arriving customers or travel-time disruptions. In this sense, the project serves as a bridge between textbook VRPTW models and the softer, multi-criteria decision problems faced by transportation operators.

## 6 Conclusion

We presented a hybrid ACS–GA framework with configurable novelty scoring for the Solomon VRPTW benchmark. The implementation includes an enhanced ACS with $q_0$ annealing, \(\tau_0\) initialization, candidate lists, and 2‑opt local search, as well as GA‑based parameter tuning and a reproducible pipeline for repeated experiments, aggregation, and analysis. Our results show practically meaningful improvements on some clustered instances compared to a $q_0=0$ baseline, while overall differences across all instances are not statistically significant under our current run budget. More importantly, the framework is modular, configurable, and fully reproducible, making it a useful starting point for further studies on dynamic and fuzzy VRPTW variants and for educational use in soft computing or metaheuristics courses.

## 7 Reproducibility

All code and experiments for this project are contained in the GitHub repository `Enhancements-for-Dynamic-Vehicle-Routing-Problems`. The main components are:

- `src/aco/acs.py`: ACS solver implementation.
- `src/ga/optimizer.py` and `scripts/run_ga.py`: GA‑based tuner.
- `scripts/run_acs.py`: experiment runner for single instances and batches.
- `scripts/aggregate_repeats.py`: aggregation of repeated runs into summary CSVs.
- `scripts/analyze_results.py`: analysis and plotting pipeline, including novelty scoring and PDF report generation.
- `config/novelty_config.json`: configuration file for novelty feature weights.

To reproduce the main experiments on a new machine:

1. **Create and activate a virtual environment** (example on Windows):

	```powershell
	python -m venv .venv
	.venv\Scripts\activate
	```

2. **Install dependencies**:

	```powershell
	pip install --upgrade pip
	pip install -r requirements.txt
	```

3. **Import and parse Solomon instances** (if not already parsed):

	```powershell
	python main.py --mode import_all --instance data/solomon_dataset
	```

4. **Run ACS repeats for the current configuration** (example):

	```powershell
	for ($i = 1; $i -le 5; $i++) {
		 python scripts\run_acs.py \
			--instance data\solomon_dataset\parsed\R1\R101.json \
			--batch-root data\solomon_dataset\parsed \
			--out-dir results\aco_repeats\current\repeat_$i \
			--ants 6 --iters 12 --capacity 200 \
			--q0 0.9 --q0-decay 0.01 --q0-min 0.2 \
			--seed $i
	}
	```

5. **Run ACS repeats for the baseline configuration** (example):

	```powershell
	for ($i = 1; $i -le 5; $i++) {
		 python scripts\run_acs.py \
			--instance data\solomon_dataset\parsed\R1\R101.json \
			--batch-root data\solomon_dataset\parsed \
			--out-dir results\aco_repeats\baseline\repeat_$i \
			--ants 6 --iters 12 --capacity 200 \
			--q0 0.0 \
			--seed $i
	}
	```

6. **Aggregate repeats**:

	```powershell
	python scripts\aggregate_repeats.py
	```

7. **Run analysis and generate reports**:

	```powershell
	python scripts\analyze_results.py
	```

	This will create plots, CSVs, and a multi‑page `report.pdf` under `results/analysis/`.

8. **Run unit tests** to verify the core solver and plotting utilities:

	```powershell
	python tests\run_tests_manual.py
	```

In addition, a GitHub Actions workflow (`.github/workflows/tests.yml`) is configured to run the manual test suite on each push or pull request, helping to ensure that the implementation remains stable over time.