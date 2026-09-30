"""
main.py - Entry Point Eksekusi Modul CSP Solver Keputusan Bisnis
Fakultas Informatika dan Teknik Elektro - Institut Teknologi Del
Mata Kuliah: 10S3001 - Artificial Intelligence
"""

import argparse
import json
from business_problem import StaffShiftSchedulingProblem, LogisticsAllocationProblem
from solver import backtrack_search, ac3, CSPSolverMetrics
import benchmark


def run_staff_scheduling_demo():
    print("\n" + "=" * 70)
    print(" DEMO 1: PENJADWALAN SHIFT STAF ENTERPRISE / RUMAH SAKIT")
    print("=" * 70)

    problem = StaffShiftSchedulingProblem(
        num_staff=5,
        num_days=3,
        senior_staff_ids=[1, 2],
        unavailability={(1, 1): ["Malam"], (3, 2): ["Pagi"]},
        conflict_pairs=[(1, 2)],
        shift_capacity={"Pagi": 1, "Siang": 1, "Malam": 1},
    )

    print("Definisi Masalah:")
    print(f" - Jumlah Staf: {problem.num_staff} (Senior: Staff_1, Staff_2)")
    print(f" - Periode Hari: {problem.num_days} Hari")
    print(" - Batasan Unary: Staff_1 Cuti Malam Hari 1; Staff_3 Cuti Pagi Hari 2; Staff Junior (3,4,5) Dilarang Shift Malam")
    print(" - Batasan Biner: Rest Period (Malam Hari t -> Melarang Pagi Hari t+1); Konflik Malam Staff_1 & Staff_2")
    print(" - Batasan Global: Minimal 1 Pagi, 1 Siang, 1 Malam per Hari; Min 1 Senior pada Shift Malam")

    csp = problem.build_csp()
    print("\nMenjalankan AC-3 & Backtracking Search dengan MRV, LCV, Forward Checking...")
    sol, metrics = backtrack_search(
        csp, use_ac3_preprocess=True, use_mrv=True, use_lcv=True, use_fc=True
    )

    if sol:
        print("\n[BERHASIL] Solusi Penjadwalan Ditemukan:")
        print("-" * 50)
        # Format output matriks jadwal
        for s_id in range(1, problem.num_staff + 1):
            row_str = f"Staff_{s_id:<2}: "
            for day in range(1, problem.num_days + 1):
                val = sol[(f"Staff_{s_id}", f"Day_{day}")]
                row_str += f"[Hari {day}: {val:<6}] "
            print(row_str)
        print("-" * 50)
    else:
        print("\n[GAGAL] Solusi Tidak Ditemukan (Over-constrained).")

    print(f"Metrik: Waktu={metrics.runtime_sec:.4f}s | Backtracks={metrics.backtracks} | AC3 Revisions={metrics.ac3_revisions} | Constraint Checks={metrics.constraint_checks}")


def run_logistics_allocation_demo():
    print("\n" + "=" * 70)
    print(" DEMO 2: ALOKASI RUANG FASILITAS LOGISTIK MULTI-ZONA GUDANG")
    print("=" * 70)

    items = [
        {"id": "Vaksin_Biomedis_01", "required_zone": "Zone_Cold_Storage"},
        {"id": "Bahan_Kimia_Oksidator", "required_zone": None},
        {"id": "Bahan_Kimia_Flambel", "required_zone": None},
        {"id": "Elektronik_Presisi", "required_zone": "Zone_Dry_Vault"},
        {"id": "Kargo_Umum_A", "required_zone": None},
        {"id": "Kargo_Umum_B", "required_zone": None},
    ]

    zones = ["Zone_Cold_Storage", "Zone_Hazardous", "Zone_Dry_Vault", "Zone_General"]
    capacities = {
        "Zone_Cold_Storage": 2,
        "Zone_Hazardous": 2,
        "Zone_Dry_Vault": 2,
        "Zone_General": 3,
    }
    incompatibilities = [("Bahan_Kimia_Oksidator", "Bahan_Kimia_Flambel")]

    problem = LogisticsAllocationProblem(items, zones, capacities, incompatibilities)

    print("Definisi Masalah:")
    print(f" - Jumlah Barang Logistik: {len(items)}")
    print(f" - Zona Gudang Tersedia: {zones}")
    print(" - Batasan Unary: Vaksin wajib di Zone_Cold_Storage; Elektronik wajib di Zone_Dry_Vault")
    print(" - Batasan Biner: Bahan Oksidator dan Flambel TIDAK boleh di zona yang sama (Isolasi Bahaya)")
    print(" - Batasan Global: Kapasitas Maksimal Per Zona")

    csp = problem.build_csp()
    print("\nMenjalankan AC-3 & Backtracking Search...")
    sol, metrics = backtrack_search(csp, use_ac3_preprocess=True)

    if sol:
        print("\n[BERHASIL] Solusi Alokasi Ruang Ditemukan:")
        print("-" * 50)
        zone_map = {z: [] for z in zones}
        for item_id, assigned_zone in sol.items():
            zone_map[assigned_zone].append(item_id)

        for z, assigned_items in zone_map.items():
            print(f" {z:<20} (Kapasitas {capacities[z]}): {assigned_items}")
        print("-" * 50)
    else:
        print("\n[GAGAL] Solusi Tidak Ditemukan.")

    print(f"Metrik: Waktu={metrics.runtime_sec:.4f}s | Backtracks={metrics.backtracks} | AC3 Revisions={metrics.ac3_revisions} | Constraint Checks={metrics.constraint_checks}")


def main():
    parser = argparse.ArgumentParser(description="CSP Business Decision Solver CLI")
    parser.add_argument(
        "--case",
        choices=["staff", "logistics", "all"],
        default="all",
        help="Pilih studi kasus yang ingin dijalankan: staff | logistics | all",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Jalankan analisis sensitivitas skala dan buat grafik",
    )

    args = parser.parse_args()

    if args.benchmark:
        staff_res = benchmark.run_staff_scheduling_benchmarks()
        log_res = benchmark.run_logistics_benchmarks()
        benchmark.plot_sensitivity_analysis(staff_res, log_res)
    else:
        if args.case in ["staff", "all"]:
            run_staff_scheduling_demo()
        if args.case in ["logistics", "all"]:
            run_logistics_allocation_demo()


if __name__ == "__main__":
    main()
