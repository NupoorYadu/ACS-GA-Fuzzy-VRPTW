"""
Orchestrate repeated experiments, baselines, and simple ablation studies.
This script will:
 - run multiple repeats of ACS on provided instances
 - optionally run baseline (q0=0) and ablation variants
 - call scripts/aggregate_repeats.py to produce aggregated summaries

Usage examples:
 python scripts/auto_experiments.py --instances data/solomon_dataset/parsed/SAMPLE --repeats 3 --out-root results/aco_repeats --mode all

"""
import os
import sys
import argparse
import subprocess
from glob import glob

proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

DEFAULT_INST_ROOT = os.path.join('data', 'solomon_dataset', 'parsed')


def find_instances(root, pattern='**/*.json'):
    p = os.path.join(root, pattern)
    return sorted(glob(p, recursive=True))


def run_cmd(cmd, cwd=None):
    print('CMD:', ' '.join(cmd))
    res = subprocess.run(cmd, cwd=cwd)
    if res.returncode != 0:
        raise SystemExit(res.returncode)


def run_repeats(inst_paths, repeats, out_root, ants, iters, capacity, seed_base=1000, name='current', extra_args=None):
    extra_args = extra_args or []
    os.makedirs(out_root, exist_ok=True)
    for r in range(1, repeats + 1):
        rep_dir = os.path.join(out_root, f'repeat_{r}')
        os.makedirs(rep_dir, exist_ok=True)
        for inst in inst_paths:
            base = os.path.splitext(os.path.basename(inst))[0]
            inst_out = os.path.join(rep_dir, base)
            os.makedirs(inst_out, exist_ok=True)
            cmd = [sys.executable, 'scripts/run_acs.py', '--instance', inst, '--ants', str(ants), '--iters', str(iters), '--out-dir', inst_out, '--capacity', str(capacity), '--seed', str(seed_base + r)]
            cmd += extra_args
            run_cmd(cmd)
    print('Done runs for', name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instances', default=DEFAULT_INST_ROOT, help='Root folder with parsed instance JSONs or a single file')
    parser.add_argument('--pattern', default='**/*.json')
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--out-root', default='results/aco_repeats')
    parser.add_argument('--ants', type=int, default=8)
    parser.add_argument('--iters', type=int, default=12)
    parser.add_argument('--capacity', type=int, default=200)
    parser.add_argument('--seed-base', type=int, default=1000)
    parser.add_argument('--mode', choices=['current', 'baseline', 'ablation', 'all'], default='current')
    parser.add_argument('--ablation-features', nargs='*', default=['no_two_opt', 'no_candidates', 'no_q0_anneal'])
    args = parser.parse_args()

    # resolve instances
    if os.path.isfile(args.instances) and args.instances.lower().endswith('.json'):
        insts = [args.instances]
    else:
        insts = find_instances(args.instances, pattern=args.pattern)
    if not insts:
        print('No instances found under', args.instances)
        return

    print('Found', len(insts), 'instances; running', args.repeats, 'repeats each')

    # run current
    if args.mode in ('current', 'all'):
        cur_out = os.path.join(args.out_root, 'current')
        run_repeats(insts, args.repeats, cur_out, args.ants, args.iters, args.capacity, seed_base=args.seed_base, name='current')

    # run baseline (e.g., q0=0 exploitation disabled)
    if args.mode in ('baseline', 'all'):
        base_out = os.path.join(args.out_root, 'baseline')
        extra = ['--q0', '0.0']
        run_repeats(insts, args.repeats, base_out, args.ants, args.iters, args.capacity, seed_base=args.seed_base + 10000, name='baseline', extra_args=extra)

    # ablation studies: create variants by toggling features
    if args.mode in ('ablation', 'all'):
        for feat in args.ablation_features:
            print('Running ablation for feature', feat)
            ab_name = f'ablation_{feat}'
            ab_out = os.path.join(args.out_root, ab_name)
            extra = []
            if feat == 'no_two_opt':
                extra += ['--no-two-opt']
            if feat == 'no_candidates':
                extra += ['--candidate-k', '0']
            if feat == 'no_q0_anneal':
                extra += ['--q0-decay', '0.0']
            run_repeats(insts, args.repeats, ab_out, args.ants, args.iters, args.capacity, seed_base=args.seed_base + 20000, name=ab_name, extra_args=extra)

    # after runs, call aggregate_repeats.py which expects the standard folder layout
    print('Aggregating repeats...')
    run_cmd([sys.executable, 'scripts/aggregate_repeats.py'])
    print('All done')


if __name__ == '__main__':
    main()
