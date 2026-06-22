from itertools import product
from typing import List, Tuple


def build_nsga_combinations(
    max_combinations: int,
) -> List[Tuple[int, float, float, int, int]]:
    population_sizes = [2, 4, 8, 15, 30][: max(max_combinations, 1)]
    mutate_probs = [0.8]
    crossover_probs = [1.0]
    mutate_etas = [15]
    crossover_etas = [5]
    return list(
        product(
            population_sizes, mutate_probs, crossover_probs, mutate_etas, crossover_etas
        )
    )[:max_combinations]


def format_nsga_combination(
    combination: Tuple[int, float, float, int, int],
    index: int,
    total: int,
) -> str:
    population_size, mutate_prob, crossover_prob, mutate_eta, crossover_eta = (
        combination
    )
    return (
        f"combination {index}/{total}: population_size={population_size}, "
        f"mutate_prob={mutate_prob}, crossover_prob={crossover_prob}, "
        f"mutate_eta={mutate_eta}, crossover_eta={crossover_eta}"
    )
