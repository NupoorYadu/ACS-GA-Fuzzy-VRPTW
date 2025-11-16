import json
import argparse
import os
import sys
# ensure project root is on sys.path so 'src' package can be imported when running from scripts/
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
from src.aco.acs import ACS
from src.utils.plotting import plot_routes


def load_parsed(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', required=True, help='Path to parsed JSON instance')
    parser.add_argument('--ants', type=int, default=10)
    parser.add_argument('--iters', type=int, default=30)
    parser.add_argument('--capacity', type=int, default=200)
    parser.add_argument('--out-dir', default='results/aco', help='Directory to write results and plots')
    parser.add_argument('--q0', type=float, default=0.9, help='ACS exploitation probability')
    parser.add_argument('--candidate-k', type=int, default=15, help='Number of nearest neighbors for candidate list')
    parser.add_argument('--q0-decay', type=float, default=0.0, help='Multiplicative decay fraction of q0 per iteration (0=no decay)')
    parser.add_argument('--q0-min', type=float, default=0.1, help='Minimum q0 allowed during annealing')
    parser.add_argument('--seed', type=int, default=None, help='Optional RNG seed for reproducible runs')
    parser.add_argument('--batch-root', default=None, help='If set, run ACS on all parsed JSON instances under this root and create a CSV summary')
    parser.add_argument('--no-two-opt', action='store_true', help='Disable 2-opt local search (for ablation)')
    args = parser.parse_args()

    inst = load_parsed(args.instance)
    os.makedirs(args.out_dir, exist_ok=True)

    # helper to run ACS on one instance and save outputs
    def run_one(instance_path, inst):
        acs = ACS(inst, vehicle_capacity=args.capacity, q0=args.q0, candidate_k=args.candidate_k, q0_decay=args.q0_decay, q0_min=args.q0_min, use_two_opt=(not args.no_two_opt))
        import time
        start = time.time()
        # apply seed to numpy as well for reproducibility if provided
        if args.seed is not None:
            try:
                import numpy as _np
                _np.random.seed(int(args.seed))
            except Exception:
                pass
            seed_val = int(args.seed)
        else:
            seed_val = 0
        res = acs.run(num_ants=args.ants, iterations=args.iters, seed=seed_val)
        elapsed = time.time() - start
        best_cost = res['best_cost']
        best_sol = res['best_solution']
        base = os.path.splitext(os.path.basename(instance_path))[0]
        out_json = os.path.join(args.out_dir, f'{base}_acs_result.json')
        out_png = os.path.join(args.out_dir, f'{base}_acs_routes.png')
        # include solver parameters and some ACS internals (tau0, pheromone init)
        solver_meta = {'ants': args.ants, 'iters': args.iters, 'capacity': args.capacity, 'q0': args.q0, 'candidate_k': args.candidate_k, 'q0_decay': args.q0_decay, 'q0_min': args.q0_min}
        # ACS internals if available
        try:
            solver_meta['tau0'] = float(getattr(acs, 'tau0', 0.0))
            solver_meta['pheromone_init'] = 'tau0' if hasattr(acs, 'tau0') else 'default'
        except Exception:
            solver_meta['tau0'] = None
            solver_meta['pheromone_init'] = 'unknown'
        # detect fuzzy module presence
        solver_meta['fuzzy_present'] = os.path.exists(os.path.join(proj_root, 'src', 'fuzzy'))

        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump({'best_cost': best_cost, 'best_solution': best_sol, 'params': solver_meta}, f, indent=2)
        try:
            plot_routes(inst, [[n for n in route] for route in best_sol], out_png)
        except Exception as e:
            print(f'Warning: failed to create plot for {instance_path}: {e}')
        # compute some summary stats
        customers = inst.get('customers', [])
        n_customers = len(customers)
        n_routes = len(best_sol) if best_sol else 0
        # compute per-route loads and distances
        demands = [0] + [int(c.get('demand', 0)) for c in customers]
        route_loads = []
        route_dists = []
        for route in (best_sol or []):
            load = 0
            prev = 0
            dist = 0.0
            for node in route:
                load += demands[node]
                dist += acs.dist[prev][node]
                prev = node
            dist += acs.dist[prev][0]
            route_loads.append(load)
            route_dists.append(dist)

        total_load = sum(route_loads)
        avg_load = (sum(route_loads) / len(route_loads)) if route_loads else 0.0
        max_load = max(route_loads) if route_loads else 0
        avg_route_dist = (sum(route_dists) / len(route_dists)) if route_dists else 0.0

        return {
            'instance': base,
            'best_cost': best_cost,
            'n_customers': n_customers,
            'n_routes': n_routes,
            'time_s': elapsed,
            'out_json': out_json,
            'out_png': out_png,
            'total_load': total_load,
            'avg_load': round(avg_load, 3),
            'max_load': max_load,
            'avg_route_dist': round(avg_route_dist, 3),
            'route_loads': ';'.join(str(x) for x in route_loads),
            'route_dists': ';'.join(f"{x:.2f}" for x in route_dists)
        }

    # batch mode: run across many parsed JSONs
    if args.batch_root:
        import csv
        rows = []
        for root, _, files in os.walk(args.batch_root):
            for fn in files:
                if fn.lower().endswith('.json'):
                    path = os.path.join(root, fn)
                    try:
                        inst = load_parsed(path)
                        print(f'Running ACS on {path} ...')
                        r = run_one(path, inst)
                        rows.append(r)
                        print(f" Done: {r['instance']} cost={r['best_cost']:.2f} routes={r['n_routes']} time={r['time_s']:.2f}s")
                    except Exception as e:
                        print(f'Failed on {path}: {e}')
        # write summary CSV
        summary_path = os.path.join(args.out_dir, 'summary.csv')
        with open(summary_path, 'w', newline='', encoding='utf-8') as cf:
            fieldnames = ['instance', 'best_cost', 'n_customers', 'n_routes', 'time_s', 'out_json', 'out_png', 'total_load', 'avg_load', 'max_load', 'avg_route_dist', 'route_loads', 'route_dists']
            w = csv.DictWriter(cf, fieldnames=fieldnames)
            w.writeheader()
            for row in rows:
                w.writerow(row)
        print(f'Wrote batch summary to {summary_path}')
        return

    # single instance mode
    res = run_one(args.instance, inst)
    best_cost = res['best_cost']
    best_sol = res['best_solution'] if 'best_solution' in res else []
    print(f'Best cost: {best_cost:.2f}')
    print('Routes (node indices relative to parsed JSON):')
    for i, r in enumerate(best_sol):
        print(f' Route {i+1}: {r}')
    print(f'Wrote results to {res["out_json"]}')
    if os.path.exists(res['out_png']):
        print(f'Wrote plot to {res["out_png"]}')


if __name__ == '__main__':
    main()
