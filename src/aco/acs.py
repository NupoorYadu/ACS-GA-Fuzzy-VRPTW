import math
import random
from typing import List, Dict, Tuple


class ACS:
    """Simple Ant Colony System (ACS) for VRPTW (baseline, simplified).

    Inputs: parsed Solomon JSON-like dict or path (we expect dict already parsed by loader).
    This implementation focuses on correctness and a runnable baseline rather than research-grade tuning.
    """

    def __init__(self, instance: Dict, vehicle_capacity: int = 200, alpha: float = 1.0, beta: float = 2.0, rho: float = 0.1, phi: float = 0.1, q: float = 1.0, q0: float = 0.9, candidate_k: int = 15, q0_decay: float = 0.0, q0_min: float = 0.1, use_two_opt: bool = True):
        # instance: dict with keys 'depot' and 'customers'
        self.instance = instance
        self.depot = instance.get('depot')
        self.customers = instance.get('customers', [])
        # build node list: index 0 = depot, 1..n = customers
        self.nodes = [self.depot] + self.customers
        self.n = len(self.nodes)
        self.vehicle_capacity = vehicle_capacity
        self.alpha = alpha
        self.beta = beta
        self.rho = rho  # evaporation
        self.phi = phi  # local pheromone update param
        self.q = q  # global pheromone factor
        # q0 parameters: initial exploitation probability, decay per iteration (multiplicative), and minimum allowed
        self.q0 = float(q0)
        self.q0_init = float(q0)
        self.q0_decay = float(q0_decay)
        self.q0_min = float(q0_min)
        # allow disabling 2-opt for ablation studies
        self.use_two_opt = bool(use_two_opt)
        # candidate_k may be an int (uniform) or a list specifying per-node sizes
        self.candidate_k = candidate_k
        # distance matrix
        self.dist = [[0.0] * self.n for _ in range(self.n)]
        self._build_distance()
        # pheromone initialization: compute a nearest-neighbour tour length and set tau0 = 1/(n * L_nn)
        self.tau0 = 1.0
        try:
            Lnn = self._nearest_neighbor_tour_cost()
            if Lnn > 0:
                self.tau0 = 1.0 / (self.n * Lnn)
        except Exception:
            # fallback
            self.tau0 = 1.0
        # pheromone matrix initialized to tau0
        self.tau = [[self.tau0 for _ in range(self.n)] for _ in range(self.n)]
        # heuristic matrix
        self.eta = [[0.0] * self.n for _ in range(self.n)]
        for i in range(self.n):
            for j in range(self.n):
                if i != j:
                    self.eta[i][j] = 1.0 / (self.dist[i][j] + 1e-6)
                else:
                    self.eta[i][j] = 0.0
        # candidate lists (nearest neighbors for each node)
        self.candidates = [None] * self.n
        # Build candidate lists (cached). Support per-node candidate sizes if candidate_k is a list.
        # Default candidate_k if not positive
        if not isinstance(self.candidate_k, (list, tuple)) and (not self.candidate_k or int(self.candidate_k) <= 0):
            self.candidate_k = min(15, max(1, self.n - 1))

        for i in range(self.n):
            idxs = list(range(self.n))
            # remove self index
            idxs.remove(i)
            # sort by distance
            idxs.sort(key=lambda j: self.dist[i][j])
            if isinstance(self.candidate_k, (list, tuple)):
                k = int(self.candidate_k[i]) if i < len(self.candidate_k) else int(self.candidate_k[-1])
            else:
                k = int(self.candidate_k)
            k = max(0, min(k, len(idxs)))
            # For customer nodes, prefer neighbor customers (exclude depot index 0)
            if i != 0:
                filtered = [j for j in idxs if j != 0]
                self.candidates[i] = filtered[:k]
            else:
                # depot can have customers as candidates
                self.candidates[i] = idxs[:k]

    def _build_distance(self):
        for i in range(self.n):
            ni = self.nodes[i]
            xi = float(ni.get('x', 0))
            yi = float(ni.get('y', 0))
            for j in range(self.n):
                nj = self.nodes[j]
                xj = float(nj.get('x', 0))
                yj = float(nj.get('y', 0))
                self.dist[i][j] = math.hypot(xi - xj, yi - yj)

    def _nearest_neighbor_tour_cost(self) -> float:
        # simple nearest-neighbour starting from depot (0)
        unvisited = set(range(1, self.n))
        prev = 0
        total = 0.0
        while unvisited:
            # find nearest unvisited
            next_node = min(unvisited, key=lambda j: self.dist[prev][j])
            total += self.dist[prev][next_node]
            prev = next_node
            unvisited.remove(next_node)
        # return to depot
        total += self.dist[prev][0]
        return total

    def run(self, num_ants: int = 10, iterations: int = 50, seed: int = 0) -> Dict:
        random.seed(seed)
        best_solution = None
        best_cost = float('inf')

        # reset q0 to initial value at start of run
        self.q0 = float(self.q0_init)

        for it in range(iterations):
            ants_solutions = []
            for a in range(num_ants):
                sol = self._construct_solution()
                cost = self._solution_cost(sol)
                ants_solutions.append((sol, cost))
                if cost < best_cost:
                    best_cost = cost
                    best_solution = sol
            # global pheromone update using best of this iteration (or global best)
            self._global_update(best_solution, best_cost)
            # q0 annealing: multiplicative decay per iteration (if q0_decay > 0)
            if self.q0_decay and self.q0 > self.q0_min:
                # apply multiplicative decay factor (1 - q0_decay)
                self.q0 = max(self.q0_min, self.q0 * (1.0 - float(self.q0_decay)))

        return {'best_solution': best_solution, 'best_cost': best_cost}

    def _construct_solution(self) -> List[List[int]]:
        # returns list of routes, each route is list of node indices (excluding depot at ends)
        unvisited = set(range(1, self.n))
        routes: List[List[int]] = []

        while unvisited:
            route = []
            load = 0
            current = 0  # depot index
            current_time = 0.0
            while True:
                candidates = []
                for j in list(unvisited):
                    cust = self.nodes[j]
                    demand = int(cust.get('demand', 0))
                    # capacity feasibility
                    if load + demand > self.vehicle_capacity:
                        continue
                    # time feasibility: compute arrival time
                    travel = self.dist[current][j]
                    ready = float(cust.get('ready_time', 0.0))
                    due = float(cust.get('due_time', 1e9))
                    arrival = current_time + travel
                    start_service = max(arrival, ready)
                    if start_service > due:
                        continue
                    candidates.append(j)

                if not candidates:
                    break

                # selection by ACS rule: probabilistic using pheromone and heuristic
                # restrict candidates by candidate list for speed (if available)
                cand_list = [c for c in self.candidates[current] if c in candidates]
                if cand_list:
                    use_list = cand_list
                else:
                    use_list = candidates

                # ACS exploitation vs exploration
                if random.random() < self.q0:
                    # exploitation: choose argmax tau^alpha * eta^beta
                    best_j = None
                    best_val = -1.0
                    for j in use_list:
                        val = (self.tau[current][j] ** self.alpha) * (self.eta[current][j] ** self.beta)
                        if val > best_val:
                            best_val = val
                            best_j = j
                    chosen = best_j if best_j is not None else random.choice(use_list)
                else:
                    # exploration: roulette wheel on use_list
                    probs = []
                    for j in use_list:
                        tau = self.tau[current][j] ** self.alpha
                        eta = self.eta[current][j] ** self.beta
                        probs.append(tau * eta)
                    total = sum(probs)
                    if total <= 0:
                        chosen = random.choice(use_list)
                    else:
                        r = random.random() * total
                        cum = 0.0
                        chosen = use_list[-1]
                        for idx, val in enumerate(probs):
                            cum += val
                            if r <= cum:
                                chosen = use_list[idx]
                                break

                # move to chosen
                route.append(chosen)
                # local pheromone update on edge (current, chosen)
                self._local_update(current, chosen)

                # update state
                cust = self.nodes[chosen]
                travel = self.dist[current][chosen]
                ready = float(cust.get('ready_time', 0.0))
                arrival = current_time + travel
                current_time = max(arrival, ready) + float(cust.get('service_time', 0.0))
                load += int(cust.get('demand', 0))
                unvisited.remove(chosen)
                current = chosen

            # route finished, return to depot implicitly
            # optionally apply a simple 2-opt local search to improve route order
            if route:
                if self.use_two_opt:
                    routes.append(self._two_opt_route(route))
                else:
                    routes.append(route)
            else:
                routes.append(route)
        return routes

    def _two_opt_route(self, route: List[int]) -> List[int]:
        # simple 2-opt improving swaps until no improvement or max iterations
        best = route[:]
        def route_cost(r):
            prev = 0
            c = 0.0
            for node in r:
                c += self.dist[prev][node]
                prev = node
            c += self.dist[prev][0]
            return c

        best_cost = route_cost(best)
        improved = True
        max_iters = max(10, len(route) * 2)
        it = 0
        while improved and it < max_iters:
            improved = False
            it += 1
            n = len(best)
            for i in range(0, n - 1):
                for j in range(i + 1, n):
                    candidate = best[:i] + best[i:j+1][::-1] + best[j+1:]
                    cand_cost = route_cost(candidate)
                    if cand_cost + 1e-9 < best_cost:
                        best = candidate
                        best_cost = cand_cost
                        improved = True
                        break
                if improved:
                    break
        return best

    def _local_update(self, i: int, j: int):
        # tau_ij = (1-phi)*tau_ij + phi * tau0
        self.tau[i][j] = (1 - self.phi) * self.tau[i][j] + self.phi * self.tau0
        self.tau[j][i] = self.tau[i][j]

    def _global_update(self, best_solution: List[List[int]], best_cost: float):
        # evaporate
        for i in range(self.n):
            for j in range(self.n):
                self.tau[i][j] = (1 - self.rho) * self.tau[i][j]
        # reinforce edges on best_solution
        if not best_solution:
            return
        deposit = self.q / (best_cost + 1e-6)
        for route in best_solution:
            prev = 0
            for node in route:
                self.tau[prev][node] += deposit
                self.tau[node][prev] = self.tau[prev][node]
                prev = node
            # return edge to depot
            self.tau[prev][0] += deposit
            self.tau[0][prev] = self.tau[prev][0]

    def _solution_cost(self, solution: List[List[int]]) -> float:
        total = 0.0
        for route in solution:
            prev = 0
            for node in route:
                total += self.dist[prev][node]
                prev = node
            total += self.dist[prev][0]
        return total


if __name__ == '__main__':
    print('ACS module - import and use ACS class from scripts')
