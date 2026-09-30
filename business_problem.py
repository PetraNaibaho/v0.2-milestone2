"""
business_problem.py - Model Pemodelan Masalah Bisnis Terikat Batasan (CSP)
Fakultas Informatika dan Teknik Elektro - Institut Teknologi Del

Modul ini memetakan domain keputusan bisnis nyata (Penjadwalan Shift Staf & Alokasi Ruang Logistik)
ke dalam formulasi matematis CSP <X, D, C>.
"""

from typing import Dict, List, Tuple, Any, Optional
from solver import CSP, UnaryConstraint, BinaryConstraint, GlobalConstraint


class StaffShiftSchedulingProblem:
    """
    Pemodelan CSP untuk Penjadwalan Shift Staf Enterprise / Rumah Sakit.

    Variabel X_{i, t}: Penugasan shift Staf i pada Hari t.
    Domain D_{i, t}: {'Pagi', 'Siang', 'Malam', 'Libur'}.
    Batasan C:
      - Unary: Ketersediaan staf (cuti), batasan kualifikasi/peran (Junior tidak boleh shift Malam).
      - Binary: Regula Istirahat (Shift Malam di hari t melarang shift Pagi di hari t+1).
      - Binary: Konflik Pasangan Staf (Dua spesialis tidak boleh shift Malam bersamaan).
      - Global: Kuota minimal staf per shift (Pagi >= K_p, Siang >= K_s, Malam >= K_m).
      - Global: Kehadiran staf senior pada shift Malam.
    """

    def __init__(
        self,
        num_staff: int = 5,
        num_days: int = 3,
        senior_staff_ids: Optional[List[int]] = None,
        unavailability: Optional[Dict[Tuple[int, int], List[str]]] = None,
        conflict_pairs: Optional[List[Tuple[int, int]]] = None,
        shift_capacity: Optional[Dict[str, int]] = None,
    ):
        self.num_staff = num_staff
        self.num_days = num_days
        self.staff_ids = list(range(1, num_staff + 1))
        self.days = list(range(1, num_days + 1))
        self.shifts = ["Pagi", "Siang", "Malam", "Libur"]

        self.senior_staff_ids = (
            senior_staff_ids if senior_staff_ids is not None else [1, 2]
        )
        self.unavailability = unavailability if unavailability is not None else {}
        self.conflict_pairs = conflict_pairs if conflict_pairs is not None else []
        self.shift_capacity = (
            shift_capacity
            if shift_capacity is not None
            else {"Pagi": 1, "Siang": 1, "Malam": 1}
        )

    def build_csp(self) -> CSP:
        # 1. Definisi Variabel X
        variables = []
        domains = {}
        for s_id in self.staff_ids:
            for day in self.days:
                var = (f"Staff_{s_id}", f"Day_{day}")
                variables.append(var)
                domains[var] = list(self.shifts)

        csp = CSP(variables, domains)

        # 2. Batasan Unary: Ketersediaan & Kualifikasi
        for (s_id, day), prohibited_shifts in self.unavailability.items():
            var = (f"Staff_{s_id}", f"Day_{day}")
            if var in csp.domains:
                fn = lambda val, ps=prohibited_shifts: val not in ps
                csp.add_constraint(
                    UnaryConstraint(var, fn, name=f"Unavailability_{var}")
                )

        # Junior staff constraint: Staff not in senior_staff_ids cannot take 'Malam'
        for s_id in self.staff_ids:
            if s_id not in self.senior_staff_ids:
                for day in self.days:
                    var = (f"Staff_{s_id}", f"Day_{day}")
                    fn = lambda val: val != "Malam"
                    csp.add_constraint(
                        UnaryConstraint(var, fn, name=f"JuniorNoNight_{var}")
                    )

        # 3. Batasan Biner: Regula Istirahat Berturut-turut (Rest Period Constraint)
        # Shift 'Malam' di Hari t melarang Shift 'Pagi' di Hari t+1
        for s_id in self.staff_ids:
            for day in range(1, self.num_days):
                var_today = (f"Staff_{s_id}", f"Day_{day}")
                var_tomorrow = (f"Staff_{s_id}", f"Day_{day+1}")

                def rest_period_fn(v_today, v_tomorrow):
                    if v_today == "Malam" and v_tomorrow == "Pagi":
                        return False
                    return True

                csp.add_constraint(
                    BinaryConstraint(
                        var_today,
                        var_tomorrow,
                        rest_period_fn,
                        name=f"RestPeriod_{s_id}_D{day}_D{day+1}",
                    )
                )

        # Batasan Biner: Konflik Pasangan Staf pada Shift Malam di hari yang sama
        for s1, s2 in self.conflict_pairs:
            for day in self.days:
                v1 = (f"Staff_{s1}", f"Day_{day}")
                v2 = (f"Staff_{s2}", f"Day_{day}")

                def conflict_fn(val1, val2):
                    if val1 == "Malam" and val2 == "Malam":
                        return False
                    return True

                csp.add_constraint(
                    BinaryConstraint(
                        v1,
                        v2,
                        conflict_fn,
                        name=f"Conflict_Staff{s1}_Staff{s2}_D{day}",
                    )
                )

        # 4. Batasan Global: Kuota Minimal Staf per Shift per Hari & Seniority Requirement
        for day in self.days:
            day_vars = [(f"Staff_{s_id}", f"Day_{day}") for s_id in self.staff_ids]

            def make_day_capacity_fn(d_vars=day_vars):
                def day_capacity_fn(assignment: Dict[Any, Any]) -> bool:
                    assigned_vars = [v for v in d_vars if v in assignment]
                    unassigned_count = len(d_vars) - len(assigned_vars)

                    counts = {"Pagi": 0, "Siang": 0, "Malam": 0, "Libur": 0}
                    night_staffs = []

                    for v in assigned_vars:
                        val = assignment[v]
                        counts[val] += 1
                        if val == "Malam":
                            s_id = int(v[0].split("_")[1])
                            night_staffs.append(s_id)

                    # Evaluasi Parsial: Apakah kuota minimal shift masih MUNGKIN tercapai?
                    for shift, min_req in self.shift_capacity.items():
                        max_possible = counts[shift] + unassigned_count
                        if max_possible < min_req:
                            return False  # Tidak mungkin mencapai kuota min

                    # Evaluasi Lengkap
                    if unassigned_count == 0:
                        # Check senior staff requirement for 'Malam' shift if night shift is required
                        if self.shift_capacity.get("Malam", 0) > 0 or night_staffs:
                            has_senior = any(
                                s_id in self.senior_staff_ids
                                for s_id in night_staffs
                            )
                            if night_staffs and not has_senior:
                                return False

                    return True

                return day_capacity_fn

            csp.add_constraint(
                GlobalConstraint(
                    day_vars,
                    make_day_capacity_fn(day_vars),
                    name=f"GlobalShiftCapacity_Day_{day}",
                )
            )

        return csp


class LogisticsAllocationProblem:
    """
    Pemodelan CSP untuk Alokasi Ruang Fasilitas Logistik / Gudang Multi-Zona.
    """

    def __init__(
        self,
        items: List[Dict[str, Any]],
        zones: List[str],
        zone_capacities: Dict[str, int],
        incompatible_item_pairs: List[Tuple[str, str]],
    ):
        self.items = items
        self.zones = zones
        self.zone_capacities = zone_capacities
        self.incompatible_item_pairs = incompatible_item_pairs

    def build_csp(self) -> CSP:
        variables = [item["id"] for item in self.items]
        domains = {item["id"]: list(self.zones) for item in self.items}

        csp = CSP(variables, domains)

        # 1. Unary Constraints: Temperature / Storage requirement
        for item in self.items:
            item_id = item["id"]
            req_zone = item.get("required_zone")
            if req_zone:
                fn = lambda val, rz=req_zone: val == rz
                csp.add_constraint(
                    UnaryConstraint(item_id, fn, name=f"RequiredZone_{item_id}")
                )

        # 2. Binary Constraints: Chemical / Hazard Isolation
        for item1, item2 in self.incompatible_item_pairs:
            if item1 in variables and item2 in variables:

                def isola_fn(val1, val2):
                    return val1 != val2

                csp.add_constraint(
                    BinaryConstraint(
                        item1,
                        item2,
                        isola_fn,
                        name=f"Incompatible_{item1}_{item2}",
                    )
                )

        # 3. Global Constraint: Zone capacity limits
        def zone_capacity_check(assignment: Dict[Any, Any]) -> bool:
            counts = {z: 0 for z in self.zones}
            for item_id, zone in assignment.items():
                counts[zone] += 1
                if counts[zone] > self.zone_capacities.get(zone, 999):
                    return False
            return True

        csp.add_constraint(
            GlobalConstraint(
                variables, zone_capacity_check, name="GlobalZoneCapacity"
            )
        )

        return csp
