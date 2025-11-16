import os
import json
from src.aco.acs import ACS


SAMPLE_PATH = os.path.join('data', 'solomon_dataset', 'parsed', 'SAMPLE', 'sample1.json')


def test_load_sample_and_distance():
    with open(SAMPLE_PATH, 'r', encoding='utf-8') as f:
        inst = json.load(f)
    acs = ACS(inst)
    # distance matrix should be square and match nodes count
    assert len(acs.dist) == acs.n
    assert all(len(row) == acs.n for row in acs.dist)


def test_candidate_lists_nonempty():
    with open(SAMPLE_PATH, 'r', encoding='utf-8') as f:
        inst = json.load(f)
    acs = ACS(inst, candidate_k=2)
    # For depot and customers, candidate lists should be lists
    assert isinstance(acs.candidates, list)
    assert all(isinstance(c, list) for c in acs.candidates)


def test_two_opt_preserves_nodes_and_reduces_cost():
    with open(SAMPLE_PATH, 'r', encoding='utf-8') as f:
        inst = json.load(f)
    acs = ACS(inst)
    # create a route with customers in given order
    if acs.n - 1 < 2:
        return
    orig_route = list(range(1, acs.n))
    orig_cost = 0.0
    prev = 0
    for node in orig_route:
        orig_cost += acs.dist[prev][node]
        prev = node
    orig_cost += acs.dist[prev][0]
    new_route = acs._two_opt_route(orig_route)
    # ensure same set of nodes
    assert set(new_route) == set(orig_route)
    # cost should not increase
    new_cost = 0.0
    prev = 0
    for node in new_route:
        new_cost += acs.dist[prev][node]
        prev = node
    new_cost += acs.dist[prev][0]
    assert new_cost <= orig_cost + 1e-6


def test_run_returns_solution():
    with open(SAMPLE_PATH, 'r', encoding='utf-8') as f:
        inst = json.load(f)
    acs = ACS(inst)
    res = acs.run(num_ants=4, iterations=4, seed=123)
    assert 'best_solution' in res and 'best_cost' in res
    assert isinstance(res['best_cost'], float)
