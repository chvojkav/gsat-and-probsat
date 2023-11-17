from pathlib import Path
import random
import numpy.random
import sys
from argparse import ArgumentParser

from pysat.formula import CNF
from pysat.solvers import Solver


from sat import Configuration, FormulaHelper, get_unsatisfied_clauses, clause_list


def _get_formula_evals(formula: clause_list,
                       config: Configuration) -> list[bool]:
    clause_evals: list[bool] = []
    for clause in formula:
        for variable in clause:
            if config.evaluate_variable(variable):
                clause_evals.append(True)
                break
        else:
            clause_evals.append(False)
    
    return clause_evals


def satisfaction_changes_on_flip(formula: clause_list,
                                 config: Configuration,
                                 variable: int) -> tuple[int, int]:
    old_clause_evals = _get_formula_evals(formula, config)
    config.flip_variable(variable)
    new_clause_evals = _get_formula_evals(formula, config)
    config.flip_variable(variable)
    
    new_unsatisfied = 0
    new_satisfied = 0
    for old_evaluation, new_evaluation in zip(old_clause_evals, new_clause_evals, strict=True):
        if new_evaluation and not old_evaluation:
            new_satisfied += 1
        elif not new_evaluation and old_evaluation:
            new_unsatisfied += 1
    
    return new_satisfied, new_unsatisfied


def f(config: Configuration,
      variable: int,
      helper: FormulaHelper,
      cm: float,
      cb: float) -> float:
    make_, break_ = satisfaction_changes_on_flip(helper[variable],
                                                 config,
                                                 variable)
     
    return (make_ ** cm) / (0.00000000000001 + break_ ** cb)


def _do_randsat_try(formula: CNF,
                    max_flips: int,
                    cm: float,
                    cb: float,
                    helper: FormulaHelper):
    config = Configuration(formula.nv)
    config.set_random()
    best_config = Configuration(formula.nv)
    best_satisfied_count = 0
    unsatisfied_clauses = None
    for flip_no in range(max_flips):
        unsatisfied_clauses = get_unsatisfied_clauses(formula, config)
        satisfied_count = len(formula.clauses) - len(unsatisfied_clauses)

        if satisfied_count >= best_satisfied_count:
            best_satisfied_count = satisfied_count
            best_config.from_config(config)

        if len(unsatisfied_clauses) == 0:
            break

        clause = random.choice(unsatisfied_clauses)
        probabilities = [f(config, var, helper, cm, cb) for var in clause]
        sum_probs = sum(probabilities)
        probabilities = [p/sum_probs for p in probabilities]
        variable = numpy.random.choice(clause, 1, p=probabilities)
        config.flip_variable(variable[0])
    
    return best_config, flip_no
 

def randsat(formula: CNF,
            max_tries: int, 
            max_flips: int,
            cm: float,
            cb: float):
    helper = FormulaHelper(formula)
    best_config = Configuration(formula.nv)
    best_satisfied_count = 0
    solved = False
    for try_no in range(max_tries):
        config, flip_cnt = _do_randsat_try(formula,
                                           max_flips,
                                           cm,
                                           cb,
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
    flip_count = try_no * max_flips + flip_cnt + 1
    max_flip_count = max_tries * max_flips

    print(f"{flip_count}, {max_flip_count}, {satisfied_count}, {len(formula.clauses)}",
          file=sys.stderr)
    print(best_config.variable_evaluation)

    print(best_config.variable_evaluation)
    
    # -----------------------------
    # verify:
    with Solver(bootstrap_with=formula) as solver:
        assert solver.solve(assumptions=best_config.variable_evaluation) == solved


def main(args):
    parser = ArgumentParser()
    parser.add_argument("--cfg-file",
                        required=True,
                        help="File path containing formula configuration.")
    parser.add_argument("--max-tries",
                        default=1,
                        type=int,
                        help="Limit of restarts. 0 means no limit.")
    parser.add_argument("--max-flips",
                        default=300,
                        type=int,
                        help="Limit of flips. 0 means no limit.")
    parser.add_argument("--cm",
                        default=0,
                        type=float,
                        help="Exponent of make.")
    parser.add_argument("--cb",
                        default=2.3,
                        type=float,
                        help="Exponent of break.")
    parser.add_argument("--seed",
                        default=None,
                        help="Optional seed for random generator.")
    args = parser.parse_args(args[1:])

    # Check inputs.
    assert 0 <= args.max_tries
    assert 0 <= args.max_flips
    assert 0 <= args.cm
    assert 0 <= args.cb
    path = Path(args.cfg_file)
    assert path.exists() and path.is_file()

    # Unlimited tries and flips.
    if args.max_tries == 0:
        args.max_tries = 0xFFFF_FFFF
    
    if args.max_flips == 0:
        args.max_flips = 0xFFFF_FFFF
    
    # Random seed.
    if args.seed is not None:
        random.seed(args.seed)
    
    randsat(CNF(from_file=path),
            args.max_tries,
            args.max_flips,
            args.cm,
            args.cb)


if __name__ == '__main__':
    main(sys.argv)
