import argparse
import json
import os
import random
import time
import sys
# ensure project root
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from src.aco.acs import ACS


def random_individual():
    return [random.uniform(0.1, 5.0), random.uniform(0.1, 5.0), random.uniform(0.01, 0.9), random.uniform(0.0, 1.0)]


def clamp(x, a, b):
    return max(a, min(b, x))


def mate_blend(a, b, alpha=0.5):
    child1 = []
    child2 = []
    for x, y in zip(a, b):
        d = abs(x - y)
        low = min(x, y) - alpha * d
        high = max(x, y) + alpha * d
        child1.append(random.uniform(low, high))
        child2.append(random.uniform(low, high))
    return [clamp(child1[0], 0.1, 5.0), clamp(child1[1], 0.1, 5.0), clamp(child1[2], 0.01, 0.9), clamp(child1[3], 0.0, 1.0)], [clamp(child2[0], 0.1, 5.0), clamp(child2[1], 0.1, 5.0), clamp(child2[2], 0.01, 0.9), clamp(child2[3], 0.0, 1.0)]


def mutate_gaussian(ind, mu=0.0, sigma=0.3, indpb=0.2):
    out = ind[:]
    for i in range(len(out)):
        if random.random() < indpb:
            out[i] += random.gauss(mu, sigma)
    out[0] = clamp(out[0], 0.1, 5.0)
    out[1] = clamp(out[1], 0.1, 5.0)
    out[2] = clamp(out[2], 0.01, 0.9)
    out[3] = clamp(out[3], 0.0, 1.0)
    return out


def evaluate(ind, instance, ants, iters, capacity, seed=1):
    acs = ACS(instance, vehicle_capacity=capacity, alpha=ind[0], beta=ind[1], rho=ind[2], q0=ind[3])
    start = time.time()
    res = acs.run(num_ants=ants, iterations=iters, seed=seed)
    elapsed = time.time() - start
    return res['best_cost'], elapsed


def run_ga_simple(instance, pop_size=12, gens=8, cxpb=0.6, mutpb=0.3, ants=6, iters=8, capacity=200, seed=1):
    random.seed(seed)
    pop = [random_individual() for _ in range(pop_size)]
    fitness = [None] * pop_size

    # evaluate initial
    for i, ind in enumerate(pop):
        f, t = evaluate(ind, instance, ants, iters, capacity, seed=seed)
        fitness[i] = f
        print(f'Init ind {i}: {ind} -> {f:.2f} (t={t:.2f}s)')

    hof = []

    for g in range(gens):
        # selection: tournament size 3
        newpop = []
        while len(newpop) < pop_size:
            # tournament select parents
            def tour_select():
                a, b, c = random.sample(range(pop_size), 3)
                best = a if fitness[a] < fitness[b] and fitness[a] < fitness[c] else (b if fitness[b] < fitness[c] else c)
                return pop[best]
            p1 = tour_select()
            p2 = tour_select()
            if random.random() < cxpb:
                c1, c2 = mate_blend(p1, p2)
            else:
                c1, c2 = p1[:], p2[:]
            if random.random() < mutpb:
                c1 = mutate_gaussian(c1)
            if random.random() < mutpb:
                c2 = mutate_gaussian(c2)
            newpop.append(c1)
            if len(newpop) < pop_size:
                newpop.append(c2)
        # evaluate newpop
        pop = newpop
        for i, ind in enumerate(pop):
            f, t = evaluate(ind, instance, ants, iters, capacity, seed=seed+g+i)
            fitness[i] = f
        # record hof
        best_idx = min(range(pop_size), key=lambda i: fitness[i])
        best_ind = pop[best_idx]
        best_fit = fitness[best_idx]
        hof.append((best_ind, best_fit))
        print(f'Gen {g+1}: best {best_ind} -> {best_fit:.2f}')

    best_overall = min(hof, key=lambda x: x[1])
    return {'best_individual': best_overall[0], 'best_fitness': best_overall[1], 'hof': hof}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', required=True)
    parser.add_argument('--pop', type=int, default=12)
    parser.add_argument('--gens', type=int, default=8)
    parser.add_argument('--ants', type=int, default=6)
    parser.add_argument('--iters', type=int, default=8)
    parser.add_argument('--capacity', type=int, default=200)
    args = parser.parse_args()

    with open(args.instance, 'r', encoding='utf-8') as f:
        inst = json.load(f)

    res = run_ga_simple(inst, pop_size=args.pop, gens=args.gens, ants=args.ants, iters=args.iters, capacity=args.capacity)
    print('DONE. Best:', res['best_individual'], 'fitness:', res['best_fitness'])


if __name__ == '__main__':
    main()
