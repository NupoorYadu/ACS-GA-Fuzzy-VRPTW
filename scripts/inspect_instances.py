import json
import os
import csv
import argparse

# Default paths
DATA_ROOT = os.path.join('data', 'solomon')
OUT_CSV = os.path.join('results', 'instances_summary.csv')


def inspect_instances(data_root: str, out_csv: str):
    """Inspect parsed instances under data_root and write summary to out_csv."""
    rows = []
    if not os.path.isdir(data_root):
        raise FileNotFoundError(f"Dataset root not found: {data_root}")
    # Support two layouts:
    # 1) data_root/<group>/parsed/*.json  (grouped parsed inside each group)
    # 2) data_root/parsed/<group>/*.json  (single parsed folder at root)
    parsed_root_alt = os.path.join(data_root, 'parsed')
    if os.path.isdir(parsed_root_alt):
        groups = sorted([d for d in os.listdir(parsed_root_alt) if os.path.isdir(os.path.join(parsed_root_alt, d))])
        parsed_base = parsed_root_alt
    else:
        groups = sorted([d for d in os.listdir(data_root) if os.path.isdir(os.path.join(data_root, d))])
        parsed_base = None

    for group in groups:
        if parsed_base:
            parsed_dir = os.path.join(parsed_base, group)
            raw_dir = os.path.join(data_root, group, 'raw')
        else:
            group_dir = os.path.join(data_root, group)
            parsed_dir = os.path.join(group_dir, 'parsed')
            raw_dir = os.path.join(group_dir, 'raw')
        if not os.path.isdir(parsed_dir):
            # skip if no parsed folder for this group
            continue
        for fn in sorted(os.listdir(parsed_dir)):
            if not fn.lower().endswith('.json'):
                continue
            path = os.path.join(parsed_dir, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f'Error reading {path}: {e}')
                continue
            n_customers = len(data.get('customers', []))
            capacity = data.get('vehicle_capacity')
            depot = data.get('depot')
            depot_found = bool(depot)
            avg_demand = None
            xs = []
            ys = []
            demands = []
            for c in data.get('customers', []):
                try:
                    xs.append(float(c.get('x', 0)))
                    ys.append(float(c.get('y', 0)))
                    demands.append(float(c.get('demand', 0)))
                except Exception:
                    pass
            if demands:
                avg_demand = sum(demands) / len(demands)
            bbox = None
            if xs and ys:
                bbox = (min(xs), min(ys), max(xs), max(ys))
            rows.append({
                'group': group,
                'instance': os.path.splitext(fn)[0],
                'n_customers': n_customers,
                'vehicle_capacity': capacity,
                'depot_found': depot_found,
                'avg_demand': avg_demand,
                'bbox_minx': bbox[0] if bbox else None,
                'bbox_miny': bbox[1] if bbox else None,
                'bbox_maxx': bbox[2] if bbox else None,
                'bbox_maxy': bbox[3] if bbox else None,
                'parsed_path': path,
                'raw_path': os.path.join(raw_dir, os.path.splitext(fn)[0] + '.csv') if os.path.isdir(raw_dir) else None,
            })

    # Ensure results dir exists
    os.makedirs(os.path.dirname(out_csv) or '.', exist_ok=True)

    # Write CSV
    with open(out_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['group', 'instance', 'n_customers', 'vehicle_capacity', 'depot_found', 'avg_demand', 'bbox_minx', 'bbox_miny', 'bbox_maxx', 'bbox_maxy', 'parsed_path', 'raw_path']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Print brief table
    print(f'Wrote {len(rows)} rows to {out_csv}')
    print('Sample:')
    for r in rows[:10]:
        print(f"{r['group']}/{r['instance']}: customers={r['n_customers']} cap={r['vehicle_capacity']} depot={r['depot_found']} avg_demand={r['avg_demand']}")



rows = []
 

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inspect parsed Solomon instances and write a CSV summary')
    parser.add_argument('--data-root', default=DATA_ROOT, help='Root folder containing instance groups (default: data/solomon)')
    parser.add_argument('--out', default=OUT_CSV, help='Output CSV path (default: results/instances_summary.csv)')
    args = parser.parse_args()
    inspect_instances(args.data_root, args.out)
