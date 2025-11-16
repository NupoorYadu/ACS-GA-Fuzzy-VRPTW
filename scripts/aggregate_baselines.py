"""Aggregate OR-Tools baseline JSONs (results/baselines/*.json) into a CSV compatible
with the rest of the analysis pipeline (writes results/aco_baseline_agg/summary.csv).
"""
import json
import os
from glob import glob
import math
import csv

BASE_IN = 'results/baselines'
OUT_DIR = 'results/aco_baseline_agg'
os.makedirs(OUT_DIR, exist_ok=True)


def find_parsed_instance(name):
    # search parsed dataset for a matching basename
    for root, _, files in os.walk(os.path.join('data', 'solomon_dataset', 'parsed')):
        for fn in files:
            if fn.lower() == f'{name.lower()}.json':
                return os.path.join(root, fn)
    return None


def compute_route_distance(route, nodes):
    # route: list of node indices (customers starting at 1); nodes includes depot at index 0
    dist = 0.0
    prev = 0
    for node in route:
        ni = int(node)
        x1 = float(nodes[prev].get('x', 0))
        y1 = float(nodes[prev].get('y', 0))
        x2 = float(nodes[ni].get('x', 0))
        y2 = float(nodes[ni].get('y', 0))
        dist += math.hypot(x2 - x1, y2 - y1)
        prev = ni
    # return to depot
    x1 = float(nodes[prev].get('x', 0))
    y1 = float(nodes[prev].get('y', 0))
    x2 = float(nodes[0].get('x', 0))
    y2 = float(nodes[0].get('y', 0))
    dist += math.hypot(x2 - x1, y2 - y1)
    return dist


def main():
    rows = []
    for path in sorted(glob(os.path.join(BASE_IN, '*_baseline.json'))):
        base = os.path.basename(path).replace('_baseline.json', '')
        with open(path, 'r', encoding='utf-8') as f:
            j = json.load(f)
        routes = j.get('routes', [])
        total_distance = float(j.get('total_distance', j.get('total_dist', 0)))

        parsed = None
        parsed_path = find_parsed_instance(base)
        if parsed_path:
            with open(parsed_path, 'r', encoding='utf-8') as pf:
                parsed = json.load(pf)
            nodes = [parsed.get('depot')] + parsed.get('customers', [])
            demands = [0] + [int(c.get('demand', 0)) for c in parsed.get('customers', [])]
        else:
            nodes = [{'x': 0, 'y': 0}]
            demands = []

        n_customers = len(nodes) - 1
        n_routes = len(routes)
        # compute per-route loads and distances if possible
        route_loads = []
        route_dists = []
        for r in routes:
            load = 0
            for node in r:
                idx = int(node)
                if idx - 1 < len(demands):
                    try:
                        load += demands[idx]
                    except Exception:
                        pass
            route_loads.append(load)
            try:
                rd = compute_route_distance(r, nodes)
            except Exception:
                rd = 0.0
            route_dists.append(rd)

        row = {
            'instance': base,
            'best_cost': total_distance,
            'n_customers': n_customers,
            'n_routes': n_routes,
            'time_s': '',
            'out_json': path,
            'out_png': '',
            'total_load': sum(route_loads) if route_loads else '',
            'avg_load': round(sum(route_loads)/len(route_loads), 3) if route_loads else '',
            'max_load': max(route_loads) if route_loads else '',
            'avg_route_dist': round(sum(route_dists)/len(route_dists), 3) if route_dists else '',
            'route_loads': ';'.join(str(x) for x in route_loads),
            'route_dists': ';'.join(f"{x:.2f}" for x in route_dists)
        }
        rows.append(row)

    outcsv = os.path.join(OUT_DIR, 'summary.csv')
    fieldnames = ['instance','best_cost','n_customers','n_routes','time_s','out_json','out_png','total_load','avg_load','max_load','avg_route_dist','route_loads','route_dists']
    with open(outcsv, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in sorted(rows, key=lambda x: x['instance']):
            w.writerow(r)

    print('Wrote aggregated baseline summary to', outcsv)


if __name__ == '__main__':
    main()
