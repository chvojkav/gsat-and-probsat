
import random
from copy import deepcopy
from typing import Iterable

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
