"""Wrapper for OR-Tools VRP as a baseline. This is optional and will only run if ortools is installed.
The wrapper solves a basic CVRP (capacity-constrained) ignoring time windows for simplicity.
"""

from typing import Dict, List, Optional


def run_ortools_cvrp(instance: Dict, capacity: int = 200, time_limit_s: int = 10, num_vehicles: Optional[int] = None):
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except Exception as e:
        raise ImportError('ortools is not installed: install ortools to use this baseline') from e

    depot = instance.get('depot')
    customers = instance.get('customers', [])
    nodes = [depot] + customers
    n = len(nodes)

    # build distance matrix
    import math
    dist = [[0] * n for _ in range(n)]
    for i in range(n):
        xi = float(nodes[i].get('x', 0))
        yi = float(nodes[i].get('y', 0))
        for j in range(n):
            xj = float(nodes[j].get('x', 0))
            yj = float(nodes[j].get('y', 0))
            # use rounded Euclidean distance as integer cost
            dist[i][j] = int(math.hypot(xi - xj, yi - yj) + 0.5)

    demands = [0] + [int(c.get('demand', 0)) for c in customers]

    # number of vehicles: default to number of customers (conservative upper bound)
    num_customers = max(0, n - 1)
    if num_vehicles is None:
        num_vehicles = num_customers if num_customers > 0 else 1

    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(n, int(num_vehicles), 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return demands[from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    vehicle_capacities = [int(capacity)] * int(num_vehicles)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, vehicle_capacities, True, 'Capacity')

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    # set a solver time limit in a robust way depending on ortools version
    try:
        # newer ortools exposes a time_limit with a seconds attribute
        search_parameters.time_limit.seconds = int(time_limit_s)
    except Exception:
        try:
            # fallback: try the protobuf helper if available
            search_parameters.time_limit.FromSeconds(int(time_limit_s))
        except Exception:
            # last resort: set a max_time_seconds attribute if present
            if hasattr(search_parameters, 'max_time_seconds'):
                setattr(search_parameters, 'max_time_seconds', float(time_limit_s))

    solution = routing.SolveWithParameters(search_parameters)
    if solution:
        # extract routes
        routes = []
        total_dist = 0
        for vehicle_id in range(int(num_vehicles)):
            index = routing.Start(vehicle_id)
            route = []
            route_dist = 0
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != 0:
                    route.append(node)
                next_index = solution.Value(routing.NextVar(index))
                route_dist += routing.GetArcCostForVehicle(index, next_index, vehicle_id)
                index = next_index
            if route:
                routes.append(route)
                total_dist += route_dist
        return {'routes': routes, 'total_distance': total_dist}
    else:
        return {'routes': [], 'total_distance': float('inf')}
"""Wrapper for OR-Tools VRP as a baseline. This is optional and will only run if ortools is installed.
The wrapper solves a basic CVRP (capacity-constrained) ignoring time windows for simplicity.
"""

from typing import Dict, List, Optional


def run_ortools_cvrp(instance: Dict, capacity: int = 200, time_limit_s: int = 10, num_vehicles: Optional[int] = None):
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except Exception as e:
        raise ImportError('ortools is not installed: install ortools to use this baseline') from e

    depot = instance.get('depot')
    customers = instance.get('customers', [])
    nodes = [depot] + customers
    n = len(nodes)

    # build distance matrix
    import math
    dist = [[0] * n for _ in range(n)]
    for i in range(n):
        xi = float(nodes[i].get('x', 0))
        yi = float(nodes[i].get('y', 0))
        for j in range(n):
            xj = float(nodes[j].get('x', 0))
            yj = float(nodes[j].get('y', 0))
            # use rounded Euclidean distance as integer cost
            dist[i][j] = int(math.hypot(xi - xj, yi - yj) + 0.5)

    demands = [0] + [int(c.get('demand', 0)) for c in customers]

    # number of vehicles: default to number of customers (conservative upper bound)
    num_customers = max(0, n - 1)
    if num_vehicles is None:
        num_vehicles = num_customers if num_customers > 0 else 1

    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(n, int(num_vehicles), 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return demands[from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    vehicle_capacities = [int(capacity)] * int(num_vehicles)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, vehicle_capacities, True, 'Capacity')

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    # set a solver time limit in a robust way depending on ortools version
    try:
        # newer ortools exposes a time_limit with a seconds attribute
        search_parameters.time_limit.seconds = int(time_limit_s)
    except Exception:
        try:
            # fallback: try the protobuf helper if available
            search_parameters.time_limit.FromSeconds(int(time_limit_s))
        except Exception:
            # last resort: set a max_time_seconds attribute if present
            if hasattr(search_parameters, 'max_time_seconds'):
                setattr(search_parameters, 'max_time_seconds', float(time_limit_s))

    solution = routing.SolveWithParameters(search_parameters)
    if solution:
        # extract routes
        routes = []
        total_dist = 0
        for vehicle_id in range(int(num_vehicles)):
            index = routing.Start(vehicle_id)
            route = []
            route_dist = 0
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != 0:
                    route.append(node)
                next_index = solution.Value(routing.NextVar(index))
                route_dist += routing.GetArcCostForVehicle(index, next_index, vehicle_id)
                index = next_index
            if route:
                routes.append(route)
                total_dist += route_dist
        return {'routes': routes, 'total_distance': total_dist}
    else:
        return {'routes': [], 'total_distance': float('inf')}
