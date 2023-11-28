import random
from copy import deepcopy
from typing import Iterable
import numpy

from pysat.formula import CNF

clause = list[int]
clause_list = Iterable[clause]
# Helps to identify clauses in the original formula
enumerated_clause_list = Iterable[tuple[clause, int]]

class Configuration:
    def __init__(self, variable_cnt: int):
        self._variable_cnt: int = variable_cnt
        self.variable_evaluation: list[bool] | None = None
    
    def set_random(self):
        self.variable_evaluation = [None]
        for i in range(self._variable_cnt):
            is_true = random.choice((True, False))
            evaluation = i + 1
            if not is_true:
                evaluation *= -1

            self.variable_evaluation.append(evaluation)
        
        # Now copy the evaluation reversed to support negative indexes.
        cpy = deepcopy(self.variable_evaluation)
        cpy.reverse()
        self.variable_evaluation.extend(cpy)
        self.variable_evaluation.pop() # Pop the final None
    
    def from_config(self, other: "Configuration"):
        self._variable_cnt = other._variable_cnt
        self.variable_evaluation = deepcopy(other.variable_evaluation)

    def flip_variable(self, variable_name: int):
        variable_index = abs(variable_name)
        self.variable_evaluation[variable_index] *= -1
        self.variable_evaluation[-variable_index] *= -1

    def evaluate_variable(self, variable_name: int) -> bool:
        # variable_name is f.e. "2" or "-1" or "-15".
        # So it contains variable name plus evaluation.
        # Checks if the variable evaluation is in current configuration.
        return variable_name == self.variable_evaluation[variable_name]
    
    def get_evaluation(self) -> list[int]:
        return self.variable_evaluation[1 : self._variable_cnt + 1]


class FormulaHelper:
    def __init__(self, formula: CNF):
        # Contains list of clauses for each variable.
        self.clauses_per_var: dict[int, enumerated_clause_list] = {}
        for i in range(1, formula.nv + 1):
            tmp = self._find_clauses_for_var(formula, i)
            self.clauses_per_var[i] = tmp
            self.clauses_per_var[-i] = tmp
    
    @staticmethod
    def _find_clauses_for_var(formula: clause_list, variable_no: int) -> enumerated_clause_list:
        clauses = []
        for i, clause in enumerate(formula):
            for variable in clause:
                if variable_no == abs(variable):
                    clauses.append((clause, i))
                    break
        
        return clauses
    
    def __getitem__(self, key) -> enumerated_clause_list:
        return self.clauses_per_var[key]


def get_unsatisfied_clauses(form: clause_list,
                              config: Configuration) \
                                -> clause_list:
    unsatisfied_clauses = []
    for clausule in form:
        satisfied = False
        for variable in clausule:
            if config.evaluate_variable(variable):
                # One variable of clausule is satisfied
                # hence whole clausule is satisfied
                satisfied = True
                break
        
        if not satisfied:
            unsatisfied_clauses.append(clausule)
    
    return unsatisfied_clauses
