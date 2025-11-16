import json
import os
from src.ga.optimizer import evaluate_params

SAMPLE_PATH = os.path.join('data', 'solomon_dataset', 'parsed', 'SAMPLE', 'sample1.json')


def test_evaluate_params_clamps_and_runs():
    with open(SAMPLE_PATH, 'r', encoding='utf-8') as f:
        inst = json.load(f)
    # provide extreme values that must be clamped
    indiv = [1000.0, -50.0, -1.0, 2.0]
    res = evaluate_params(indiv, inst, ants=4, iters=2, capacity=200, seed=42)
    assert isinstance(res, tuple)
    assert len(res) == 1
    cost = res[0]
    assert isinstance(cost, float)
    assert cost > 0
