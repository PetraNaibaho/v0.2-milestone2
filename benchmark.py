"""
benchmark.py - Analisis Sensitivitas & Pengujian Skala Solver CSP (Small vs Large Scale)
Fakultas Informatika dan Teknik Elektro - Institut Teknologi Del
Mata Kuliah: 10S3001 - Artificial Intelligence

Script ini menguji performa modul solver.py pada dua studi kasus keputusan bisnis:
1. Penjadwalan Shift Staf Enterprise / Rumah Sakit
2. Alokasi Ruang Fasilitas Logistik / Gudang Multi-Zona

Mengukur: Waktu Eksekusi (detik), Jumlah Backtrack, Revisi AC-3, dan Evaluasi Batasan.
Menghasilkan Grafik Analisis Sensitivitas ('sensitivity_analysis.png').
"""

import time
import matplotlib.pyplot as plt
import pandas as pd
from typing import Dict, List, Any

from solver import backtrack_search, ac3, CSPSolverMetrics
from business_problem import StaffShiftSchedulingProblem, LogisticsAllocationProblem


def run_staff_scheduling_benchmarks() -> List[Dict[str, Any]]:
    print("=" * 70)
    print(" BENCHMARK 1: PENJADWALAN SHIFT STAF ENTERPRISE")
    print("=" * 70)

    scales = [
        {"name": "Sangat Kecil", "staff": 3, "days": 2, "cap": {"Pagi": 1, "Siang": 1, "Malam": 1}},
        {"name": "Kecil", "staff": 4, "days": 2, "cap": {"Pagi": 1, "Siang": 1, "Malam": 1}},
        {"name": "Sedang", "staff": 4, "days": 3, "cap": {"Pagi": 1, "Siang": 1, "Malam": 1}},
        {"name": "Besar", "staff": 5, "days": 3, "cap": {"Pagi": 1, "Siang": 1, "Malam": 1}},
    ]

    results = []
    for sc in scales:
        num_vars = sc["staff"] * sc["days"]
        prob = StaffShiftSchedulingProblem(
            num_staff=sc["staff"],
            num_days=sc["days"],
            senior_staff_ids=[1, 2],
            unavailability={(1, 1): ["Malam"]},
            conflict_pairs=[(1, 2)],
            shift_capacity=sc["cap"],
        )
        csp = prob.build_csp()

        sol, metrics = backtrack_search(
            csp, use_ac3_preprocess=True, use_mrv=True, use_lcv=True, use_fc=True
        )

        res = {
            "Domain Case": "Penjadwalan Shift Staf",
            "Skala": sc["name"],
            "Variabel (N)": num_vars,
            "Solved": metrics.solved,
            "Waktu (s)": round(metrics.runtime_sec, 5),
            "Backtracks": metrics.backtracks,
            "Assignments": metrics.assignments,
            "AC3 Revisions": metrics.ac3_revisions,
            "Constraint Checks": metrics.constraint_checks,
        }
        results.append(res)
        print(f"[{sc['name']:<12}] N={num_vars:<3} | Solved={str(metrics.solved):<5} | "
              f"Time={metrics.runtime_sec:.4f}s | Backtracks={metrics.backtracks:<4} | "
              f"Constraint Checks={metrics.constraint_checks}")

    return results


def run_logistics_benchmarks() -> List[Dict[str, Any]]:
    print("\n" + "=" * 70)
    print(" BENCHMARK 2: ALOKASI RUANG FASILITAS LOGISTIK")
    print("=" * 70)

    scales = [
        {"name": "Kecil", "items": 8, "zones": 3, "cap": 4},
        {"name": "Sedang", "items": 16, "zones": 4, "cap": 5},
        {"name": "Besar", "items": 25, "zones": 5, "cap": 6},
        {"name": "Sangat Besar", "items": 40, "zones": 6, "cap": 8},
    ]

    results = []
    for sc in scales:
        item_list = []
        zones = [f"Zone_{chr(65+i)}" for i in range(sc["zones"])]
        zone_caps = {z: sc["cap"] for z in zones}

        for idx in range(1, sc["items"] + 1):
            req = zones[0] if idx % 4 == 0 else None
            item_list.append({"id": f"Cargo_{idx}", "required_zone": req})

        incompat = [(f"Cargo_{i}", f"Cargo_{i+1}") for i in range(1, sc["items"], 3)]

        prob = LogisticsAllocationProblem(item_list, zones, zone_caps, incompat)
        csp = prob.build_csp()

        sol, metrics = backtrack_search(
            csp, use_ac3_preprocess=True, use_mrv=True, use_lcv=True, use_fc=True
        )

        res = {
            "Domain Case": "Alokasi Ruang Logistik",
            "Skala": sc["name"],
            "Variabel (N)": sc["items"],
            "Solved": metrics.solved,
            "Waktu (s)": round(metrics.runtime_sec, 5),
            "Backtracks": metrics.backtracks,
            "Assignments": metrics.assignments,
            "AC3 Revisions": metrics.ac3_revisions,
            "Constraint Checks": metrics.constraint_checks,
        }
        results.append(res)
        print(f"[{sc['name']:<12}] N={sc['items']:<3} | Solved={str(metrics.solved):<5} | "
              f"Time={metrics.runtime_sec:.4f}s | Backtracks={metrics.backtracks:<4} | "
              f"Constraint Checks={metrics.constraint_checks}")

    return results


def plot_sensitivity_analysis(staff_res: List[Dict[str, Any]], log_res: List[Dict[str, Any]]):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Analisis Sensitivitas Modul CSP Solver (AC-3 & Backtracking MRV/LCV/FC)", fontsize=14, fontweight="bold")

    # Plot 1: Staff Scheduling - Runtime vs N
    df_staff = pd.DataFrame(staff_res)
    axes[0, 0].plot(df_staff["Variabel (N)"], df_staff["Waktu (s)"], marker="o", color="navy", linewidth=2)
    axes[0, 0].set_title("Shift Staf: Waktu Eksekusi vs Ukuran Masalah (N)")
    axes[0, 0].set_xlabel("Jumlah Variabel N (Staf x Hari)")
    axes[0, 0].set_ylabel("Waktu Eksekusi (detik)")
    axes[0, 0].grid(True, linestyle="--", alpha=0.6)

    # Plot 2: Staff Scheduling - Backtracks vs N
    axes[0, 1].bar(df_staff["Skala"], df_staff["Backtracks"], color="teal", alpha=0.85)
    axes[0, 1].set_title("Shift Staf: Jumlah Backtrack vs Skala")
    axes[0, 1].set_xlabel("Skala Masalah")
    axes[0, 1].set_ylabel("Jumlah Backtrack")
    axes[0, 1].grid(True, linestyle="--", alpha=0.6)

    # Plot 3: Logistics - Runtime vs N
    df_log = pd.DataFrame(log_res)
    axes[1, 0].plot(df_log["Variabel (N)"], df_log["Waktu (s)"], marker="s", color="darkred", linewidth=2)
    axes[1, 0].set_title("Alokasi Logistik: Waktu Eksekusi vs Ukuran Masalah (N)")
    axes[1, 0].set_xlabel("Jumlah Barang (Variabel N)")
    axes[1, 0].set_ylabel("Waktu Eksekusi (detik)")
    axes[1, 0].grid(True, linestyle="--", alpha=0.6)

    # Plot 4: Logistics - Backtracks vs N
    axes[1, 1].bar(df_log["Skala"], df_log["Backtracks"], color="coral", alpha=0.85)
    axes[1, 1].set_title("Alokasi Logistik: Jumlah Backtrack vs Skala")
    axes[1, 1].set_xlabel("Skala Masalah")
    axes[1, 1].set_ylabel("Jumlah Backtrack")
    axes[1, 1].grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    output_img = "sensitivity_analysis.png"
    plt.savefig(output_img, dpi=300)
    print(f"\n[INFO] Grafik Analisis Sensitivitas berhasil disimpan ke: '{output_img}'")


if __name__ == "__main__":
    staff_results = run_staff_scheduling_benchmarks()
    logistics_results = run_logistics_benchmarks()
    plot_sensitivity_analysis(staff_results, logistics_results)
