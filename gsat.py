from pathlib import Path
import random
import sys
from argparse import ArgumentParser
from copy import deepcopy
from typing import Iterable

from pysat.formula import CNF
from pysat.solvers import Solver

clause = list[int]
clause_list = Iterable[clause]

class Configuration:
    def __init__(self, variable_cnt: int):
        self._variable_cnt: int = variable_cnt
        self.variable_evaluation: list[bool] | None = None
    
    def set_random(self):
        self.variable_evaluation = []
        for i in range(self._variable_cnt):
            is_true = random.choice((True, False))
            evaluation = i + 1
            if not is_true:
                evaluation *= -1

            self.variable_evaluation.append(evaluation)
    
    def from_config(self, other: "Configuration"):
        self._variable_cnt = other._variable_cnt
        self.variable_evaluation = deepcopy(other.variable_evaluation)

    def flip_variable(self, variable_name: int):
        variable_index = abs(variable_name) - 1
        self.variable_evaluation[variable_index] *= -1

    def evaluate_variable(self, variable_name: int) -> bool:
        # variable_name is f.e. "2" or "-1" or "-15".
        # So it contains variable name plus evaluation.
        # Checks if the variable evaluation is in current configuration.
        variable_index = abs(variable_name) - 1
        return variable_name == self.variable_evaluation[variable_index]


class FormulaHelper:
    def __init__(self, formula: CNF):
        # Contains list of clauses for each variable.
        self.clauses_per_var: dict[int, clause_list] = {}
        for i in range(1, formula.nv + 1):
            tmp = self._find_clauses_for_var(formula, i)
            self.clauses_per_var[i] = tmp
            self.clauses_per_var[-i] = tmp
    
    @staticmethod
    def _find_clauses_for_var(formula: clause_list, variable_no: int) -> clause_list:
        clauses = []
        for clause in formula:
            for variable in clause:
                if variable_no == abs(variable):
                    clauses.append(clause)
                    break
        
        return clauses
    
    def __getitem__(self, key) -> clause_list:
        return self.clauses_per_var[key]


def get_unsatisfied_clausules(form: clause_list,
                              config: Configuration) \
                                -> clause_list:
    unsatisfied_clausules = []
    for clausule in form:
        satisfied = False
        for variable in clausule:
            if config.evaluate_variable(variable):
                # One variable of clausule is satisfied
                # hence whole clausule is satisfied
                satisfied = True
                break
        
        if not satisfied:
            unsatisfied_clausules.append(clausule)
    
    return unsatisfied_clausules


def _get_best_flips(formula: CNF,
                    config: Configuration,
                    helper: FormulaHelper) -> list[int]:
    best_change = len(formula.clauses)  # worst case is that we newly usatisfy all clauses.
    best_flips = []
    for i in range(1, formula.nv + 1):
        orig_unsat_clauses_of_var = len(get_unsatisfied_clausules(helper[i], config))
        config.flip_variable(i)
        new_unsat_clauses_of_var = len(get_unsatisfied_clausules(helper[i], config))
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
        unsatisfied_clauses = get_unsatisfied_clausules(formula, config)
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

        unsatisfied_clausules = get_unsatisfied_clausules(formula, config)
        solved = len(unsatisfied_clausules) == 0
        satisfied_count = len(formula.clauses) - len(unsatisfied_clausules)
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
