import json
import os
import re
import csv
from typing import Dict, Any, List


def _is_customer_line(tokens: List[str]) -> bool:
    # Customer lines start with an integer id and contain at least 7 numeric fields
    if not tokens:
        return False
    if not re.match(r"^\d+$", tokens[0]):
        return False
    # count how many tokens are numeric (int/float)
    num_numeric = 0
    for t in tokens:
        try:
            float(t)
            num_numeric += 1
        except ValueError:
            pass
    return num_numeric >= 7


def parse_solomon(path: str) -> Dict[str, Any]:
    """Parse a Solomon VRPTW instance file into a structured dict.

    Returns a dict with keys:
      - 'customers': list of dicts with id,x,y,demand,ready_time,due_time,service_time
      - 'depot': dict (same fields for depot id 0)
      - 'vehicle_capacity': int or None
      - 'raw_lines': optional preview of first 20 non-empty lines
    """
    with open(path, 'r', encoding='utf-8') as f:
        raw = [ln.rstrip('\n') for ln in f.readlines()]

    lines = [ln for ln in raw if ln.strip()]

    customers = []
    depot = None
    vehicle_capacity = None

    # Try to find a capacity in header lines (common patterns)
    header_block = '\n'.join(lines[:20])
    cap_match = re.search(r"CAPACITY\s*[:=]?\s*(\d+)", header_block, re.IGNORECASE)
    if cap_match:
        vehicle_capacity = int(cap_match.group(1))

    # Detect CSV-like files (commas in first non-empty line) or extension
    first_nonempty = lines[0] if lines else ''
    is_csv = path.lower().endswith('.csv') or (',' in first_nonempty)

    if is_csv:
        # Parse as CSV. Support header rows with varied names.
        reader = csv.reader(lines)
        rows = list(reader)
        # Determine if first row is a header (non-numeric tokens present)
        header = [h.strip() for h in rows[0]]
        has_header = not all(re.match(r"^-?\d+(\.\d+)?$", token.strip()) for token in header)

        # Mapping of canonical names to header patterns
        def find_index(key_patterns):
            for i, h in enumerate(header):
                lh = h.lower().replace('.', '').replace('_', ' ').strip()
                for pat in key_patterns:
                    if pat in lh:
                        return i
            return None

        # Default header names patterns
        id_idx = None
        x_idx = None
        y_idx = None
        demand_idx = None
        ready_idx = None
        due_idx = None
        service_idx = None

        if has_header:
            with open(path, 'r', encoding='utf-8') as f:
                raw = f.read().splitlines()

            # Remove empty lines
            lines = [ln for ln in raw if ln.strip()]

            customers = []
            depot = None
            vehicle_capacity = None

            # Try to find a capacity in header lines (common patterns)
            header_text = '\n'.join(lines[:20])
            cap_match = re.search(r"CAPACITY\s*[:=]?\s*(\d+)", header_text, re.IGNORECASE)
            if cap_match:
                vehicle_capacity = int(cap_match.group(1))

            # Detect CSV (comma-separated) by presence of commas on header
            is_csv = False
            if lines and ',' in lines[0]:
                is_csv = True

            if is_csv:
                # Parse as CSV, try to map header names to canonical fields
                reader = csv.reader(lines)
                try:
                    header = next(reader)
                except StopIteration:
                    header = []
                # Normalize header tokens
                norm = [re.sub(r"[^a-z0-9]", "", h.lower()) for h in header]

                # mapping positions
                pos = {}
                for i, h in enumerate(norm):
                    if 'cust' in h or 'custno' in h or 'custno' == h:
                        pos['id'] = i
                    if 'xcoord' in h or h in ('x', 'xcoord'):
                        pos['x'] = i
                    if 'ycoord' in h or h in ('y', 'ycoord'):
                        pos['y'] = i
                    if 'demand' in h:
                        pos['demand'] = i
                    if 'readytime' in h or 'ready' in h:
                        pos['ready_time'] = i
                    if 'duedate' in h or 'due' in h:
                        pos['due_time'] = i
                    if 'servicetime' in h or 'service' in h:
                        pos['service_time'] = i

                for row in reader:
                    if not row:
                        continue
                    try:
                        cid = int(row[pos['id']]) if 'id' in pos else None
                    except Exception:
                        # skip malformed rows
                        continue
                    try:
                        x = float(row[pos['x']]) if 'x' in pos else 0.0
                        y = float(row[pos['y']]) if 'y' in pos else 0.0
                        demand = int(float(row[pos['demand']])) if 'demand' in pos else 0
                        ready_time = float(row[pos['ready_time']]) if 'ready_time' in pos else 0.0
                        due_time = float(row[pos['due_time']]) if 'due_time' in pos else 0.0
                        service_time = float(row[pos['service_time']]) if 'service_time' in pos else 0.0
                    except Exception:
                        # if any parsing error, skip row
                        continue
                    rec = {
                        'id': cid,
                        'x': x,
                        'y': y,
                        'demand': demand,
                        'ready_time': ready_time,
                        'due_time': due_time,
                        'service_time': service_time,
                    }
                    customers.append(rec)

            else:
                # whitespace separated / original parser fallback
                # Fallback: look for a line with two integers and interpret second as capacity
                if vehicle_capacity is None:
                    for ln in lines[:10]:
                        toks = ln.split()
                        if len(toks) >= 2 and toks[0].isdigit() and toks[1].isdigit():
                            a, b = int(toks[0]), int(toks[1])
                            if 0 < b <= 10000 and a > 0:
                                vehicle_capacity = b
                                break

                for ln in lines:
                    toks = ln.split()
                    if _is_customer_line(toks):
                        numeric = []
                        for t in toks:
                            try:
                                numeric.append(float(t))
                            except ValueError:
                                pass
                            if len(numeric) >= 7:
                                break
                        if len(numeric) < 7:
                            continue
                        cid = int(numeric[0])
                        rec = {
                            'id': cid,
                            'x': float(numeric[1]),
                            'y': float(numeric[2]),
                            'demand': int(numeric[3]),
                            'ready_time': float(numeric[4]),
                            'due_time': float(numeric[5]),
                            'service_time': float(numeric[6]),
                        }
                        customers.append(rec)

            # Heuristic: find depot as the customer with demand == 0 and ready_time == 0 or id==0/1
            depot_candidates = [c for c in customers if int(c.get('demand', 1)) == 0 and float(c.get('ready_time', 1)) == 0]
            if not depot_candidates:
                depot_candidates = [c for c in customers if int(c.get('id')) in (0, 1)]

            if depot_candidates:
                depot = depot_candidates[0]
                customers = [c for c in customers if c['id'] != depot['id']]
            elif customers:
                customers_sorted = sorted(customers, key=lambda c: c['id'])
                depot = customers_sorted[0]
                customers = customers_sorted[1:]
            else:
                depot = None

            result = {
                'file': os.path.basename(path),
                'n_lines': len(lines),
                'vehicle_capacity': vehicle_capacity,
                'depot': depot,
                'customers': customers,
                'raw_preview': lines[:20],
            }
            return result
def import_directory(dir_path: str, out_dir: str = None) -> Dict[str, Any]:
    """Parse all text files in dir_path and write JSON parsed versions to out_dir.

    Returns a summary dict with counts and written files.
    """
    if out_dir is None:
        out_dir = os.path.join(dir_path, 'parsed')
    os.makedirs(out_dir, exist_ok=True)

    summary = {'parsed_files': []}
    for root, _, files in os.walk(dir_path):
        rel_root = os.path.relpath(root, dir_path)
        out_subdir = os.path.join(out_dir, rel_root) if rel_root != '.' else out_dir
        os.makedirs(out_subdir, exist_ok=True)
        for fn in files:
            # support common instance file extensions including CSV
            if not (fn.lower().endswith('.txt') or fn.lower().endswith('.vrp') or fn.lower().endswith('.dat') or fn.lower().endswith('.csv')):
                continue
            path = os.path.join(root, fn)
            try:
                parsed = parse_solomon(path)
                out_path = os.path.join(out_subdir, os.path.splitext(fn)[0] + '.json')
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed, f, indent=2)
                summary['parsed_files'].append(out_path)
            except Exception as e:
                summary.setdefault('errors', []).append({'file': os.path.join(root, fn), 'error': str(e)})

    summary['n_parsed'] = len(summary['parsed_files'])
    return summary


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--import_dir', default='data/solomon')
    parser.add_argument('--out_dir', default=None)
    args = parser.parse_args()
    print(import_directory(args.import_dir, args.out_dir))
