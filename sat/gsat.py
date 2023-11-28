from pathlib import Path
import random
import sys
from argparse import ArgumentParser

from pysat.formula import CNF
from pysat.solvers import Solver


from sat import Configuration, FormulaHelper, clause_list


class Gsat:
    def __init__(self,
                 formula: CNF,
                 probability: float,
                 max_tries: int,
                 max_iters: int) -> None:
        self.formula = formula
        self.clauses_cnt = len(self.formula.clauses)
        self.probability = probability
        self.max_tries = max_tries
        self.max_iters = max_iters
        self.helper = FormulaHelper(formula)
        self.best_config = Configuration(formula.nv)
        self.best_satisfied_count = 0
        self.solved = False
        self.working_config = Configuration(formula.nv)
        self.counts_of_satisfied_literals: list[int] = []
    
    def run(self) -> tuple[int, int, list[int]]:
        for try_no in range(self.max_tries):
            iter_cnt = self._do_gsat_try()

            if self.solved:
                break
            
        # -----------------------------
        # verify:
        with Solver(bootstrap_with=self.formula) as solver:
            assert solver.solve(assumptions=self.best_config.get_evaluation()) == self.solved

        # -----------------------------
        # print results:
        iteration_count = try_no * self.max_iters + iter_cnt + 1

        return iteration_count, self.best_satisfied_count, self.best_config.get_evaluation()

    def _do_gsat_try(self) -> tuple[Configuration, int]:
        self.working_config.set_random()
        self.calculate_counts_of_satisfied_literals()
        unsatisfied_clauses = None
        for iter_no in range(self.max_iters):
            unsatisfied_clauses = self.get_unsatisfied_clauses()
            satisfied_count = self.clauses_cnt - len(unsatisfied_clauses)

            if satisfied_count >= self.best_satisfied_count:
                self.best_satisfied_count = satisfied_count
                self.best_config.from_config(self.working_config)

            if len(unsatisfied_clauses) == 0:
                self.solved = True
                break

            if random.random() <= self.probability:
                # randomly pick an unsatisfied clause in F. 
                clausule = random.choice(unsatisfied_clauses)
                # randomly pick a variable in that clause.
                variable = random.choice(clausule)
                # flip the truth assignment of the chosen variable.
                self.flip_variable(variable)
            else:
                # randomly pick any variable in T
                # whose value flip results in greatest
                # decrease (can be 0 or negative)
                # in the number of unsatisfied clauses.
                best_flips = self._get_best_flips()
                variable = random.choice(best_flips)
                self.flip_variable(variable)
        
        return iter_no
    
    def calculate_counts_of_satisfied_literals(self):
        self.counts_of_satisfied_literals = []
        for clause in self.formula:
            count_of_satisfied_literals = 0
            for variable in clause:
                if self.working_config.evaluate_variable(variable):
                    count_of_satisfied_literals += 1
            self.counts_of_satisfied_literals.append(count_of_satisfied_literals)
    
    def flip_variable(self, variable_name: int):
        self.working_config.flip_variable(variable_name)

        # Recalculate satisfied literals counts.
        for clause, clause_index in self.helper[variable_name]:
            new_sat_cnt = 0
            for variable in clause:
                new_sat_cnt += self.working_config.evaluate_variable(variable)
                    
            self.counts_of_satisfied_literals[clause_index] = new_sat_cnt
    
    def sat_change_if_fliped(self, variable_name: int) -> int:
        # Returns hypotetical change in number of satisfied clauses.
        # Positive means more would be satisfied. negative means less would be satisfied.
        change = 0
        for clause, clause_index in self.helper[variable_name]:
            if self.counts_of_satisfied_literals[clause_index] == 0:
                change += 1
            elif self.counts_of_satisfied_literals[clause_index] == 1:
                for variable in clause:
                    if abs(variable) == variable_name \
                            and self.working_config.evaluate_variable(variable):
                        change -= 1
                        break
        
        return change

    def get_unsatisfied_clauses(self) -> clause_list:
        ret = []
        for clause, sat_cnt in zip(self.formula, self.counts_of_satisfied_literals):
            if sat_cnt == 0:
                ret.append(clause)
        
        return ret

    def _get_best_flips(self) -> list[int]:
        best_change = -self.clauses_cnt  # worst case is that we newly usatisfy all clauses.
        best_flips = []
        for i in range(1, self.formula.nv + 1):
            change = self.sat_change_if_fliped(i)
            if change == best_change:
                best_flips.append(i)
            elif change > best_change:
                best_flips = [i,]
            
        assert len(best_flips) != 0
        return best_flips


def gsat(formula: CNF,
        probability: float,
        max_tries: int,
        max_iters: int):
    solver = Gsat(formula, probability, max_tries, max_iters)
    return solver.run()


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
    
    # ---------------------------
    # Execution.
    formula = CNF(from_file=path)

    iteration_count, satisfied_count, variable_evaluation = \
        gsat(formula,
             args.probability,
             args.max_tries,
             args.max_iters)
    
    max_iteration_count = args.max_tries * args.max_iters

    print(f"{iteration_count}, {max_iteration_count}, {satisfied_count}, {len(formula.clauses)}",
          file=sys.stderr)
    print(variable_evaluation)

if __name__ == '__main__':
    main(sys.argv)
