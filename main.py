#!/usr/bin/env python3
import argparse
from src.io.solomon_loader import import_directory, parse_solomon

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='smoke')
    parser.add_argument('--instance', default=None)
    args = parser.parse_args()

    if args.mode == 'smoke':
        print('Smoke test: project skeleton is ready.')
        if args.instance:
            try:
                inst = parse_solomon(args.instance)
                print(f"Loaded instance: {inst.get('n_lines','?')} non-empty lines (depot: {inst.get('depot') is not None})")
            except Exception as e:
                print(f'Could not load instance: {e}')
    elif args.mode == 'import_all':
        import_dir = args.instance or 'data/solomon'
        print(f'Importing all instances from {import_dir} ...')
        summary = import_directory(import_dir)
        print(f"Imported {summary.get('n_parsed',0)} files. Parsed files written to {import_dir}/parsed/")
    else:
        print('No other modes implemented yet.')

if __name__ == '__main__':
    main()
