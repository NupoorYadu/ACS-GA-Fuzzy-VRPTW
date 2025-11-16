"""Generate publication-quality figures (300 DPI) and a mean±std table for the paper.
Also compute effect sizes and multiple-comparison corrections and update
`results/analysis/stat_tests.json` with the additional fields.

Writes figures to `paper/figures/` and appends a small table into `paper/paper.md`.
"""
import os
import json
from glob import glob
import math
import csv
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


FIGDIR = os.path.join('paper', 'figures')
os.makedirs(FIGDIR, exist_ok=True)

CURR_CSV = os.path.join('results', 'aco_agg', 'summary.csv')
BASE_CSV = os.path.join('results', 'aco_baseline_agg', 'summary.csv')
STAT_JSON = os.path.join('results', 'analysis', 'stat_tests.json')
PAPER_MD = os.path.join('paper', 'paper.md')


def load_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def group_prefix(name):
    # prefix: C*, R*, RC* (choose RC for names starting with RC)
    if name.upper().startswith('RC'):
        return 'RC'
    return name[0].upper()


def holm_correction(pvals):
    # Holm step-down
    n = len(pvals)
    idx = np.argsort(pvals)
    sorted_p = np.array(pvals)[idx]
    adjusted = np.empty(n)
    for i, p in enumerate(sorted_p):
        adjusted[i] = min((n - i) * p, 1.0)
    # reorder to original
    inv = np.empty(n)
    inv[idx] = adjusted
    return list(inv)


def benjamini_hochberg(pvals):
    pvals = np.array(pvals)
    n = len(pvals)
    idx = np.argsort(pvals)
    sorted_p = pvals[idx]
    adjusted = np.empty(n)
    for i, p in enumerate(sorted_p, start=1):
        adjusted[i-1] = min(p * n / i, 1.0)
    # enforce monotonicity
    for i in range(n-2, -1, -1):
        adjusted[i] = min(adjusted[i], adjusted[i+1])
    inv = np.empty(n)
    inv[idx] = adjusted
    return list(inv)


def compute_effect_size_paired(a, b):
    # Cohen's d for paired samples: mean(diff)/sd(diff)
    diff = np.array(a) - np.array(b)
    md = diff.mean()
    sd = diff.std(ddof=1)
    if sd == 0:
        return float('nan')
    return md / sd


def main():
    curr = load_csv(CURR_CSV)
    base = load_csv(BASE_CSV)

    if curr.empty or base.empty:
        print('Missing aggregated CSVs; aborting.')
        return

    # align by instance
    left = curr.set_index('instance')
    right = base.set_index('instance')
    common = left.index.intersection(right.index)
    df = pd.DataFrame(index=common)
    df['curr_mean'] = left.loc[common, 'best_cost'].astype(float)
    df['base_mean'] = right.loc[common, 'best_cost'].astype(float)
    df = df.sort_index()

    # per-instance diff (baseline - current): positive means current (ACS) better
    df['diff'] = df['base_mean'] - df['curr_mean']

    # overall paired tests
    tstat, tp = stats.ttest_rel(df['base_mean'], df['curr_mean'], nan_policy='omit')
    try:
        wstat, wp = stats.wilcoxon(df['base_mean'] - df['curr_mean'])
    except Exception:
        wstat, wp = None, None

    cohen_d = compute_effect_size_paired(df['base_mean'], df['curr_mean'])

    # group-level tests (C, R, RC)
    df['group'] = [group_prefix(i) for i in df.index]
    group_results = {}
    pvals = []
    groups = []
    for g in sorted(df['group'].unique()):
        sub = df[df['group'] == g]
        if len(sub) < 2:
            pvals.append(1.0)
            groups.append(g)
            group_results[g] = {'t': None, 'p': None, 'n': len(sub)}
            continue
        t, p = stats.ttest_rel(sub['base_mean'], sub['curr_mean'])
        group_results[g] = {'t': float(t), 'p': float(p), 'n': int(len(sub))}
        pvals.append(p)
        groups.append(g)

    # multiple comparison corrections for group p-values
    holm = holm_correction(pvals)
    bh = benjamini_hochberg(pvals)
    for i, g in enumerate(groups):
        group_results[g]['p_holm'] = float(holm[i])
        group_results[g]['p_bh'] = float(bh[i])

    # update stat_tests.json with extra info
    stats_obj = {}
    stats_obj['paired_t'] = {'t': float(tstat), 'p': float(tp), 'n': int(len(df))}
    stats_obj['wilcoxon'] = {'statistic': float(wstat) if wstat is not None else None, 'p': float(wp) if wp is not None else None}
    stats_obj['cohen_d_paired'] = float(cohen_d) if not math.isnan(cohen_d) else None
    stats_obj['group_tests'] = group_results

    with open(STAT_JSON, 'w', encoding='utf-8') as f:
        json.dump(stats_obj, f, indent=2)
    print('Wrote updated stats to', STAT_JSON)

    # create simple summary table mean±std by group for both methods
    rows = []
    for g in sorted(df['group'].unique()):
        sub = df[df['group'] == g]
        rows.append({
            'group': g,
            'n': len(sub),
            'acs_mean': float(sub['curr_mean'].mean()),
            'acs_std': float(sub['curr_mean'].std(ddof=1)),
            'ort_mean': float(sub['base_mean'].mean()),
            'ort_std': float(sub['base_mean'].std(ddof=1)),
        })

    overall = {
        'group': 'ALL',
        'n': len(df),
        'acs_mean': float(df['curr_mean'].mean()),
        'acs_std': float(df['curr_mean'].std(ddof=1)),
        'ort_mean': float(df['base_mean'].mean()),
        'ort_std': float(df['base_mean'].std(ddof=1)),
    }
    rows.append(overall)

    # write a markdown table to paper/paper.md (append)
    md_lines = []
    md_lines.append('\n## Numerical results (mean ± std)\n')
    md_lines.append('Summary of average route costs by problem class (ACS vs OR-Tools).')
    md_lines.append('\n| Class | n | ACS mean ± std | OR-Tools mean ± std |')
    md_lines.append('|---:|---:|:---:|:---:|')
    for r in rows:
        md_lines.append(f"| {r['group']} | {r['n']} | {r['acs_mean']:.2f} ± {r['acs_std']:.2f} | {r['ort_mean']:.2f} ± {r['ort_std']:.2f} |")

    md_lines.append('\nFigure: mean costs by problem class and violin of instance-level differences (baseline - ACS).')

    # save table and figures
    with open(PAPER_MD, 'a', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    print('Appended mean±std table to', PAPER_MD)

    # Figure 1: bar chart by group
    groups = [r['group'] for r in rows]
    acs_means = [r['acs_mean'] for r in rows]
    acs_stds = [r['acs_std'] for r in rows]
    ort_means = [r['ort_mean'] for r in rows]
    ort_stds = [r['ort_std'] for r in rows]

    x = np.arange(len(groups))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    ax.bar(x - width/2, acs_means, width, yerr=acs_stds, label='ACS', color='#1f77b4', capsize=4)
    ax.bar(x + width/2, ort_means, width, yerr=ort_stds, label='OR-Tools', color='#ff7f0e', capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylabel('Mean best cost')
    ax.set_title('Mean best cost by problem class (300 DPI)')
    ax.legend()
    fig_path = os.path.join(FIGDIR, 'mean_cost_by_class.png')
    fig.tight_layout()
    fig.savefig(fig_path, dpi=300)
    print('Wrote figure to', fig_path)

    # Figure 2: violin of per-instance diffs
    fig2, ax2 = plt.subplots(figsize=(8, 4.5), dpi=300)
    diffs = df['diff'].values
    ax2.violinplot(diffs, showmeans=True)
    ax2.axhline(0, color='k', linestyle='--', linewidth=0.8)
    ax2.set_title('Instance-level cost differences (OR-Tools - ACS)')
    ax2.set_ylabel('Cost difference')
    ax2.set_xticks([1])
    ax2.set_xticklabels(['All instances'])
    fig2_path = os.path.join(FIGDIR, 'diff_violin_all.png')
    fig2.tight_layout()
    fig2.savefig(fig2_path, dpi=300)
    print('Wrote figure to', fig2_path)


if __name__ == '__main__':
    main()
