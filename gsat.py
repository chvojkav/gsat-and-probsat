from pathlib import Path
import random
import sys
from argparse import ArgumentParser

from pysat.formula import CNF
from pysat.solvers import Solver


from sat import Configuration, FormulaHelper, get_unsatisfied_clauses


def _get_best_flips(formula: CNF,
                    config: Configuration,
                    helper: FormulaHelper) -> list[int]:
    best_change = len(formula.clauses)  # worst case is that we newly usatisfy all clauses.
    best_flips = []
    for i in range(1, formula.nv + 1):
        orig_unsat_clauses_of_var = len(get_unsatisfied_clauses(helper[i], config))
        config.flip_variable(i)
        new_unsat_clauses_of_var = len(get_unsatisfied_clauses(helper[i], config))
        config.flip_variable(i)
        change = new_unsat_clauses_of_var - orig_unsat_clauses_of_var
        if change == best_change:
            best_flips.append(i)
        elif change < best_change:
            best_flips = [i,]
        
    assert len(best_flips) != 0
    return best_flips
    


def _do_gsat_try(formula: CNF,
                 probability: float,
                 max_iters: int,
                 helper: FormulaHelper):
    config = Configuration(formula.nv)
    config.set_random()
    best_config = Configuration(formula.nv)
    best_satisfied_count = 0
    unsatisfied_clauses = None
    for iter_no in range(max_iters):
        unsatisfied_clauses = get_unsatisfied_clauses(formula, config)
        satisfied_count = len(formula.clauses) - len(unsatisfied_clauses)

        if satisfied_count >= best_satisfied_count:
            best_satisfied_count = satisfied_count
            best_config.from_config(config)

        if len(unsatisfied_clauses) == 0:
            break

        if random.random() <= probability:
            # randomly pick an unsatisfied clause in F. 
            clausule = random.choice(unsatisfied_clauses)
            # randomly pick a variable in that clause.
            variable = random.choice(clausule)
            # flip the truth assignment of the chosen variable.
            config.flip_variable(variable)
        else:
            # randomly pick any variable in T
            # whose value flip results in greatest
            # decrease (can be 0 or negative)
            # in the number of unsatisfied clauses.
            best_flips = _get_best_flips(formula, config, helper)
            variable = random.choice(best_flips)
            config.flip_variable(variable)
    
    return best_config, iter_no


def gsat(formula: CNF,
         probability: float,
         max_tries: int,
         max_iters: int):
    helper = FormulaHelper(formula)
    best_config = Configuration(formula.nv)
    best_satisfied_count = 0
    solved = False
    for try_no in range(max_tries):
        config, iter_cnt = _do_gsat_try(formula,
                                        probability,
                                        max_iters,
                                        helper)

        unsatisfied_clauses = get_unsatisfied_clauses(formula, config)
        solved = len(unsatisfied_clauses) == 0
        satisfied_count = len(formula.clauses) - len(unsatisfied_clauses)
        if satisfied_count >= best_satisfied_count:
            best_satisfied_count = satisfied_count
            best_config.from_config(config)

        if solved:
            break

    # -----------------------------
    # print results:
    iteration_count = try_no * max_iters + iter_cnt + 1
    max_iteration_count = max_tries * max_iters

    print(f"{iteration_count}, {max_iteration_count}, {satisfied_count}, {len(formula.clauses)}",
          file=sys.stderr)
    print(best_config.variable_evaluation)
    
    # -----------------------------
    # verify:
    with Solver(bootstrap_with=formula) as solver:
        assert solver.solve(assumptions=config.variable_evaluation) == solved


def main(args):
    parser = ArgumentParser()
    parser.add_argument("--cfg-file",
                        required=True,
                        help="File path containing formula configuration.")
    parser.add_argument('--probability',
                        default=0.4,
                        type=float,
                        help="Probability of random step in each iteration.")
    parser.add_argument("--max-tries",
                        default=1,
                        type=int,
                        help="Limit of restarts. 0 means no limit.")
    parser.add_argument("--max-iters",
                        default=300,
                        type=int,
                        help="Limit of iterations. 0 means no limit.")
    parser.add_argument("--seed",
                        default=None,
                        help="Optional seed for random generator.")
    args = parser.parse_args(args[1:])

    # Check inputs.
    assert 0 <= args.probability <= 1
    assert 0 <= args.max_tries
    assert 0 <= args.max_iters
    path = Path(args.cfg_file)
    assert path.exists() and path.is_file()

    # Unlimited tries and iters.
    if args.max_tries == 0:
        args.max_tries = 0xFFFF_FFFF
    
    if args.max_iters == 0:
        args.max_iters = 0xFFFF_FFFF
    
    # Random seed.
    if args.seed is not None:
        random.seed(args.seed)
    
    gsat(CNF(from_file=path),
         args.probability,
         args.max_tries,
         args.max_iters)


if __name__ == '__main__':
    main(sys.argv)
