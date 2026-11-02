# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi data demo
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Isi data demo untuk `manage.py seed_demo_data`.

Berkas berawalan `_` supaya Django tidak membacanya sebagai command. Semua nama
orang dan perusahaan di sini rekaan. Domain email `paradise.test` (TLD `.test`
dicadangkan RFC 2606), jadi tidak ada email yang bisa nyasar ke orang sungguhan,
dan `--reset` cukup menyapu domain ini.
"""

DEMO_DOMAIN = "paradise.test"
DEMO_PASSWORD = "P@ssw0rd"
SUMBER_DEMO = "seed-demo"

# (kode, nama, [(kode departemen, nama departemen), ...])
ORGANISASI = [
    (
        "SLS",
        "Sales & Marketing",
        [("SLS-DOM", "Penjualan Domestik"), ("SLS-EXP", "Penjualan Ekspor"), ("MKT", "Marketing dan Promosi")],
    ),
    (
        "OPS",
        "Operasional",
        [("PPIC", "Perencanaan Produksi"), ("WH", "Gudang dan Logistik"), ("QC", "Quality Control")],
    ),
    ("FIN", "Finance & Accounting", [("ACC", "Akuntansi"), ("TAX", "Pajak dan Treasury")]),
    ("HRGA", "Human Resources & GA", [("HR", "Human Resources"), ("GA", "General Affair")]),
    ("IT", "Teknologi Informasi", [("IT-DEV", "Pengembangan Aplikasi"), ("IT-INF", "Infrastruktur dan Helpdesk")]),
]

# (nama lengkap, jabatan di kartu)
DIREKTUR = [
    ("Hendra Gunawan", "Direktur Utama"),
    ("Linda Kusuma", "Direktur Operasional"),
]

# kode divisi -> nama manager
MANAGER = {
    "SLS": "Bambang Prasetyo",
    "OPS": "Agus Santoso",
    "FIN": "Ratna Wulandari",
    "HRGA": "Dewi Lestari",
    "IT": "Fajar Nugroho",
}

# nama supervisor -> departemen yang dia pegang. Satu supervisor memegang dua
# departemen (ACC + TAX) supaya kasus multi-penempatan ikut terlihat di God Mode.
SUPERVISOR = {
    "Rudi Hartono": ["SLS-DOM"],
    "Maya Sari": ["SLS-EXP"],
    "Andreas Wijaya": ["MKT"],
    "Yusuf Hidayat": ["PPIC"],
    "Slamet Riyadi": ["WH"],
    "Nurul Aini": ["QC"],
    "Indah Permata": ["ACC", "TAX"],
    "Siti Rahmawati": ["HR"],
    "Joko Susilo": ["GA"],
    "Kevin Tanoto": ["IT-DEV"],
    "Arif Setiawan": ["IT-INF"],
}

# departemen -> staf
STAF = {
    "SLS-DOM": ["Dimas Saputra", "Putri Ayu", "Rizky Ramadhan", "Anisa Fitri"],
    "SLS-EXP": ["Michael Halim", "Citra Dewi", "Bagus Pratama"],
    "MKT": ["Nadia Paramitha", "Reza Fahlevi", "Tania Oktaviani"],
    "PPIC": ["Eko Wahyudi", "Lia Marlina", "Hadi Purnomo"],
    "WH": ["Teguh Supriadi", "Wahyu Kurniawan", "Sri Handayani", "Dedi Mulyadi"],
    "QC": ["Fitri Handayani", "Galih Saputro", "Yuni Astuti"],
    "ACC": ["Melati Puspita", "Hendro Wibowo", "Clara Anggraini"],
    "TAX": ["Stefanus Lim", "Rina Marliana"],
    "HR": ["Ayu Lestari", "Bima Aditya", "Sarah Natalia"],
    "GA": ["Udin Syamsudin", "Rahmat Hidayat", "Lestari Wulan"],
    "IT-DEV": ["Gilang Ramadhan", "Vania Kristanti", "Aditya Nugraha", "Kenny Gunadi"],
    "IT-INF": ["Ilham Maulana", "Yosua Pardede", "Dinda Safitri"],
}

LABEL = [
    ("Urgent", "#e5484d"),
    ("Klien", "#3e63dd"),
    ("Internal", "#8e8c99"),
    ("Dokumen", "#f5a524"),
    ("Perbaikan", "#12a594"),
]

# departemen -> [nama modul]
MODUL = {
    "SLS-DOM": ["Akun Distributor Jawa", "Target Q4 2026", "Tender Pemerintah"],
    "SLS-EXP": ["Pasar ASEAN", "Dokumen Ekspor", "Pameran Dagang 2026"],
    "MKT": ["Kampanye Akhir Tahun", "Konten Digital", "Event & Sponsorship"],
    "PPIC": ["Jadwal Produksi November", "Kebutuhan Material", "Kapasitas Mesin"],
    "WH": ["Stock Opname Q4", "Pengiriman Rutin", "Penataan Gudang B"],
    "QC": ["Audit ISO 9001", "Inspeksi Incoming", "Keluhan Pelanggan"],
    "ACC": ["Tutup Buku Oktober", "Audit Eksternal 2026", "Rekonsiliasi Bank"],
    "TAX": ["SPT Masa", "Arus Kas Mingguan", "Restitusi PPN"],
    "HR": ["Rekrutmen Q4", "Penilaian Kinerja 2026", "Pelatihan Karyawan"],
    "GA": ["Renovasi Kantor Lt. 3", "Armada Kendaraan", "Pengadaan ATK"],
    "IT-DEV": ["Portal Pelanggan v2", "Integrasi ERP", "Aplikasi Mobile Sales"],
    "IT-INF": ["Migrasi Server", "Keamanan Jaringan", "Helpdesk Rutin"],
}

# departemen -> [(judul induk, [judul sub-tugas])]
TUGAS = {
    "SLS-DOM": [
        (
            "Kunjungan distributor wilayah Jawa Timur",
            ["Siapkan materi presentasi produk", "Atur jadwal kunjungan Surabaya", "Laporan hasil kunjungan"],
        ),
        ("Penawaran harga proyek RSUD Sidoarjo", ["Hitung HPP dan margin", "Susun dokumen penawaran"]),
        ("Follow-up piutang distributor jatuh tempo", ["Rekap invoice lewat 60 hari", "Telepon distributor prioritas"]),
        ("Rekap penjualan Oktober per wilayah", []),
        ("Onboarding distributor baru Semarang", ["Verifikasi dokumen legal", "Training produk untuk tim distributor"]),
        ("Revisi price list 2027", ["Bandingkan harga kompetitor"]),
        ("Persiapan tender e-katalog LKPP", ["Lengkapi dokumen kualifikasi", "Unggah katalog produk"]),
    ],
    "SLS-EXP": [
        ("Penawaran untuk buyer Malaysia", ["Hitung harga FOB", "Kirim sampel produk"]),
        ("Pengurusan Certificate of Origin", ["Ajukan form E ke Kemendag"]),
        (
            "Persiapan Trade Expo Indonesia",
            ["Desain booth", "Cetak katalog bahasa Inggris", "Daftar calon buyer yang diundang"],
        ),
        ("Negosiasi kontrak distributor Vietnam", ["Review draf kontrak dengan legal"]),
        ("Laporan realisasi ekspor Q3", []),
        ("Koordinasi jadwal kapal dengan forwarder", ["Booking kontainer 40ft"]),
    ],
    "MKT": [
        ("Kampanye promo akhir tahun", ["Konsep visual kampanye", "Jadwal posting media sosial", "Brief untuk agensi"]),
        ("Update company profile", ["Foto ulang produk", "Revisi copywriting"]),
        ("Laporan performa iklan digital Oktober", []),
        ("Sponsorship seminar industri", ["Negosiasi paket sponsor", "Siapkan merchandise"]),
        ("Riset kepuasan pelanggan 2026", ["Susun kuesioner", "Olah hasil survei"]),
        ("Redesain halaman produk di website", ["Wireframe halaman", "Koordinasi dengan tim IT"]),
    ],
    "PPIC": [
        ("Susun jadwal produksi minggu 45", ["Cek ketersediaan bahan baku", "Konfirmasi kapasitas lini 2"]),
        ("Hitung kebutuhan material Desember", ["Update BOM produk baru", "Kirim PR ke purchasing"]),
        ("Analisis downtime mesin Oktober", []),
        ("Percepatan order PT Sinar Abadi", ["Negosiasi lembur shift malam", "Update tanggal kirim ke sales"]),
        ("Evaluasi akurasi forecast Q3", []),
        ("Rencana perawatan mesin tahunan", ["Koordinasi jadwal dengan maintenance"]),
    ],
    "WH": [
        (
            "Stock opname gudang bahan baku",
            ["Siapkan form hitung fisik", "Rekonsiliasi selisih stok", "Laporan hasil opname"],
        ),
        ("Penataan ulang rak gudang B", ["Pasang label lokasi rak", "Pindahkan barang slow moving"]),
        ("Jadwal pengiriman mingguan area Jabodetabek", []),
        ("Pemusnahan barang kedaluwarsa", ["Buat berita acara pemusnahan"]),
        ("Evaluasi vendor ekspedisi", ["Rekap keterlambatan pengiriman"]),
        ("Pengecekan forklift berkala", []),
    ],
    "QC": [
        (
            "Persiapan audit surveillance ISO 9001",
            ["Update dokumen SOP", "Internal audit pra-surveillance", "Tindak lanjut temuan audit lalu"],
        ),
        ("Inspeksi bahan baku kiriman vendor baru", ["Uji lab sampel", "Buat laporan inspeksi"]),
        ("Investigasi keluhan pelanggan batch 2610", ["Analisis akar masalah", "Kirim laporan 8D ke pelanggan"]),
        ("Kalibrasi alat ukur tahunan", []),
        ("Rekap reject rate Oktober", []),
        ("Training QC untuk operator baru", ["Siapkan modul training"]),
    ],
    "ACC": [
        (
            "Tutup buku Oktober 2026",
            ["Jurnal penyesuaian akhir bulan", "Rekonsiliasi akun piutang", "Laporan keuangan bulanan"],
        ),
        ("Persiapan audit eksternal", ["Kumpulkan dokumen pendukung", "Jawab daftar permintaan auditor"]),
        ("Rekonsiliasi rekening bank BCA dan Mandiri", []),
        ("Verifikasi invoice vendor masuk", ["Cocokkan PO dengan invoice"]),
        ("Penyusutan aset tetap Q4", []),
    ],
    "TAX": [
        ("Lapor SPT Masa PPN Oktober", ["Rekap faktur keluaran", "Rekap faktur masukan"]),
        ("Proyeksi arus kas November", []),
        ("Pengajuan restitusi PPN", ["Lengkapi dokumen pendukung restitusi"]),
        ("Pembayaran PPh 21 karyawan", []),
        ("Perpanjangan fasilitas kredit bank", ["Siapkan laporan keuangan untuk bank"]),
    ],
    "HR": [
        (
            "Rekrutmen staf IT dan sales",
            ["Pasang lowongan di job portal", "Seleksi CV tahap awal", "Jadwalkan interview user"],
        ),
        ("Penilaian kinerja tahunan 2026", ["Sebar form self-assessment", "Rekap nilai per departemen"]),
        ("Pelatihan K3 untuk karyawan produksi", ["Hubungi vendor pelatihan"]),
        ("Update peraturan perusahaan", []),
        ("Onboarding karyawan baru November", ["Siapkan kit karyawan baru", "Atur sesi orientasi"]),
        ("Rekap lembur dan absensi Oktober", []),
    ],
    "GA": [
        ("Renovasi ruang meeting lantai 3", ["Minta penawaran dari kontraktor", "Pilih desain interior"]),
        ("Servis berkala kendaraan operasional", ["Jadwalkan servis mobil box"]),
        ("Pengadaan ATK kuartal IV", []),
        ("Perpanjangan kontrak sewa gudang", ["Negosiasi harga sewa"]),
        ("Perbaikan AC ruang server", []),
        ("Pengaturan tamu kunjungan pabrik", []),
    ],
    "IT-DEV": [
        (
            "Portal pelanggan v2: modul pelacakan order",
            ["Desain API status order", "Halaman pelacakan di frontend", "Uji coba dengan 3 pelanggan"],
        ),
        ("Integrasi ERP dengan aplikasi gudang", ["Mapping data item master", "Sinkron stok otomatis"]),
        ("Perbaikan bug laporan penjualan ganda", []),
        (
            "Aplikasi mobile sales: fitur check-in kunjungan",
            ["Ambil lokasi GPS saat check-in", "Laporan kunjungan harian"],
        ),
        ("Dokumentasi API internal", []),
        ("Upgrade framework backend ke versi terbaru", ["Uji regresi modul keuangan"]),
    ],
    "IT-INF": [
        (
            "Migrasi server file ke NAS baru",
            ["Backup data lama", "Atur hak akses folder", "Uji akses dari tiap divisi"],
        ),
        ("Pembaruan firewall kantor pusat", ["Review rule akses VPN"]),
        ("Penggantian laptop karyawan tahap 2", ["Inventaris laptop yang diganti", "Instal ulang dan serah terima"]),
        ("Audit lisensi software", []),
        ("Perbaikan jaringan Wi-Fi gudang", []),
        ("Prosedur backup harian database", ["Uji restore backup"]),
    ],
}

KOMENTAR = [
    "Sudah saya mulai, target selesai sesuai tenggat.",
    "Mohon dicek dulu draft-nya, saya lampirkan di folder bersama.",
    "Ada kendala data dari divisi lain, sedang saya follow-up.",
    "Oke, lanjutkan. Kabari kalau butuh bantuan.",
    "Update: progres sekitar 60%, sisa menunggu konfirmasi vendor.",
    "Sudah dikoordinasikan dengan pihak terkait, tinggal finalisasi.",
    "Tolong prioritaskan ini minggu ini ya.",
    "Revisi sudah saya kerjakan sesuai masukan kemarin.",
    "Saya jadwalkan meeting singkat besok pagi untuk membahas ini.",
    "Dokumen pendukung sudah lengkap.",
]

ALASAN_TOLAK = [
    "Laporan belum memuat lampiran bukti, tolong dilengkapi dulu.",
    "Angkanya belum cocok dengan data sistem, cek ulang ya.",
    "Masih ada poin dari meeting yang belum dikerjakan.",
]

# (departemen asal, departemen tujuan, judul, prioritas, catatan)
PERMINTAAN_LINTAS = [
    (
        "SLS-DOM",
        "PPIC",
        "Percepatan produksi order distributor Surabaya",
        "high",
        "Distributor minta kirim sebelum tanggal 20.",
    ),
    (
        "HR",
        "IT-INF",
        "Siapkan akun email dan laptop untuk 4 karyawan baru",
        "medium",
        "Mulai kerja tanggal 10 November.",
    ),
    ("MKT", "IT-DEV", "Tambah banner promo akhir tahun di website", "low", ""),
    ("QC", "WH", "Karantina batch 2610 di gudang", "urgent", "Menunggu hasil investigasi keluhan pelanggan."),
    ("ACC", "SLS-EXP", "Kirim salinan invoice ekspor Oktober", "medium", "Untuk rekonsiliasi tutup buku."),
    ("GA", "TAX", "Pencairan dana renovasi ruang meeting", "high", ""),
]

# (judul, isi HTML) per project; `{dep}` diganti nama departemen.
PAGE = [
    (
        "SOP {dep}",
        "<h2>Tujuan</h2><p>Panduan kerja harian tim {dep} supaya semua orang memakai cara yang sama.</p>"
        "<h2>Alur kerja</h2><ol><li><p>Tugas baru dibuat atasan atau diajukan staf.</p></li>"
        "<li><p>Staf menggeser progres ke In Progress saat mulai mengerjakan.</p></li>"
        "<li><p>Saat selesai, staf menggeser ke Done dan menunggu persetujuan atasan.</p></li></ol>"
        "<h2>Kontak</h2><p>Pertanyaan soal SOP ini ke supervisor {dep}.</p>",
    ),
    (
        "Notulen rapat mingguan {dep}",
        "<h2>Agenda</h2><ul><li><p>Review progres tugas minggu lalu</p></li>"
        "<li><p>Kendala dan bantuan yang dibutuhkan</p></li><li><p>Prioritas minggu ini</p></li></ul>"
        "<h2>Keputusan</h2><ul><li><p>Tugas yang lewat tenggat dibahas satu per satu.</p></li>"
        "<li><p>Laporan mingguan dikirim paling lambat Jumat sore.</p></li></ul>",
    ),
]

# (nama view, filter lama). Filter rich-nya dihasilkan converter yang sama dengan API.
VIEW = [
    ("Prioritas tinggi", {"priority": ["urgent", "high"]}),
    ("Sedang dikerjakan", {"state_group": ["started"]}),
]

# Tugas yang melibatkan Super Admin pemilik instance (akun sungguhan, bukan demo),
# supaya akun yang paling sering membuka aplikasi ikut terlihat di data demo.
# `{dep}` diganti nama departemen.
ADMIN_MEMBERI = "Lengkapi data tugas {dep} di Paradise Task Tracker"
ADMIN_DIBERI = ("Atur ulang hak akses {dep} di sistem", ["Cek daftar anggota project {dep}"])
ADMIN_KOMENTAR = [
    "Sudah saya cek dari sisi sistem, aman.",
    "Kalau butuh akses tambahan, ajukan lewat saya ya.",
    "Mohon lampirkan bukti di tugas ini supaya mudah diaudit.",
]
ADMIN_PAGE = (
    "Catatan IT untuk {dep}",
    "<h2>Akses & akun</h2><p>Permintaan akun baru atau reset password untuk tim {dep} diajukan "
    "ke tim IT lewat tugas di project ini.</p><h2>Kontak</h2><p>Hubungi admin sistem untuk kendala akses.</p>",
)
