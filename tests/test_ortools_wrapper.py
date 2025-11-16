import json
import pytest

ortools = pytest.importorskip('ortools')

from src.baselines.ortools_wrapper import run_ortools_cvrp


def make_tiny_instance():
    # depot + 3 customers
    inst = {
        'depot': {'x': 0, 'y': 0},
        'customers': [
            {'x': 1, 'y': 0, 'demand': 1},
            {'x': 0, 'y': 1, 'demand': 1},
            {'x': -1, 'y': 0, 'demand': 1}
        ]
    }
    return inst


def test_run_ortools_cvrp_basic():
    inst = make_tiny_instance()
    res = run_ortools_cvrp(inst, capacity=10, time_limit_s=5, num_vehicles=3)
    assert isinstance(res, dict)
    assert 'routes' in res and 'total_distance' in res
    assert isinstance(res['routes'], list)
    assert res['total_distance'] >= 0
