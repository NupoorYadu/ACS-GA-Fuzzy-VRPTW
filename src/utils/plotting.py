import matplotlib.pyplot as plt
from typing import List, Dict


def plot_routes(instance: Dict, solution: List[List[int]], out_path: str):
    """Plot the depot and customer coordinates and draw routes.
    solution: list of routes where node indices correspond to instance nodes (0=depot, 1..n customers)
    """
    depot = instance.get('depot')
    customers = instance.get('customers', [])
    xs = [depot.get('x')] + [c.get('x') for c in customers]
    ys = [depot.get('y')] + [c.get('y') for c in customers]

    plt.figure(figsize=(8, 8))
    # plot nodes
    plt.scatter(xs[1:], ys[1:], c='blue', s=20, label='customers')
    plt.scatter(xs[0], ys[0], c='red', s=50, label='depot')

    # annotate a few points for readability (optional)
    # draw routes
    for ridx, route in enumerate(solution):
        if not route:
            continue
        rx = [xs[0]]
        ry = [ys[0]]
        for node in route:
            rx.append(xs[node])
            ry.append(ys[node])
        rx.append(xs[0])
        ry.append(ys[0])
        plt.plot(rx, ry, '-', linewidth=1, label=f'R{ridx+1}' if ridx < 8 else None)

    plt.title('ACS routes')
    plt.legend(loc='upper right', fontsize='small')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
