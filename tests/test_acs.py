import os
from src.aco.acs import ACS


def make_tiny_instance():
    depot = {'id': 0, 'x': 0.0, 'y': 0.0, 'demand': 0, 'ready_time': 0, 'due_time': 9999, 'service_time': 0}
    customers = []
    # create 5 customers in a small circle
    for i in range(1, 6):
        customers.append({'id': i, 'x': i * 1.0, 'y': i * 0.5, 'demand': 1, 'ready_time': 0, 'due_time': 9999, 'service_time': 0})
    return {'depot': depot, 'customers': customers}


def test_acs_basic_solution():
    inst = make_tiny_instance()
    acs = ACS(inst, vehicle_capacity=10, alpha=1.0, beta=2.0, rho=0.1, q0=0.8, candidate_k=3)
    res = acs.run(num_ants=4, iterations=4, seed=42)
    assert 'best_cost' in res
    assert res['best_cost'] > 0
    # ensure solution covers all customers
    sol = res['best_solution']
    visited = set()
    for route in sol:
        for n in route:
            visited.add(n)
    # customer indices are 1..n
    assert visited == set(range(1, 6))
