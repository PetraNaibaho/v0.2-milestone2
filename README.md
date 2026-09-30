# Modul Pemecahan Batasan Keputusan Bisnis (CSP Solver dengan AC-3 & Backtracking)

**Mata Kuliah:** 10S3001 - Artificial Intelligence (+P)  
**Institusi:** Institut Teknologi Del - Fakultas Informatika dan Teknik Elektro  
**Program Studi:** Sarjana Sistem Informasi  
**Tugas:** Milestone 2 (Tugas 2 - W04)  
**Tag Rilis:** `v0.2-milestone2`  

---

## 📌 Ringkasan Proyek

Proyek ini mengimplementasikan **Modul Komputasi Cerdas Pemecah Batasan Keputusan Bisnis** berbasis **Constraint Satisfaction Problems (CSP)**. Modul dirancang secara modular (`solver.py`) dan dilengkapi dengan teknik inferensi propagasi batasan **Arc Consistency 3 (AC-3)** serta algoritma **Backtracking Search** yang diakselerasi dengan heuristik:
- **MRV (Minimum Remaining Values)** + *Degree Heuristic* (Pemutus Seri)
- **LCV (Least Constraining Value)**
- **Forward Checking (FC)** / *Early Pruning*

Modul ini memetakan dua domain keputusan bisnis nyata yang terikat batasan ketat:
1. **Penjadwalan Shift Staf Enterprise / Rumah Sakit (*Enterprise & Healthcare Staff Shift Scheduling*)**
2. **Alokasi Ruang Fasilitas Logistik Gudang Multi-Zona (*Logistics Multi-Zone Space Allocation*)**

---

## 🧮 Pemodelan Matematis Formal $\langle X, D, C \rangle$

### 1. Studi Kasus 1: Penjadwalan Shift Staf Enterprise ($SSSP$)

#### A. Himpunan Variabel ($X$)
Variabel keputusan didefinisikan sebagai penugasan shift untuk Staf $i$ pada Hari $t$:
$$X = \{ X_{i, t} \mid i \in \{1, 2, \dots, N_{staf}\}, \, t \in \{1, 2, \dots, N_{hari}\} \}$$
Total variabel: $N = N_{staf} \times N_{hari}$.

#### B. Domain Nilai ($D$)
Untuk setiap variabel $X_{i, t}$, domain nilai legal didefinisikan sebagai:
$$D(X_{i, t}) = \{ \text{'Pagi' (P)}, \, \text{'Siang' (S)}, \, \text{'Malam' (M)}, \, \text{'Libur' (L)} \}$$

#### C. Himpunan Batasan ($C$)
1. **Unary Constraints (Arity 1)**:
   - *Batasan Ketersediaan (Cuti)*: Jika Staf $i$ tidak tersedia pada Hari $t$ untuk shift $s$, maka $s \notin D(X_{i, t})$.
   - *Batasan Kualifikasi Peran*: Staf level Junior ($i \notin \text{Senior}$) dilarang mengambil shift Malam:
     $$\forall i \notin \text{Senior}, \, \forall t: \, \text{'Malam'} \notin D(X_{i, t})$$
2. **Binary Constraints (Arity 2)**:
   - *Regula Istirahat Berturut-turut (Rest Period)*: Staf yang bekerja shift Malam pada Hari $t$ dilarang bekerja shift Pagi pada Hari $t+1$ (agar istirahat $\ge 12$ jam):
     $$C_{rest}(X_{i, t}, X_{i, t+1}): \, \neg (X_{i, t} = \text{'Malam'} \land X_{i, t+1} = \text{'Pagi'})$$
   - *Konflik Pasangan Staf (Conflict Exclusion)*: Pasangan staf $(i_1, i_2) \in \text{Konflik}$ dilarang berada di shift Malam bersamaan pada hari yang sama:
     $$C_{conflict}(X_{i_1, t}, X_{i_2, t}): \, \neg (X_{i_1, t} = \text{'Malam'} \land X_{i_2, t} = \text{'Malam'})$$
3. **Global / Higher-Order Constraints (Arity $k$)**:
   - *Kuota Minimal Shift per Hari*: Untuk setiap hari $t$ dan jenis shift $s \in \{\text{'Pagi'}, \text{'Siang'}, \text{'Malam'}\}$, jumlah staf yang bertugas harus memenuhi kuota minimal $K_s$:
     $$\sum_{i=1}^{N_{staf}} \mathbb{I}(X_{i, t} = s) \ge K_s$$
   - *Kehadiran Senior*: Shift Malam pada setiap hari $t$ wajib dihadiri minimal 1 staf senior.

---

### 2. Studi Kasus 2: Alokasi Ruang Fasilitas Logistik ($LSA$)

#### A. Variabel ($X$) & Domain ($D$)
- **Variabel $X$**: $X_i$ menyatakan zona penempatan untuk barang/palet logistik $i \in \{1, \dots, N_{barang}\}$.
- **Domain $D$**: $D(X_i) = \{ \text{'Zone\_Cold'}, \text{'Zone\_Hazardous'}, \text{'Zone\_Dry'}, \text{'Zone\_General'} \}$.

#### B. Batasan ($C$)
- **Unary**: Barang vaksin/biomedis wajib dialokasikan ke `Zone_Cold`.
- **Binary**: Bahan kimia berisiko bereaksi (Oksidator vs Flambel) dilarang ditempatkan pada zona yang sama (*Chemical Hazard Isolation*).
- **Global**: Jumlah total barang pada zona $z$ tidak boleh melebihi kapasitas maksimal zona $\text{Cap}(z)$.

---

## 🏗️ Struktur & Arsitektur Modul

```text
v0.2-milestone2/
├── solver.py               # Engine CSP Generik (AC-3 & Backtracking MRV/LCV/FC)
├── business_problem.py     # Generator Masalah Bisnis (Shift Scheduling & Logistics)
├── test_solver.py          # Modul Pengujian Otomatis & Case Ekstrem (Edge Cases)
├── benchmark.py            # Script Analisis Sensitivitas & Benchmark Performa
├── main.py                 # CLI Entrypoint Demonstrasi Interaktif
├── sensitivity_analysis.png# Grafik Hasil Analisis Sensitivitas Konvergensi
└── README.md               # Dokumentasi Laporan Formal & Panduan Repositori
```

---

## ⚡ Fitur Utama Algoritma

1. **Arc Consistency 3 (AC-3)**: Memangkas domain inkonsisten dengan mengevaluasi busur berarah $(X_i, X_j)$ via prosedur `Revise(Xi, Xj)` sebelum pencarian.
2. **Minimum Remaining Values (MRV)**: Memilih variabel dengan sisa domain terkecil (*Fail-First Principle*) dengan *Degree Heuristic* sebagai pemutus seri.
3. **Least Constraining Value (LCV)**: Mengurutkan opsi nilai domain berdasarkan dampak pemangkasan minimum terhadap domain tetangga (*Fail-Last Principle*).
4. **Forward Checking (FC)**: Secara dinamis memangkas domain variabel tetangga yang belum terisi setiap kali suatu variabel diberi nilai.

---

## 🧪 Hasil Pengujian & Analisis Sensitivitas

### 1. Pengujian Otomatis (`test_solver.py`)
Pengujian mencakup kasus normal dan **kasus ekstrem (edge cases)**:
- **`test_ac3_domain_pruning`**: Memverifikasi pemangkasan domain oleh AC-3 pada relasi pertidaksamaan.
- **`test_edge_case_unsolvable_overconstrained`**: Solver mendeteksi kontradiksi/over-constrained dan mengembalikan `None` secara langsung.
- **`test_edge_case_empty_domain`**: Memastikan solver menangani domain awal kosong akibat batasan unary.
- **`test_edge_case_tightly_constrained_single_solution`**: Solver menemukan solusi unik tanpa pencarian berlebih.
- **`test_heuristics_efficiency_comparison`**: Pengujian perbandingan membuktikan heuristik MRV/FC secara drastis mengurangi jumlah backtrack dibanding naive backtracking.

### 2. Benchmark Performa & Konvergensi (`benchmark.py`)

| Domain Studi Kasus | Skala Masalah | Jumlah Variabel ($N$) | Solved | Waktu Eksekusi (s) | Backtracks | Constraint Checks |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Shift Staf** | Sangat Kecil | 6 | `True` | 0.0010 s | 7 | 109 |
| **Shift Staf** | Kecil | 8 | `True` | 0.0010 s | 7 | 139 |
| **Shift Staf** | Sedang | 12 | `True` | 0.0026 s | 24 | 311 |
| **Shift Staf** | Besar | 15 | `True` | 0.0036 s | 24 | 370 |
| **Alokasi Logistik** | Kecil | 8 | `True` | 0.0004 s | 0 | 95 |
| **Alokasi Logistik** | Sedang | 16 | `True` | 0.0014 s | 0 | 495 |
| **Alokasi Logistik** | Besar | 25 | `True` | 0.0046 s | 0 | 1485 |

> Grafik hasil analisis sensitivitas dapat dilihat pada file `sensitivity_analysis.png`.

---

## 🚀 Panduan Menjalankan Kode

### 1. Menjalankan Demo Keputusan Bisnis
```bash
python main.py --case all
```
Atau pilih spesifik kasus:
```bash
python main.py --case staff
python main.py --case logistics
```

### 2. Menjalankan Suite Pengujian Otomatis
```bash
python test_solver.py
```

### 3. Menjalankan Analisis Sensitivitas & Regenerasi Grafik
```bash
python main.py --benchmark
```

---

## 🏷️ Tag Release Git

Repositori ini telah ditandai dengan tag rilis:
```bash
git tag v0.2-milestone2
```