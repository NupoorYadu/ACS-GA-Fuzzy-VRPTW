"""Run baseline solvers (ORTools) over a set of instances and save simple summaries."""
import os
import sys
import argparse
import json
from glob import glob

proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from src.baselines import ortools_wrapper


def find_instances(root, pattern='**/*.json'):
    return sorted(glob(os.path.join(root, pattern), recursive=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instances', default=os.path.join('data', 'solomon_dataset', 'parsed'), help='Root with parsed instances or file')
    parser.add_argument('--out-dir', default='results/baselines')
    parser.add_argument('--time-limit', type=int, default=10)
    parser.add_argument('--capacity', type=int, default=200)
    args = parser.parse_args()

    if os.path.isfile(args.instances) and args.instances.lower().endswith('.json'):
        insts = [args.instances]
    else:
        insts = find_instances(args.instances)
    os.makedirs(args.out_dir, exist_ok=True)
    for instp in insts:
        with open(instp, 'r', encoding='utf-8') as f:
            inst = json.load(f)
        base = os.path.splitext(os.path.basename(instp))[0]
        out = os.path.join(args.out_dir, f'{base}_baseline.json')
        try:
            res = ortools_wrapper.run_ortools_cvrp(inst, capacity=args.capacity, time_limit_s=args.time_limit)
            with open(out, 'w', encoding='utf-8') as of:
                json.dump(res, of, indent=2)
            print('Wrote baseline for', base)
        except ImportError as e:
            print('Skipping baseline for', base, '-', e)

if __name__ == '__main__':
    main()
