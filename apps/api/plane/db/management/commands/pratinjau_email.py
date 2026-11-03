# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pratinjau semua email notifikasi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Render semua email notifikasi dengan data contoh ke satu berkas HTML.

    python manage.py pratinjau_email --out /tmp/pratinjau-email.html

Tanpa database dan tanpa SMTP: tiap email lewat fungsi render yang SAMA dengan
pengirimnya (susun_email_*, konteks_persetujuan, templat Django), jadi yang
terlihat di sini adalah yang diterima orang. Di atasnya ada matriks siapa
menerima apa secara bawaan, dibaca dari `BAWAAN_STAF` / `BAWAAN_PIMPINAN`.
"""

from datetime import timedelta
from html import escape
from types import SimpleNamespace as NS
from uuid import uuid4

from django.core.management import BaseCommand
from django.test import override_settings
from django.utils import timezone

from plane.bgtasks import daily_digest_email as dd
from plane.bgtasks import direktur_digest_email as dr
from plane.bgtasks.deadline_reminder_email import susun_email_pengingat
from plane.bgtasks.email_notification_task import _STRINGS_APPROVAL_ID, konteks_persetujuan, render_approval
from plane.bgtasks.penugasan_email import susun_email_penugasan
from plane.utils.email import generate_plain_text_from_html
from plane.utils.email_merek import render_email
from plane.utils.email_pembaruan import konteks_pembaruan
from plane.utils.preferensi_email import BAWAAN_PIMPINAN, BAWAAN_STAF

URL = "https://tasks.paradise.example"
WS = NS(slug="pt-paradise-perkasa")

# (judul, saklar | None = selalu, penjelasan)
JENIS = [
    ("Tugas baru untuk Anda", "assigned", "Begitu seseorang menambahkan Anda sebagai penanggung jawab"),
    ("Ringkasan harian", "daily_digest", "Sen-Jum 08.30: tugas Anda + yang Anda berikan (+ tim untuk spv/manager)"),
    ("Ringkasan akhir hari", "daily_digest_sore", "Sen-Jum 17.30: selesai hari ini, belum selesai, besok"),
    ("Laporan direktur", None, "Sen-Jum 08.30, khusus direktur: angka per divisi/departemen, tanpa rincian staf"),
    ("Keputusan persetujuan", "approval", "Pengajuan disetujui/ditolak (dan pengajuan baru untuk penyetuju)"),
    ("Tugas selesai", "issue_completed", "Tugas yang Anda ikuti pindah ke status selesai"),
    ("Pengingat tenggat per tugas", "deadline_reminder", "H-7..H+7 + .ics; juga butuh saklar God Mode"),
    ("Perubahan properti / status / komentar / mention", "property_change", "Email pembaruan umum Plane"),
]


def _orang(nama):
    return NS(id=uuid4(), display_name=nama, first_name=nama, email=f"{nama.lower()}@paradise.example")


def _project(kode, nama):
    return NS(identifier=kode, name=nama)


def _tugas(project, seq, nama, selisih, hari_ini, **lain):
    return NS(
        id=uuid4(),
        project=project,
        project_id=uuid4(),
        workspace=WS,
        sequence_id=seq,
        name=nama,
        target_date=hari_ini + timedelta(days=selisih) if selisih is not None else None,
        start_date=lain.get("mulai"),
        priority=lain.get("prioritas", "medium"),
        state=NS(name=lain.get("status", "Todo")),
        description_stripped=lain.get("deskripsi", ""),
        updated_at=timezone.now(),
    )


class Command(BaseCommand):
    help = "Render semua email notifikasi Paradise dengan data contoh ke satu berkas HTML."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="pratinjau-email.html")

    def handle(self, *args, **opsi):
        with override_settings(APP_BASE_URL=URL):
            email = self._semua(timezone.localtime(timezone.now()).date())
        with open(opsi["out"], "w", encoding="utf-8") as f:
            f.write(self._halaman(email))
        self.stdout.write(f"{len(email)} email -> {opsi['out']}")

    # ------------------------------------------------------------ contoh

    def _semua(self, h):
        gdg, krm, rek = _project("GDG", "Gudang"), _project("KRM", "Pengiriman"), _project("REK", "Rekrutmen")
        staf, rina, sup, mgr, dirk = (_orang(n) for n in ("Andi", "Rina", "Budi", "Sari", "Hartono"))
        t1 = _tugas(gdg, 41, "Stock opname rak C", -2, h, status="In Progress")
        t2 = _tugas(gdg, 44, "Rekap barang retur Oktober", 0, h)
        t3 = _tugas(gdg, 47, "Label ulang palet masuk", 3, h)
        t4 = _tugas(krm, 12, "Jadwal armada minggu depan", -9, h, prioritas="high")
        t5 = _tugas(krm, 15, "Konfirmasi resi ekspedisi", 0, h)
        t6 = _tugas(gdg, 50, "Cek suhu cold storage", 5, h)
        baru = _tugas(
            gdg,
            52,
            "Audit selisih stok SKU elektronik",
            4,
            h,
            prioritas="high",
            mulai=h,
            deskripsi="Cocokkan stok fisik rak E1-E4 dengan sistem. Selisih di atas 2% dilaporkan dengan foto rak.",
        )
        nama = {t1.id: ["Andi"], t2.id: ["Andi"], t3.id: ["Rina"], t4.id: ["Dodi"], t5.id: [], t6.id: ["Rina"]}

        hasil = [
            (
                "Staf (Andi)",
                "Tugas baru untuk Anda",
                *susun_email_penugasan(baru, staf, sup, "Supervisor", f"{URL}/pt-paradise-perkasa/projects/x/issues/y"),
                "Dilampiri GDG-52.ics karena tugasnya punya tenggat.",
            ),
        ]

        r_staf = dd.Ringkasan(peran="Staf", cakupan="Gudang", sendiri=dd.kelompokkan([t1, t2], h))
        hasil.append(("Staf (Andi)", "Ringkasan harian", *dd.susun_email(staf, r_staf, h), ""))

        r_sup = dd.Ringkasan(
            peran="Supervisor",
            cakupan="Gudang",
            diberikan=dd.kelompokkan([t1, t3], h),
            judul_tim="Departemen Anda",
            penanggung=nama,
            tim=[dd.GrupTim(nama="Gudang", tugas=dd.kelompokkan([t2, t6], h))],
        )
        hasil.append(("Supervisor (Budi)", "Ringkasan harian", *dd.susun_email(sup, r_sup, h), ""))

        # Edisi sore: jendela depan = hari kerja berikutnya, plus yang selesai hari ini.
        depan_sore = dd.hari_ke_hari_kerja_berikutnya(h)
        beres = _tugas(gdg, 47, "Stock opname rak A", 0, h, status="Done")
        beres.state.group = "completed"
        sore_sup = dd.kelompokkan([t1, t3], h, depan_sore)
        sore_sup.selesai = [beres]
        r_sore = dd.Ringkasan(
            peran="Supervisor",
            cakupan="Gudang",
            diberikan=sore_sup,
            judul_tim="Departemen Anda",
            penanggung={**nama, beres.id: ["Andi"]},
            tim=[dd.GrupTim(nama="Gudang", tugas=dd.kelompokkan([t2, t6], h, depan_sore))],
            sore=True,
            hari_ke_depan=depan_sore,
        )
        hasil.append(
            (
                "Supervisor (Budi)",
                "Ringkasan akhir hari",
                *dd.susun_email(sup, r_sore, h),
                "Sen-Jum 17.30, saklar daily_digest_sore.",
            )
        )

        r_mgr = dd.Ringkasan(
            peran="Manager",
            cakupan="Operasional",
            judul_tim="Divisi Anda",
            penanggung=nama,
            tim=[
                dd.GrupTim(nama="Pengiriman", tugas=dd.kelompokkan([t4, t5], h)),
                dd.GrupTim(nama="Gudang", tugas=dd.kelompokkan([t1, t2, t3, t6], h)),
            ],
        )
        hasil.append(("Manager (Sari)", "Ringkasan harian", *dd.susun_email(mgr, r_mgr, h), ""))

        pribadi = _tugas(rek, 3, "Tanda tangan kontrak vendor seragam", 1, h)
        r_dir = dd.Ringkasan(peran="Direktur", cakupan="Seluruh divisi", sendiri=dd.kelompokkan([pribadi], h))
        hasil.append(
            (
                "Direktur (Hartono)",
                "Ringkasan harian",
                *dd.susun_email(dirk, r_dir, h),
                "Hanya tugas pribadinya. Tanpa bagian tim; tidak dikirim kalau kosong.",
            )
        )

        A = dr.Angka
        laporan = dr.Laporan(
            jendela="24 jam terakhir",
            divisi=[
                dr.DivisiLaporan(
                    "Operasional",
                    ["Sari"],
                    [
                        dr.Unit("Pengiriman", ["Dodi"], A(selesai=4, lewat=6, macet=2, hari=3, depan=9)),
                        dr.Unit("Gudang", ["Budi"], A(selesai=7, lewat=3, macet=0, hari=2, depan=11)),
                    ],
                ),
                dr.DivisiLaporan(
                    "Finance",
                    ["Lestari"],
                    [
                        dr.Unit("Accounting", ["Yoga"], A(selesai=5, lewat=1, hari=1, depan=4)),
                        dr.Unit("Tax", [], A(selesai=1, depan=2)),
                    ],
                ),
                dr.DivisiLaporan("HRGA", ["Maya"], [dr.Unit("Rekrutmen", ["Tono"], A(selesai=2, hari=1, depan=3))]),
            ],
        )
        hasil.append(
            (
                "Direktur (Hartono)",
                "Laporan direktur",
                *dr.susun_email(dirk, laporan, h, f"{URL}/pt-paradise-perkasa"),
                "Selalu hidup. Hanya angka + nama manager/supervisor.",
            )
        )

        hasil.append(
            (
                "Staf (Andi)",
                "Pengingat tenggat H-3",
                *susun_email_pengingat(t3, staf, -3, "tinggal 3 hari lagi", f"{URL}/x"),
                "Bawaan mati (ringkasan harian menggantikannya).",
            )
        )
        hasil.append(
            (
                "Staf (Andi)",
                "Pengingat TERLAMBAT H+3",
                *susun_email_pengingat(
                    _tugas(gdg, 41, "Stock opname rak C", -3, h, status="In Progress"),
                    staf,
                    3,
                    "TERLAMBAT 3 hari",
                    f"{URL}/x",
                ),
                "Bawaan mati.",
            )
        )

        for verb, judul, penerima, aktor, alasan in (
            ("submitted", "Persetujuan: pengajuan baru", "Supervisor (Budi)", "Andi", ""),
            ("approved", "Persetujuan: disetujui", "Staf (Andi)", "Budi", ""),
            ("rejected", "Persetujuan: ditolak", "Staf (Andi)", "Budi", "Tenggat terlalu mepet, geser ke Jumat."),
        ):
            k = konteks_persetujuan(
                _STRINGS_APPROVAL_ID, verb, aktor, "GDG-52", baru.name, alasan, f"{URL}/x", f"{URL}/x/persetujuan"
            )
            html, _ = render_approval(k, "id", _orang(aktor), "", WS.slug)
            ket = "Bawaan pimpinan mati: pengajuan menunggu tidak diemail ke atasan." if verb == "submitted" else ""
            hasil.append((penerima, judul, k["subject"], generate_plain_text_from_html(html), html, ket))

        k = konteks_pembaruan(
            {"issue_identifier": "GDG-41", "name": t1.name, "issue_url": f"{URL}/x"},
            [{"nama": "Budi", "waktu": "09:12", "changes": {"state": {"old_value": ["In Progress"], "new_value": ["Done"]}}}],
            "id",
        )
        html, _ = render_email(
            "emails/notifications/issue-updates.html",
            {**k, "judul": f"GDG-41 {t1.name}", "alasan": k["t"]["alasan"], "url_preferensi": f"{URL}/settings"},
            "id",
        )
        hasil.append(
            (
                "Staf (Andi)",
                "Pembaruan work item",
                f"GDG-41 {t1.name}",
                generate_plain_text_from_html(html),
                html,
                "Dipakai juga untuk komentar/properti kalau dinyalakan.",
            )
        )
        return hasil

    # ------------------------------------------------------------ halaman

    def _matriks(self):
        def sel(saklar, pimpinan, direktur=False):
            if saklar is None:
                return "ya (selalu)" if direktur else "-"
            nilai = (BAWAAN_PIMPINAN if pimpinan else BAWAAN_STAF)[saklar]
            return "ya" if nilai else "mati*"

        baris = "".join(
            f"<tr><td><b>{escape(j)}</b><br><small>{escape(k)}</small></td>"
            f"<td>{sel(s, False)}</td><td>{sel(s, True)}</td><td>{sel(s, True)}</td><td>{sel(s, True, True)}</td></tr>"
            for j, s, k in JENIS
        )
        return (
            "<h2>Siapa menerima apa (bawaan)</h2><table class=m><tr><th>Email</th><th>Staf</th>"
            "<th>Supervisor</th><th>Manager</th><th>Direktur</th></tr>"
            f"{baris}</table><p><small>* mati = bisa dinyalakan sendiri di Profil &gt; Notifikasi. "
            "Bawaan bisa diubah Super Admin di God Mode &gt; Members &gt; Defaults (berlaku untuk akun baru).</small></p>"
        )

    def _halaman(self, email):
        kartu = ""
        for i, (siapa, judul, subjek, teks, html, ket) in enumerate(email):
            kartu += (
                f'<section id="e{i}"><h3>{escape(judul)} <span class=p>untuk {escape(siapa)}</span></h3>'
                f"<div class=s><b>Subjek:</b> {escape(subjek)}</div>"
                + (f"<div class=k>{escape(ket)}</div>" if ket else "")
                + f'<iframe srcdoc="{escape(html)}" onload="this.style.height=this.contentDocument.body.scrollHeight+40+\'px\'"></iframe>'
                f"<details><summary>Versi teks</summary><pre>{escape(teks)}</pre></details></section>"
            )
        daftar = "".join(
            f'<li><a href="#e{i}">{escape(e[1])}</a> <small>({escape(e[0])})</small></li>' for i, e in enumerate(email)
        )
        return f"""<!doctype html><html lang=id><meta charset=utf-8><title>Pratinjau email Paradise</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;background:#f3f4f6;color:#1f2937;margin:0;padding:24px}}
main{{max-width:760px;margin:auto}} h1{{font-size:22px}} h2{{font-size:17px;margin-top:28px}}
table.m{{border-collapse:collapse;background:#fff;width:100%;font-size:13px}}
table.m td,table.m th{{border:1px solid #e5e7eb;padding:6px 8px;text-align:left;vertical-align:top}}
section{{background:#fff;border-radius:8px;padding:16px;margin:20px 0;box-shadow:0 1px 2px #0001}}
section h3{{margin:0 0 8px;font-size:16px}} .p{{color:#6b7280;font-weight:normal;font-size:13px}}
.s{{font-size:13px;background:#f9fafb;padding:6px 8px;border-radius:4px}} .k{{font-size:12px;color:#b45309;margin:6px 0}}
iframe{{width:100%;border:1px solid #e5e7eb;border-radius:4px;margin-top:10px;min-height:200px}}
pre{{white-space:pre-wrap;font-size:12px;background:#f9fafb;padding:8px}}
</style><main><h1>Pratinjau email notifikasi Paradise</h1>
{self._matriks()}<h2>Email ({len(email)})</h2><ol>{daftar}</ol>{kartu}</main></html>"""
