"""
test_solver.py - Suite Pengujian Otomatis Modul CSP Solver & Kasus Ekstrem (Edge Cases)
Fakultas Informatika dan Teknik Elektro - Institut Teknologi Del
"""

import sys
import unittest
from solver import (
    CSP,
    UnaryConstraint,
    BinaryConstraint,
    ac3,
    backtrack_search,
    CSPSolverMetrics,
)
from business_problem import StaffShiftSchedulingProblem, LogisticsAllocationProblem


class TestCSPSolver(unittest.TestCase):

    def test_ac3_domain_pruning(self):
        """
        Uji apakah algoritma AC-3 berhasil memangkas nilai domain yang inkonsisten secara logis.
        Contoh: X1, X2 in {1, 2, 3}, batasan biner X1 > X2.
        Domain X1 harus terpotong menjadi {2, 3} dan X2 terpotong menjadi {1, 2}.
        """
        variables = ["X1", "X2"]
        domains = {"X1": [1, 2, 3], "X2": [1, 2, 3]}
        csp = CSP(variables, domains)

        def greater_than(val1, val2):
            return val1 > val2

        csp.add_constraint(BinaryConstraint("X1", "X2", greater_than))

        metrics = CSPSolverMetrics()
        result = ac3(csp, metrics=metrics)

        self.assertTrue(result)
        self.assertEqual(set(csp.domains["X1"]), {2, 3})
        self.assertEqual(set(csp.domains["X2"]), {1, 2})
        self.assertGreater(metrics.ac3_revisions, 0)

    def test_edge_case_unsolvable_overconstrained(self):
        """
        KASUS EKSTREM 1: Over-constrained (Tidak Memiliki Solusi).
        2 Staf, 1 Hari, Keduanya menolak shift Malam, tetapi shift Malam membutuhkan min 1 staf senior (Staf 1).
        Solver harus segera mendeteksi kegagalan (solution is None).
        """
        problem = StaffShiftSchedulingProblem(
            num_staff=2,
            num_days=1,
            senior_staff_ids=[1],
            unavailability={(1, 1): ["Malam"], (2, 1): ["Malam"]},
            shift_capacity={"Pagi": 0, "Siang": 0, "Malam": 1},
        )
        csp = problem.build_csp()
        sol, metrics = backtrack_search(csp, use_ac3_preprocess=True)

        self.assertIsNone(sol)
        self.assertFalse(metrics.solved)

    def test_edge_case_empty_domain(self):
        """
        KASUS EKSTREM 2: Empty Domain awal karena Unary Constraint kontradiktif.
        Staf 1 menolak seluruh opsi shift ['Pagi', 'Siang', 'Malam', 'Libur'].
        """
        variables = ["X1"]
        domains = {"X1": ["Pagi", "Siang", "Malam", "Libur"]}
        csp = CSP(variables, domains)
        csp.add_constraint(UnaryConstraint("X1", lambda v: False))  # Tolak semua

        sol, metrics = backtrack_search(csp)
        self.assertIsNone(sol)
        self.assertFalse(metrics.solved)

    def test_edge_case_tightly_constrained_single_solution(self):
        """
        KASUS EKSTREM 3: Tightly Constrained (Tepat Memiliki 1 Solusi Unik).
        """
        variables = ["A", "B", "C"]
        domains = {"A": [1, 2, 3], "B": [1, 2, 3], "C": [1, 2, 3]}
        csp = CSP(variables, domains)

        # A < B < C -> Solusi unik: A=1, B=2, C=3
        csp.add_constraint(BinaryConstraint("A", "B", lambda a, b: a < b))
        csp.add_constraint(BinaryConstraint("B", "C", lambda b, c: b < c))

        sol, metrics = backtrack_search(csp, use_ac3_preprocess=True)
        self.assertIsNotNone(sol)
        self.assertEqual(sol["A"], 1)
        self.assertEqual(sol["B"], 2)
        self.assertEqual(sol["C"], 3)

    def test_staff_scheduling_normal_case(self):
        """
        Uji Kasus Penjadwalan Staf Normal (4 Staf, 3 Hari).
        """
        problem = StaffShiftSchedulingProblem(
            num_staff=4,
            num_days=3,
            senior_staff_ids=[1, 2],
            unavailability={(1, 1): ["Malam"], (3, 2): ["Pagi"]},
            conflict_pairs=[(1, 2)],
            shift_capacity={"Pagi": 1, "Siang": 1, "Malam": 1},
        )
        csp = problem.build_csp()
        sol, metrics = backtrack_search(
            csp, use_ac3_preprocess=True, use_mrv=True, use_fc=True
        )

        self.assertIsNotNone(sol)
        self.assertTrue(metrics.solved)
        self.assertEqual(len(sol), 12)  # 4 staff x 3 days

        # Verifikasi batasan istirahat (Malam -> Pagi melanggar)
        for s_id in range(1, 5):
            d1_val = sol[(f"Staff_{s_id}", "Day_1")]
            d2_val = sol[(f"Staff_{s_id}", "Day_2")]
            if d1_val == "Malam":
                self.assertNotEqual(d2_val, "Pagi")

    def test_logistics_allocation_normal_case(self):
        """
        Uji Kasus Alokasi Logistik Normal (4 Barang, 3 Zona).
        """
        items = [
            {"id": "Vaccine_Batch_1", "required_zone": "Zone_Cold"},
            {"id": "Chemical_A", "required_zone": None},
            {"id": "Chemical_B", "required_zone": None},
            {"id": "General_Box", "required_zone": "Zone_General"},
        ]
        zones = ["Zone_Cold", "Zone_Hazardous", "Zone_General"]
        capacities = {"Zone_Cold": 2, "Zone_Hazardous": 2, "Zone_General": 2}
        incompatibilities = [("Chemical_A", "Chemical_B")]

        problem = LogisticsAllocationProblem(
            items, zones, capacities, incompatibilities
        )
        csp = problem.build_csp()
        sol, metrics = backtrack_search(csp, use_ac3_preprocess=True)

        self.assertIsNotNone(sol)
        self.assertEqual(sol["Vaccine_Batch_1"], "Zone_Cold")
        self.assertEqual(sol["General_Box"], "Zone_General")
        self.assertNotEqual(sol["Chemical_A"], sol["Chemical_B"])

    def test_heuristics_efficiency_comparison(self):
        """
        Uji efisiensi Heuristik (MRV + LCV + FC) vs Naive Backtracking.
        """
        problem = StaffShiftSchedulingProblem(
            num_staff=4,
            num_days=2,
            senior_staff_ids=[1],
            shift_capacity={"Pagi": 1, "Siang": 1, "Malam": 1},
        )
        csp = problem.build_csp()

        # 1. Dengan Heuristik Lengkap
        sol_h, metrics_h = backtrack_search(
            csp, use_ac3_preprocess=True, use_mrv=True, use_lcv=True, use_fc=True
        )

        # 2. Naive (Tanpa Heuristik)
        sol_n, metrics_n = backtrack_search(
            csp, use_ac3_preprocess=False, use_mrv=False, use_lcv=False, use_fc=False
        )

        self.assertIsNotNone(sol_h)
        self.assertIsNotNone(sol_n)
        self.assertLessEqual(metrics_h.backtracks, metrics_n.backtracks)


if __name__ == "__main__":
    unittest.main()
