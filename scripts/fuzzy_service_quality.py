import json
import os
from statistics import mean

# ensure project root on path if needed
import sys
from pathlib import Path

proj_root = Path(__file__).resolve().parents[1]
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from src.aco.acs import ACS


def compute_fuzzy_scores(instance, solution, dist, T=30.0):
    """
    Compute average and minimum fuzzy satisfaction for one instance/solution.

    instance: parsed Solomon JSON (with depot + customers)
    solution: list of routes (list of node indices, 1..n; 0 is depot)
    dist: distance matrix from ACS.dist
    T: lateness tolerance
    """
    customers = instance.get("customers", [])
    # build arrays indexed by node index (0 = depot)
    ready = [float(instance.get("depot", {}).get("ready_time", 0.0))]
    due = [float(instance.get("depot", {}).get("due_time", 0.0))]
    service = [float(instance.get("depot", {}).get("service_time", 0.0))]
    for c in customers:
        ready.append(float(c.get("ready_time", 0.0)))
        due.append(float(c.get("due_time", 0.0)))
        service.append(float(c.get("service_time", 0.0)))

    mu_vals = []
    for route in solution:
        time = 0.0
        prev = 0
        for node in route:
            travel = dist[prev][node]
            arrive = time + travel
            start = max(arrive, ready[node])
            L = max(0.0, start - due[node])
            if L <= 0:
                mu = 1.0
            else:
                mu = max(0.0, 1.0 - L / T)
            mu_vals.append(mu)
            time = start + service[node]
            prev = node

    if not mu_vals:
        return 1.0, 1.0
    return mean(mu_vals), min(mu_vals)


def summarize_instance(instance_path, result_path, T=30.0):
    with open(instance_path, "r", encoding="utf-8") as f:
        inst = json.load(f)
    with open(result_path, "r", encoding="utf-8") as f:
        res = json.load(f)

    # rebuild ACS just to get dist matrix
    acs = ACS(inst)
    solution = res.get("best_solution", [])
    best_cost = float(res.get("best_cost", float("nan")))
    avg_mu, min_mu = compute_fuzzy_scores(inst, solution, acs.dist, T=T)
    return best_cost, avg_mu, min_mu


def main():
    # example: C101, R101, RC101 current ACS results in results/aco_agg or single-run JSONs
    cases = [
        ("C101", "data/solomon_dataset/parsed/C1/C101.json", "results/aco/C101_acs_result.json"),
        ("R101", "data/solomon_dataset/parsed/R1/R101.json", "results/aco/R101_acs_result.json"),
        ("RC101", "data/solomon_dataset/parsed/RC1/RC101.json", "results/aco/RC101_acs_result.json"),
    ]

    print("Instance,Class,BestCost,AvgFuzzy,MinFuzzy")
    for inst_name, inst_path, res_path in cases:
        if not (os.path.exists(inst_path) and os.path.exists(res_path)):
            continue
        cls = inst_name[0] if inst_name.startswith(("C", "R")) else "RC"
        best_cost, avg_mu, min_mu = summarize_instance(inst_path, res_path)
        print(f"{inst_name},{cls},{best_cost:.3f},{avg_mu:.3f},{min_mu:.3f}")


if __name__ == "__main__":
    main()