import argparse
import json
import os
import sys
# ensure project root is importable
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from src.ga.optimizer import run_ga, evaluate_params


def load_parsed(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', required=True, help='Path to parsed JSON instance')
    parser.add_argument('--pop', type=int, default=12)
    parser.add_argument('--gens', type=int, default=10)
    parser.add_argument('--ants', type=int, default=8)
    parser.add_argument('--iters', type=int, default=12)
    parser.add_argument('--capacity', type=int, default=200)
    args = parser.parse_args()

    inst = load_parsed(args.instance)
    res = run_ga(inst, pop_size=args.pop, gens=args.gens, ants=args.ants, iters=args.iters, capacity=args.capacity)
    print('Best individual:', res['best_individual'])
    print('Best fitness:', res['best_fitness'])


if __name__ == '__main__':
    main()
