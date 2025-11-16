"""
Aggregate per-instance results across repeated batch runs.
Usage: python scripts/aggregate_repeats.py
It expects directories:
 - results/aco_repeats/current/repeat_1..repeat_N/summary.csv
 - results/aco_repeats/baseline/repeat_1..repeat_N/summary.csv
It will write aggregated CSVs to:
 - results/aco/summary.csv (current aggregated)
 - results/aco_baseline/summary.csv (baseline aggregated)
And also to results/aco_agg/ and results/aco_baseline_agg/ for safety.
"""
import csv
import os
import glob
import statistics
from collections import defaultdict

BASE = 'results/aco_repeats'
OUT_CURR = 'results/aco_agg'
OUT_BASE = 'results/aco_baseline_agg'
os.makedirs(OUT_CURR, exist_ok=True)
os.makedirs(OUT_BASE, exist_ok=True)


def read_summary(path):
    rows = {}
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            inst = r['instance']
            rows[inst] = r
    return rows


def collect(repeat_dirs):
    per_inst = defaultdict(list)
    for d in repeat_dirs:
        sfile = os.path.join(d, 'summary.csv')
        if not os.path.exists(sfile):
            continue
        rows = read_summary(sfile)
        for inst, r in rows.items():
            # pick numeric fields we care about
            per_inst[inst].append({
                'best_cost': float(r.get('best_cost', 'nan')),
                'time_s': float(r.get('time_s', 'nan')),
                'n_routes': int(r.get('n_routes', 0)),
                'n_customers': int(r.get('n_customers', 0)),
                'out_json': r.get('out_json',''),
                'out_png': r.get('out_png',''),
                'total_load': r.get('total_load',''),
                'avg_load': r.get('avg_load',''),
                'max_load': r.get('max_load',''),
                'avg_route_dist': r.get('avg_route_dist',''),
                'route_loads': r.get('route_loads',''),
                'route_dists': r.get('route_dists',''),
            })
    return per_inst


def aggregate_and_write(per_inst, outdir, write_target=None):
    os.makedirs(outdir, exist_ok=True)
    outcsv = os.path.join(outdir, 'summary.csv')
    fieldnames = ['instance','best_cost','n_customers','n_routes','time_s','out_json','out_png','total_load','avg_load','max_load','avg_route_dist','route_loads','route_dists']
    with open(outcsv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for inst, vals in sorted(per_inst.items()):
            costs = [v['best_cost'] for v in vals]
            times = [v['time_s'] for v in vals]
            n_routes = [v['n_routes'] for v in vals]
            n_customers = vals[0]['n_customers'] if vals else 0
            # pick representative strings from the first repeat (params and route details)
            rep = vals[0] if vals else {}
            row = {
                'instance': inst,
                'best_cost': statistics.mean(costs) if costs else float('nan'),
                'n_customers': n_customers,
                'n_routes': int(round(statistics.mean(n_routes))) if n_routes else 0,
                'time_s': statistics.mean(times) if times else float('nan'),
                'out_json': rep.get('out_json',''),
                'out_png': rep.get('out_png',''),
                'total_load': rep.get('total_load',''),
                'avg_load': rep.get('avg_load',''),
                'max_load': rep.get('max_load',''),
                'avg_route_dist': rep.get('avg_route_dist',''),
                'route_loads': rep.get('route_loads',''),
                'route_dists': rep.get('route_dists',''),
            }
            writer.writerow(row)
    # optionally copy to target location
    if write_target:
        os.makedirs(os.path.dirname(write_target), exist_ok=True)
        with open(outcsv, 'rb') as src, open(write_target, 'wb') as dst:
            dst.write(src.read())
    return outcsv


def main():
    # find repeat dirs
    curr_dirs = sorted(glob.glob(os.path.join(BASE, 'current', 'repeat_*')))
    base_dirs = sorted(glob.glob(os.path.join(BASE, 'baseline', 'repeat_*')))
    print('Found', len(curr_dirs), 'current repeats and', len(base_dirs), 'baseline repeats')

    curr_per = collect(curr_dirs)
    base_per = collect(base_dirs)

    cur_out = aggregate_and_write(curr_per, OUT_CURR, write_target='results/aco/summary.csv')
    base_out = aggregate_and_write(base_per, OUT_BASE, write_target='results/aco_baseline/summary.csv')

    print('Wrote aggregated current summary to', cur_out)
    print('Wrote aggregated baseline summary to', base_out)


if __name__ == '__main__':
    main()
