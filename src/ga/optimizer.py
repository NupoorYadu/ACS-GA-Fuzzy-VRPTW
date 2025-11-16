import random
import time
from typing import Tuple

from deap import base, creator, tools, algorithms

from src.aco.acs import ACS


def evaluate_params(individual, instance, ants=8, iters=10, capacity=200, seed=1):
    """Evaluate an individual [alpha, beta, rho, q0] by running ACS with small budget.
    Returns a tuple with single fitness (minimize cost).
    """
    alpha, beta, rho, q0 = individual
    # clamp parameters to safe ranges to avoid invalid behavior (e.g., negative pheromone updates)
    alpha = float(max(0.01, min(alpha, 10.0)))
    beta = float(max(0.01, min(beta, 10.0)))
    rho = float(max(0.001, min(rho, 0.999)))
    q0 = float(max(0.0, min(q0, 1.0)))
    acs = ACS(instance, vehicle_capacity=capacity, alpha=alpha, beta=beta, rho=rho, q0=q0)
    start = time.time()
    res = acs.run(num_ants=ants, iterations=iters, seed=seed)
    elapsed = time.time() - start
    cost = res['best_cost']
    # return tuple (fitness,)
    return (cost,)


def run_ga(instance, pop_size=20, gens=10, cxpb=0.5, mutpb=0.2, ants=8, iters=10, capacity=200, seed=1):
    random.seed(seed)
    # minimize cost
    creator.create('FitnessMin', base.Fitness, weights=(-1.0,))
    creator.create('Individual', list, fitness=creator.FitnessMin)

    toolbox = base.Toolbox()
    # alpha in [0.1, 5.0], beta in [0.1, 5.0], rho in [0.01, 1.0], q0 in [0.0, 1.0]
    toolbox.register('alpha', random.uniform, 0.1, 5.0)
    toolbox.register('beta', random.uniform, 0.1, 5.0)
    toolbox.register('rho', random.uniform, 0.01, 1.0)
    toolbox.register('q0', random.uniform, 0.0, 1.0)
    toolbox.register('individual', tools.initCycle, creator.Individual, (toolbox.alpha, toolbox.beta, toolbox.rho, toolbox.q0), n=1)
    toolbox.register('population', tools.initRepeat, list, toolbox.individual)

    def eval_wrapper(ind):
        return evaluate_params(ind, instance, ants=ants, iters=iters, capacity=capacity, seed=seed)

    toolbox.register('evaluate', eval_wrapper)
    toolbox.register('mate', tools.cxBlend, alpha=0.5)
    toolbox.register('mutate', tools.mutGaussian, mu=0, sigma=0.2, indpb=0.2)
    toolbox.register('select', tools.selTournament, tournsize=3)

    pop = toolbox.population(n=pop_size)
    hof = tools.HallOfFame(3)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register('min', min)
    stats.register('avg', lambda x: sum(v[0] for v in x) / len(x))

    pop, log = algorithms.eaSimple(pop, toolbox, cxpb=cxpb, mutpb=mutpb, ngen=gens, stats=stats, halloffame=hof, verbose=True)

    best = hof[0]
    return {'best_individual': best, 'best_fitness': best.fitness.values[0], 'log': log, 'halloffame': hof}
