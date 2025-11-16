import csv
import json
import os
from collections import defaultdict
import math

import matplotlib.pyplot as plt
import numpy as np
from statistics import mean, stdev
import argparse

SUMMARY = 'results/aco/summary.csv'
OUTDIR = 'results/analysis'
os.makedirs(OUTDIR, exist_ok=True)

# configuration for novelty features
# Load novelty config from file if present, otherwise fall back to defaults.
NOVELTY_CONFIG_PATH = 'config/novelty_config.json'
DEFAULT_NOVELTY_CONFIG = {
    'candidate_k_relative_thresh': 0.15,  # candidate_k / n_customers > this is considered "large"
    'weights': {
        'candidate_k_large': 1.0,
        'q0_decay': 1.0,
        'tau0_present': 0.8,
        'pheromone_init_tau0': 0.8,
        'fuzzy_present': 1.2,
        'two_opt': 0.6,
        'ga_tuned': 1.2,
    }
}

def load_novelty_config(path=NOVELTY_CONFIG_PATH):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                # basic validation
                if 'weights' in cfg and isinstance(cfg['weights'], dict):
                    return cfg
    except Exception:
        pass
    return DEFAULT_NOVELTY_CONFIG

NOVELTY_CONFIG = load_novelty_config()


def load_summary(path=SUMMARY):
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            # parse numeric fields
            r['best_cost'] = float(r['best_cost'])
            r['n_customers'] = int(r['n_customers'])
            r['n_routes'] = int(r['n_routes'])
            r['time_s'] = float(r['time_s'])
            r['total_load'] = int(r.get('total_load', 0))
            r['avg_load'] = float(r.get('avg_load', 0.0))
            r['max_load'] = int(r.get('max_load', 0))
            r['avg_route_dist'] = float(r.get('avg_route_dist', 0.0))
            # keep paths for later
            r['out_json'] = r.get('out_json')
            r['out_png'] = r.get('out_png')
            rows.append(r)
    return rows


def group_by_set(rows):
    groups = defaultdict(list)
    for r in rows:
        inst = r['instance']
        if inst.startswith('C'):
            groups['C'].append(r)
        elif inst.startswith('R'):
            groups['R'].append(r)
        elif inst.startswith('RC'):
            groups['RC'].append(r)
        else:
            groups['other'].append(r)
    return groups


def compute_stats(rows):
    vals = np.array([r['best_cost'] for r in rows])
    return {'count': len(rows), 'mean_cost': float(vals.mean()), 'std_cost': float(vals.std()), 'min_cost': float(vals.min()), 'max_cost': float(vals.max())}


def novelty_score_for_instance(row):
    # improved heuristic novelty score using multiple binary features
    pj = row.get('out_json')
    params = {}
    try:
        if pj and os.path.exists(pj):
            with open(pj, 'r', encoding='utf-8') as f:
                data = json.load(f)
                params = data.get('params', {})
    except Exception:
        params = {}

    feats = {}
    # candidate_k relative
    try:
        candidate_k = int(float(params.get('candidate_k', 0)))
    except Exception:
        candidate_k = 0
    feats['candidate_k_relative'] = candidate_k / max(1, row['n_customers'])
    feats['candidate_k_large'] = int(feats['candidate_k_relative'] > NOVELTY_CONFIG['candidate_k_relative_thresh'])
    # q0_decay
    try:
        feats['q0_decay'] = 1 if float(params.get('q0_decay', 0.0)) > 0.0 else 0
    except Exception:
        feats['q0_decay'] = 0
    # tau0 present
    feats['tau0_present'] = 1 if 'tau0' in params and params.get('tau0') else 0
    feats['pheromone_init_tau0'] = 1 if params.get('pheromone_init') == 'tau0' else 0
    feats['fuzzy_present'] = 1 if params.get('fuzzy_present') else 0
    feats['two_opt'] = 1  # two-opt applied in current ACS implementation
    # ga tuned (presence of final tuned file)
    ga_final = os.path.join('results/aco_final', f"{row['instance']}_acs_result.json")
    feats['ga_tuned'] = 1 if os.path.exists(ga_final) else 0

    # compute weighted score
    w = NOVELTY_CONFIG['weights']
    score = 0.0
    for k, weight in w.items():
        score += feats.get(k, 0) * weight

    max_score = sum(w.values())
    normalized = score / max_score if max_score > 0 else 0.0
    return normalized, feats


def plot_group_costs(groups):
    labels = []
    means = []
    stds = []
    for k in ['C', 'R', 'RC']:
        if k in groups and groups[k]:
            s = compute_stats(groups[k])
            labels.append(k)
            means.append(s['mean_cost'])
            stds.append(s['std_cost'])
    x = np.arange(len(labels))
    plt.figure(figsize=(8,4))
    plt.bar(x, means, yerr=stds, capsize=6)
    plt.xticks(x, labels)
    plt.ylabel('Mean best cost')
    plt.title('Mean best cost by instance set (with std)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, 'mean_cost_by_set.png'))
    plt.close()


def plot_novelty(rows):
    inst = [r['instance'] for r in rows]
    scores = []
    feats_list = []
    for r in rows:
        s, feats = novelty_score_for_instance(r)
        scores.append(s)
        feats_list.append(feats)

    # write instance features table
    feat_keys = sorted({k for f in feats_list for k in f.keys()})
    with open(os.path.join(OUTDIR, 'instance_features.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['instance', 'novelty_score'] + feat_keys)
        for r, s, fdict in zip(rows, scores, feats_list):
            writer.writerow([r['instance'], s] + [fdict.get(k, '') for k in feat_keys])

    plt.figure(figsize=(10,4))
    idx = np.argsort(scores)[::-1]
    inst_sorted = [inst[i] for i in idx]
    scores_sorted = [scores[i] for i in idx]
    plt.bar(range(len(scores_sorted)), scores_sorted)
    plt.xticks(range(len(scores_sorted)), inst_sorted, rotation=90)
    plt.ylabel('Novelty score (0-1)')
    plt.title('Instance novelty score (heuristic)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, 'novelty_scores.png'))
    plt.close()

    return scores


def radar_plot_set(groups):
    # radar comparing mean metrics per set
    metrics = ['mean_cost', 'avg_route_dist', 'avg_load', 'n_routes', 'time_s']
    sets = [k for k in ['C', 'R', 'RC'] if k in groups and groups[k]]
    if not sets:
        return
    data = {}
    for s in sets:
        rows = groups[s]
        data[s] = {
            'mean_cost': compute_stats(rows)['mean_cost'],
            'avg_route_dist': float(np.mean([r.get('avg_route_dist', 0.0) for r in rows])),
            'avg_load': float(np.mean([r.get('avg_load', 0.0) for r in rows])),
            'n_routes': float(np.mean([r.get('n_routes', 0) for r in rows])),
            'time_s': float(np.mean([r.get('time_s', 0.0) for r in rows])),
        }

    # normalize each metric to [0,1]
    vals = {m: [data[s][m] for s in sets] for m in metrics}
    norm = {}
    for m in metrics:
        arr = np.array(vals[m])
        mi, ma = arr.min(), arr.max()
        if ma - mi == 0:
            norm[m] = [0.5 for _ in arr]
        else:
            norm[m] = ((arr - mi) / (ma - mi)).tolist()

    # build radar
    N = len(metrics)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    plt.figure(figsize=(6,6))
    ax = plt.subplot(111, polar=True)
    for i, s in enumerate(sets):
        vals_norm = [norm[m][i] for m in metrics]
        vals_plot = vals_norm + vals_norm[:1]
        ax.plot(angles, vals_plot, label=s)
        ax.fill(angles, vals_plot, alpha=0.15)

    ax.set_thetagrids(np.degrees(angles[:-1]), metrics)
    ax.set_title('Radar: normalized metrics by instance set')
    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, 'radar_by_set.png'))
    plt.close()


def violin_box_costs(groups):
    labels = []
    data = []
    for k in ['C', 'R', 'RC']:
        if k in groups and groups[k]:
            labels.append(k)
            data.append([r['best_cost'] for r in groups[k]])
    if not data:
        return
    plt.figure(figsize=(8,6))
    plt.violinplot(data)
    plt.xticks(range(1, len(labels)+1), labels)
    plt.title('Cost distribution by set (violin)')
    plt.ylabel('Best cost')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, 'violin_costs_by_set.png'))
    plt.close()


def scatter_cost_vs(rows, scores):
    # cost vs time and vs avg_route_dist colored by novelty
    novelty = np.array(scores)
    cost = np.array([r['best_cost'] for r in rows])
    time_s = np.array([r['time_s'] for r in rows])
    avg_rd = np.array([r.get('avg_route_dist', 0.0) for r in rows])

    plt.figure(figsize=(6,4))
    sc = plt.scatter(time_s, cost, c=novelty, cmap='viridis', s=40)
    plt.colorbar(sc, label='novelty')
    plt.xlabel('time_s')
    plt.ylabel('best_cost')
    plt.title('Cost vs Time (colored by novelty)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, 'scatter_cost_vs_time.png'))
    plt.close()

    plt.figure(figsize=(6,4))
    sc = plt.scatter(avg_rd, cost, c=novelty, cmap='plasma', s=40)
    plt.colorbar(sc, label='novelty')
    plt.xlabel('avg_route_dist')
    plt.ylabel('best_cost')
    plt.title('Cost vs Avg Route Dist (colored by novelty)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, 'scatter_cost_vs_avg_route_dist.png'))
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--novelty-config', default=None, help='Path to novelty_config.json to override defaults')
    parser.add_argument('--top-n', type=int, default=6, help='Number of top novel instances to include in PDF')
    args = parser.parse_args()

    # allow overriding the novelty config via CLI
    global NOVELTY_CONFIG
    if args.novelty_config:
        NOVELTY_CONFIG = load_novelty_config(args.novelty_config)

    rows = load_summary()
    groups = group_by_set(rows)
    # compute and save group stats
    stats = {k: compute_stats(v) for k, v in groups.items()}
    with open(os.path.join(OUTDIR, 'group_stats.json'), 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    plot_group_costs(groups)
    scores = plot_novelty(rows)
    # extra plots
    radar_plot_set(groups)
    violin_box_costs(groups)
    scatter_cost_vs(rows, scores)

    # optional baseline comparison
    baseline_summary = 'results/aco_baseline/summary.csv'
    stat_results = {}
    if os.path.exists(baseline_summary):
        try:
            base_rows = load_summary(baseline_summary)
            # match instances present in both
            base_map = {r['instance']: r for r in base_rows}
            paired = []
            for r in rows:
                inst = r['instance']
                if inst in base_map:
                    paired.append((base_map[inst]['best_cost'], r['best_cost']))
            if paired:
                diffs = [b - a for a, b in paired]
                # paired t-test (approx)
                n = len(diffs)
                md = mean(diffs)
                sd = stdev(diffs) if n > 1 else 0.0
                se = sd / math.sqrt(n) if n > 1 else float('inf')
                t_stat = md / se if se != 0 and se != float('inf') else 0.0
                # compute p using normal approximation if scipy unavailable
                try:
                    from scipy import stats
                    t_res = stats.ttest_rel([a for a,b in paired], [b for a,b in paired])
                    stat_results['paired_t'] = {'statistic': float(t_res.statistic), 'pvalue': float(t_res.pvalue)}
                    try:
                        w_res = stats.wilcoxon([a for a,b in paired], [b for a,b in paired])
                        stat_results['wilcoxon'] = {'statistic': float(w_res.statistic), 'pvalue': float(w_res.pvalue)}
                    except Exception:
                        stat_results['wilcoxon'] = {'error': 'wilcoxon failed'}
                except Exception:
                    # normal approx for paired t
                    # two-sided p from normal cdf
                    z = t_stat
                    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
                    stat_results['paired_t_approx'] = {'t': t_stat, 'p_approx': p, 'n': n}
        except Exception as e:
            stat_results['error'] = str(e)

    with open(os.path.join(OUTDIR, 'stat_tests.json'), 'w', encoding='utf-8') as f:
        json.dump(stat_results, f, indent=2)

    # assemble PDF report of main figures
    try:
        from matplotlib.backends.backend_pdf import PdfPages
        pdf_path = os.path.join(OUTDIR, 'report.pdf')
        figs = ['mean_cost_by_set.png', 'novelty_scores.png', 'radar_by_set.png', 'violin_costs_by_set.png', 'scatter_cost_vs_time.png', 'scatter_cost_vs_avg_route_dist.png']
        with PdfPages(pdf_path) as pdf:
            # first, add textual summary page
            summary_text = []
            summary_text.append('Analysis report')
            summary_text.append('')
            # basic group stats
            try:
                with open(os.path.join(OUTDIR, 'group_stats.json'), 'r', encoding='utf-8') as gf:
                    gstats = json.load(gf)
                    summary_text.append('Group stats:')
                    for k, v in gstats.items():
                        summary_text.append(f" {k}: count={v.get('count')} mean_cost={v.get('mean_cost'):.2f} std={v.get('std_cost'):.2f}")
            except Exception:
                pass
            # stat tests
            try:
                with open(os.path.join(OUTDIR, 'stat_tests.json'), 'r', encoding='utf-8') as sf:
                    st = json.load(sf)
                    summary_text.append('')
                    summary_text.append('Statistical tests (baseline vs current):')
                    summary_text.append(json.dumps(st, indent=2))
            except Exception:
                pass

            plt.figure(figsize=(8.5, 11))
            plt.axis('off')
            plt.text(0.01, 0.99, '\n'.join(summary_text), va='top', ha='left', wrap=True, fontsize=10)
            pdf.savefig()
            plt.close()

            # add main figures
            for fn in figs:
                p = os.path.join(OUTDIR, fn)
                if os.path.exists(p):
                    img = plt.imread(p)
                    plt.figure(figsize=(8,6))
                    plt.axis('off')
                    plt.imshow(img)
                    pdf.savefig()
                    plt.close()

            # include top-N novel instance thumbnails with captions
            try:
                # scores were returned earlier; recompute quickly
                scores = []
                for r in rows:
                    s, _ = novelty_score_for_instance(r)
                    scores.append(s)
                idx = np.argsort(scores)[::-1]
                topn = args.top_n
                top_idxs = idx[:topn]
                # layout thumbnails in a grid
                cols = 3
                rows_grid = (len(top_idxs) + cols - 1) // cols
                fig, axes = plt.subplots(rows_grid, cols, figsize=(8.5, 11))
                axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]
                for ax in axes:
                    ax.axis('off')
                for i, ti in enumerate(top_idxs):
                    r = rows[int(ti)]
                    imgp = r.get('out_png')
                    caption = f"{r['instance']}  cost={r['best_cost']:.2f} novelty={scores[int(ti)]:.3f}"
                    try:
                        if imgp and os.path.exists(imgp):
                            im = plt.imread(imgp)
                            axes[i].imshow(im)
                        axes[i].set_title(caption, fontsize=8)
                        axes[i].axis('off')
                    except Exception:
                        axes[i].text(0.5, 0.5, caption, ha='center', va='center')
                pdf.savefig()
                plt.close()
            except Exception:
                pass
    except Exception:
        # PDF generation optional; ignore failures
        pass

    print('Wrote analysis to', OUTDIR)


if __name__ == '__main__':
    main()
