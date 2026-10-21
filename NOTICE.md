# NOTICE, Paradise Task Tracker

**Paradise Task Tracker** adalah deployment internal kantor berbasis **Plane
Community Edition**.

- **Upstream:** https://github.com/makeplane/plane
- **Lisensi:** GNU AGPL-3.0 (lihat `LICENSE.txt`, tidak dimodifikasi)
- **Hak cipta kode aplikasi:** © Plane (makeplane) dan kontributornya.

## Yang ditambahkan oleh fork ini

Fork ini **tidak menulis ulang aplikasi Plane**, inti aplikasinya (work item,
cycle, module, view, project, editor kolaboratif) tetap milik upstream.

Di atasnya, fork ini menambahkan **delapan kemampuan yang tidak ada di
upstream**, dibangun dari nol: model database, migrasi, endpoint API, aturan
izin, sampai antarmukanya.

| #   | Kemampuan                                                                                                          | Jejak utama                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| 1   | **Time Tracking**, worklog per work item, izin edit-milik-sendiri                                                  | `IssueWorkLog`, `/work-logs/`                                                                                      |
| 2   | **Work Item Types & Custom Properties**, 6 jenis field, validasi bertipe di server                                 | `IssueType`, `IssueProperty`, `IssuePropertyOption`, `IssuePropertyValue`                                          |
| 3   | **Templates & Recurring Issues**, penjadwalan berulang via Celery beat                                             | `IssueTemplate`, `RecurringIssue`, `plane/bgtasks/recurring_issue_task.py`                                         |
| 4   | **Workspace Wiki Fase A**, semua tipe lampiran s/d 100 MB + node berkas di editor dengan pratinjau                 | `asset/v2.py`, `packages/editor/.../custom-file/`                                                                  |
| 5   | **Wiki Fase B, ACL per folder**, folder tingkat atas dimiliki divisi; ditegakkan di REST **dan** server kolaborasi | `WikiGovernedProject`, `WikiFolderAccess`, `utils/wiki_access.py`, `page/can_edit.py`, `apps/live/src/lib/auth.ts` |
| 6   | **Wiki Fase C, pohon halaman bertingkat**                                                                          | `page/base.py` (opt-in `?sub_pages=true`)                                                                          |
| 7   | **Dashboard Divisi + ekspor CSV laporan waktu**                                                                    | `workspace/paradise_dashboard.py`                                                                                  |
| 8   | **Initiatives**, sasaran workspace lintas divisi dengan rollup progres                                             | `Initiative`, `InitiativeProject`                                                                                  |

Plus **Audit Logs**: perekaman aktor pada model akses & konten, dengan API baca
khusus admin (`workspace/audit_log.py`), memakai `django-auditlog`, lihat tabel
library di bawah.

Ditambah lapisan operasional kantor:

- Konfigurasi & template environment untuk deployment kantor (`paradise/`)
- Dokumentasi deploy, keamanan, dan upgrade
- Script bantu (dev up, backup DB, healthcheck, registrasi scheduled task) di
  `paradise/bin/`
- Pipeline CI/CD ke GHCR + skrip deploy & rollback per commit SHA
- Rebrand nama aplikasi menjadi "Paradise Task Tracker"

> **Rebrand ≠ penghapusan atribusi.** Yang dibuang dari antarmuka adalah **merek
> produk** upstream (nama, logo, tautan promosi, ajakan berlangganan tier
> berbayar), AGPL-3.0 tidak memberi hak atas merek dagang, dan fork
> termodifikasi yang tetap menyebut dirinya "Plane" justru lebih berisiko.
> Yang **tetap dipertahankan** adalah atribusi hukum: header hak cipta di
> berkas sumber, `LICENSE.txt`, dan berkas ini.

## Kewajiban AGPL-3.0

Karena AGPL-3.0, bila layanan ini diakses lewat jaringan oleh pengguna, source
code (termasuk modifikasi) **wajib tetap tersedia** untuk mereka. Jangan hapus
`LICENSE.txt` maupun berkas ini.

## Library pihak ketiga yang ditambahkan fork ini

Fitur tambahan kantor memakai library open-source berikut. Hak cipta dan lisensi
milik penulis masing-masing; teks lisensinya ikut terdistribusi via paket
(`pip`) dan tidak boleh dihapus.

| Library                                                        | Fitur                            | Lisensi |
| -------------------------------------------------------------- | -------------------------------- | ------- |
| [django-auditlog](https://github.com/jazzband/django-auditlog) | Jejak audit (siapa mengubah apa) | MIT     |
