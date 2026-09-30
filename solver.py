"""
solver.py - Modular Constraint Satisfaction Problem (CSP) Solver Engine
Fakultas Informatika dan Teknik Elektro - Institut Teknologi Del
Mata Kuliah: 10S3001 - Artificial Intelligence

Fitur Utama:
1. Abstraksi Generik: Variable, Domain, UnaryConstraint, BinaryConstraint, & GlobalConstraint.
2. Propagasi Batasan AC-3 (Arc Consistency 3) via Prosedur Revise.
3. Rekursif Backtracking Search dengan Akselerasi Heuristik:
   - MRV (Minimum Remaining Values) dengan Degree Heuristic sebagai pemutus seri.
   - LCV (Least Constraining Value).
   - FC (Forward Checking) untuk memangkas domain tetangga secara dinamis.
4. Pengukuran Performa (Waktu eksekusi, backtrack count, ac3 revisions, constraint checks).
"""

import copy
from collections import deque
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class Constraint:
    """
    Kelas abstrak untuk representasi batasan (constraint) pada CSP.
    """

    def __init__(self, variables: List[Any], name: str = "Constraint"):
        self.variables = variables
        self.name = name

    def is_satisfied(self, assignment: Dict[Any, Any]) -> bool:
        """
        Memeriksa apakah batasan terpenuhi pada assignment tertentu.
        """
        raise NotImplementedError

    def is_violating(self, assignment: Dict[Any, Any]) -> bool:
        """
        Mengembalikan True jika penugasan saat ini secara eksplisit melanggar batasan ini.
        """
        if all(v in assignment for v in self.variables):
            return not self.is_satisfied(assignment)
        return False


class BinaryConstraint(Constraint):
    """
    Representasi batasan biner (Arity 2) antara dua variabel (var1, var2).
    """

    def __init__(
        self,
        var1: Any,
        var2: Any,
        satisfied_pair_fn: Callable[[Any, Any], bool],
        name: str = "BinaryConstraint",
    ):
        super().__init__([var1, var2], name=name)
        self.var1 = var1
        self.var2 = var2
        self.satisfied_pair_fn = satisfied_pair_fn

    def is_satisfied(self, assignment: Dict[Any, Any]) -> bool:
        if self.var1 in assignment and self.var2 in assignment:
            return self.satisfied_pair_fn(assignment[self.var1], assignment[self.var2])
        return True

    def is_pair_satisfied(self, val1: Any, val2: Any) -> bool:
        return self.satisfied_pair_fn(val1, val2)


class UnaryConstraint(Constraint):
    """
    Representasi batasan unary (Arity 1) pada satu variabel.
    """

    def __init__(
        self,
        var: Any,
        satisfied_val_fn: Callable[[Any], bool],
        name: str = "UnaryConstraint",
    ):
        super().__init__([var], name=name)
        self.var = var
        self.satisfied_val_fn = satisfied_val_fn

    def is_satisfied(self, assignment: Dict[Any, Any]) -> bool:
        if self.var in assignment:
            return self.satisfied_val_fn(assignment[self.var])
        return True


class GlobalConstraint(Constraint):
    """
    Representasi batasan tingkat tinggi / global (Arity k >= 3).
    """

    def __init__(
        self,
        variables: List[Any],
        satisfied_fn: Callable[[Dict[Any, Any]], bool],
        name: str = "GlobalConstraint",
    ):
        super().__init__(variables, name=name)
        self.satisfied_fn = satisfied_fn

    def is_satisfied(self, assignment: Dict[Any, Any]) -> bool:
        return self.satisfied_fn(assignment)


class CSP:
    """
    Formulasi Komponen CSP Tiga Serangkai <X, D, C>.
    """

    def __init__(self, variables: List[Any], domains: Dict[Any, List[Any]]):
        self.variables: List[Any] = list(variables)
        self.domains: Dict[Any, List[Any]] = {v: list(domains[v]) for v in variables}
        self.constraints: Dict[Any, List[Constraint]] = {v: [] for v in variables}
        self.binary_constraints: List[BinaryConstraint] = []
        self.global_constraints: List[Constraint] = []
        self.neighbors: Dict[Any, Set[Any]] = {v: set() for v in variables}

    def add_constraint(self, constraint: Constraint) -> None:
        """
        Menambahkan batasan ke dalam struktur data CSP.
        """
        for v in constraint.variables:
            if v in self.constraints:
                self.constraints[v].append(constraint)

        if isinstance(constraint, BinaryConstraint):
            self.binary_constraints.append(constraint)
            self.neighbors[constraint.var1].add(constraint.var2)
            self.neighbors[constraint.var2].add(constraint.var1)
        elif isinstance(constraint, UnaryConstraint):
            var = constraint.var
            self.domains[var] = [
                val for val in self.domains[var] if constraint.satisfied_val_fn(val)
            ]
        else:
            self.global_constraints.append(constraint)
            for v1 in constraint.variables:
                for v2 in constraint.variables:
                    if v1 != v2:
                        self.neighbors[v1].add(v2)

    def is_consistent(self, var: Any, value: Any, assignment: Dict[Any, Any]) -> bool:
        """
        Pemeriksaan konsistensi parsial.
        GlobalConstraint dievaluasi langsung pada temp_assignment parsial untuk pemangkasan dini.
        """
        temp_assignment = assignment.copy()
        temp_assignment[var] = value

        for constraint in self.constraints[var]:
            if isinstance(constraint, GlobalConstraint):
                if not constraint.is_satisfied(temp_assignment):
                    return False
            elif all(v in temp_assignment for v in constraint.variables):
                if not constraint.is_satisfied(temp_assignment):
                    return False
        return True


class CSPSolverMetrics:
    """
    Kelas untuk merekam metrik kinerja pencarian dan propagasi.
    """

    def __init__(self):
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.runtime_sec: float = 0.0
        self.backtracks: int = 0
        self.assignments: int = 0
        self.ac3_revisions: int = 0
        self.constraint_checks: int = 0
        self.solved: bool = False

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self, solved: bool):
        self.end_time = time.perf_counter()
        self.runtime_sec = self.end_time - self.start_time
        self.solved = solved


def ac3(
    csp: CSP,
    queue: Optional[List[Tuple[Any, Any]]] = None,
    metrics: Optional[CSPSolverMetrics] = None,
) -> bool:
    """
    Algoritma Arc Consistency 3 (AC-3).
    """
    if queue is None:
        queue_deque = deque()
        for b_constraint in csp.binary_constraints:
            queue_deque.append((b_constraint.var1, b_constraint.var2))
            queue_deque.append((b_constraint.var2, b_constraint.var1))
    else:
        queue_deque = deque(queue)

    while queue_deque:
        Xi, Xj = queue_deque.popleft()
        if revise(csp, Xi, Xj, metrics):
            if metrics:
                metrics.ac3_revisions += 1
            if len(csp.domains[Xi]) == 0:
                return False  # Domain kosong -> Gagal
            for Xk in csp.neighbors[Xi]:
                if Xk != Xj:
                    queue_deque.append((Xk, Xi))
    return True


def revise(
    csp: CSP,
    Xi: Any,
    Xj: Any,
    metrics: Optional[CSPSolverMetrics] = None,
) -> bool:
    """
    Prosedur Revise(Xi, Xj) untuk AC-3.
    """
    revised = False
    relevant_constraints = [
        c
        for c in csp.binary_constraints
        if (c.var1 == Xi and c.var2 == Xj) or (c.var1 == Xj and c.var2 == Xi)
    ]

    if not relevant_constraints:
        return False

    to_remove = []
    for x in csp.domains[Xi]:
        has_support = False
        for y in csp.domains[Xj]:
            if metrics:
                metrics.constraint_checks += 1

            all_satisfied = True
            for c in relevant_constraints:
                val1 = x if c.var1 == Xi else y
                val2 = y if c.var1 == Xi else x
                if not c.is_pair_satisfied(val1, val2):
                    all_satisfied = False
                    break

            if all_satisfied:
                has_support = True
                break

        if not has_support:
            to_remove.append(x)
            revised = True

    for x in to_remove:
        csp.domains[Xi].remove(x)

    return revised


def select_unassigned_variable(
    csp: CSP, assignment: Dict[Any, Any], use_mrv: bool = True
) -> Any:
    """
    Pilihan variabel berikutnya dengan MRV + Degree Heuristic.
    """
    unassigned = [v for v in csp.variables if v not in assignment]
    if not use_mrv or not unassigned:
        return unassigned[0]

    def mrv_degree_key(var):
        domain_size = len(csp.domains[var])
        unassigned_neighbors = sum(
            1 for n in csp.neighbors[var] if n not in assignment
        )
        return (domain_size, -unassigned_neighbors)

    return min(unassigned, key=mrv_degree_key)


def order_domain_values(
    csp: CSP, var: Any, assignment: Dict[Any, Any], use_lcv: bool = True
) -> List[Any]:
    """
    Pengurutan nilai domain dengan LCV.
    """
    values = list(csp.domains[var])
    if not use_lcv or len(values) <= 1:
        return values

    def count_eliminated_choices(val):
        eliminated = 0
        for neighbor in csp.neighbors[var]:
            if neighbor not in assignment:
                for n_val in csp.domains[neighbor]:
                    for c in csp.binary_constraints:
                        if c.var1 == var and c.var2 == neighbor:
                            if not c.is_pair_satisfied(val, n_val):
                                eliminated += 1
                        elif c.var1 == neighbor and c.var2 == var:
                            if not c.is_pair_satisfied(n_val, val):
                                eliminated += 1
        return eliminated

    values.sort(key=count_eliminated_choices)
    return values


def forward_check(
    csp: CSP,
    var: Any,
    value: Any,
    assignment: Dict[Any, Any],
    metrics: Optional[CSPSolverMetrics] = None,
) -> Tuple[bool, Dict[Any, List[Any]]]:
    """
    Forward Checking (FC).
    """
    pruned = {}
    for neighbor in csp.neighbors[var]:
        if neighbor not in assignment:
            new_domain = []
            for n_val in csp.domains[neighbor]:
                if metrics:
                    metrics.constraint_checks += 1

                consistent = True
                for c in csp.binary_constraints:
                    if c.var1 == var and c.var2 == neighbor:
                        if not c.is_pair_satisfied(value, n_val):
                            consistent = False
                            break
                    elif c.var1 == neighbor and c.var2 == var:
                        if not c.is_pair_satisfied(n_val, value):
                            consistent = False
                            break
                if consistent:
                    new_domain.append(n_val)

            if len(new_domain) == 0:
                return False, pruned
            if len(new_domain) < len(csp.domains[neighbor]):
                pruned[neighbor] = csp.domains[neighbor]
                csp.domains[neighbor] = new_domain

    return True, pruned


def backtrack_search(
    csp: CSP,
    use_ac3_preprocess: bool = True,
    use_mrv: bool = True,
    use_lcv: bool = True,
    use_fc: bool = True,
    metrics: Optional[CSPSolverMetrics] = None,
) -> Tuple[Optional[Dict[Any, Any]], CSPSolverMetrics]:
    """
    Backtracking Search dengan AC-3, MRV, LCV, dan FC.
    """
    if metrics is None:
        metrics = CSPSolverMetrics()

    metrics.start()
    csp_working = copy.deepcopy(csp)

    if use_ac3_preprocess:
        ac3_ok = ac3(csp_working, metrics=metrics)
        if not ac3_ok:
            metrics.stop(solved=False)
            return None, metrics

    def backtrack(assignment: Dict[Any, Any]) -> Optional[Dict[Any, Any]]:
        if len(assignment) == len(csp_working.variables):
            for gc in csp_working.global_constraints:
                if metrics:
                    metrics.constraint_checks += 1
                if not gc.is_satisfied(assignment):
                    return None
            return assignment

        var = select_unassigned_variable(csp_working, assignment, use_mrv=use_mrv)
        ordered_vals = order_domain_values(
            csp_working, var, assignment, use_lcv=use_lcv
        )

        for val in ordered_vals:
            metrics.assignments += 1
            if csp_working.is_consistent(var, val, assignment):
                assignment[var] = val

                fc_ok = True
                pruned_domains = {}
                if use_fc:
                    fc_ok, pruned_domains = forward_check(
                        csp_working, var, val, assignment, metrics
                    )

                if fc_ok:
                    result = backtrack(assignment)
                    if result is not None:
                        return result

                metrics.backtracks += 1
                del assignment[var]
                for neighbor, orig_domain in pruned_domains.items():
                    csp_working.domains[neighbor] = orig_domain

        return None

    solution = backtrack({})
    metrics.stop(solved=(solution is not None))
    return solution, metrics
