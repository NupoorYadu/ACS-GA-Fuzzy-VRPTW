import json
import os
from statistics import mean

ROOT = "results/ga_eval"


def collect_best_costs(instance: str, variant: str):
    """Collect best_cost values for a given instance and variant (e.g. default)."""
    base_dir = os.path.join(ROOT, instance, variant)
    vals = []
    for root, _, files in os.walk(base_dir):
        for fn in files:
            if not fn.endswith("_acs_result.json"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                vals.append(float(data.get("best_cost", float("nan"))))
            except Exception:
                pass
    return vals


def main():
    instances = ["C101", "R101", "RC101"]
    variants = ["default"]  # extend with "tuned" later if needed
    print("Instance,Variant,N,MeanBestCost")
    for inst in instances:
        for var in variants:
            vals = collect_best_costs(inst, var)
            if not vals:
                continue
            print(f"{inst},{var},{len(vals)},{mean(vals):.3f}")


if __name__ == "__main__":
    main()
