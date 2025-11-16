import os
from src.utils.plotting import plot_routes


def make_tiny_instance():
    depot = {'id': 0, 'x': 0.0, 'y': 0.0, 'demand': 0, 'ready_time': 0, 'due_time': 9999, 'service_time': 0}
    customers = []
    for i in range(1, 6):
        customers.append({'id': i, 'x': i * 1.0, 'y': i * 0.5, 'demand': 1, 'ready_time': 0, 'due_time': 9999, 'service_time': 0})
    return {'depot': depot, 'customers': customers}


def test_plot_routes_creates_file(tmp_path):
    inst = make_tiny_instance()
    # simple solution: one route visiting all
    sol = [list(range(1, 6))]
    out = tmp_path / 'test_routes.png'
    plot_routes(inst, sol, str(out))
    assert out.exists()
