# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: contoh semua email, dirender dan dikirim ke satu alamat uji
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Render SEMUA email aplikasi dengan data contoh, simpan ke HTML, dan (opsional) kirim.

    python manage.py kirim_contoh_email --out /tmp/contoh-email            # render saja
    python manage.py kirim_contoh_email --out /tmp/contoh-email --kirim    # + kirim
    python manage.py kirim_contoh_email --kirim --host localhost --port 1025   # lewat mailpit

Penerima DIKUNCI ke satu alamat uji (`PENERIMA_UJI`). `--ke` dengan alamat lain
ditolak, dan setiap pesan diperiksa lagi tepat sebelum `send()`. Tidak ada jalur
di perintah ini yang membaca alamat dari database, jadi tidak mungkin terkirim
ke pengguna sungguhan.

Tanpa database: semua orang/tugas/workspace adalah objek contoh, dan tiap email
dirakit lewat fungsi `susun_*` yang SAMA dengan pengirim sungguhan. SMTP diambil
dari God Mode kecuali `--host` diberikan.
"""

import base64
import re
import struct
import zlib
from datetime import timedelta
from email import message_from_bytes
from html import escape
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock
from uuid import uuid4

from django.core.mail import get_connection
from django.core.management import BaseCommand, CommandError
from django.test import override_settings
from django.utils import timezone

PENERIMA_UJI = "it.ai1@itechmandiri.com"
URL = "https://space.paradiseperkasa.com"
SLUG = "pt-paradise-perkasa"


def _png_contoh(ukuran=64) -> bytes:
    """PNG gradien hangat, pengganti foto profil (tanpa Pillow)."""
    baris = b""
    for y in range(ukuran):
        baris += b"\x00" + b"".join(
            bytes((min(255, 180 + x), max(0, 120 - y), 60 + (x + y) // 3)) for x in range(ukuran)
        )

    def potong(jenis, data):
        isi = jenis + data
        return struct.pack(">I", len(data)) + isi + struct.pack(">I", zlib.crc32(isi) & 0xFFFFFFFF)

    kepala = struct.pack(">IIBBBBB", ukuran, ukuran, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + potong(b"IHDR", kepala) + potong(b"IDAT", zlib.compress(baris)) + potong(b"IEND", b"")


def _orang(nama, foto=False):
    return NS(
        id=uuid4(),
        display_name=nama,
        first_name=nama,
        last_name="",
        email=f"{nama.split()[0].lower()}@contoh.paradiseperkasa.com",
        avatar="",
        avatar_asset_id=uuid4() if foto else None,
        avatar_asset=NS(size=1000, asset=NS(name="contoh")) if foto else None,
    )


def _tugas(kode, nama_project, seq, judul, selisih, hari_ini, **lain):
    return NS(
        id=uuid4(),
        project=NS(identifier=kode, name=nama_project, id=uuid4(), workspace=NS(slug=SLUG)),
        project_id=uuid4(),
        workspace=NS(slug=SLUG),
        workspace_id=uuid4(),
        sequence_id=seq,
        name=judul,
        target_date=hari_ini + timedelta(days=selisih) if selisih is not None else None,
        start_date=lain.get("mulai"),
        priority=lain.get("prioritas", "medium"),
        state=NS(name=lain.get("status", "Todo"), group=lain.get("grup", "unstarted")),
        description_stripped=lain.get("deskripsi", ""),
        updated_at=timezone.now(),
    )


class Command(BaseCommand):
    help = f"Render semua email dengan data contoh dan kirim HANYA ke {PENERIMA_UJI}."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="contoh-email", help="Folder untuk berkas .html/.eml")
        parser.add_argument("--kirim", action="store_true", help=f"Kirim juga ke {PENERIMA_UJI}")
        parser.add_argument("--ke", default=PENERIMA_UJI, help="Harus sama dengan alamat uji; lainnya ditolak")
        parser.add_argument("--bahasa", choices=("id", "en", "semua"), default="semua")
        parser.add_argument("--hanya", default="", help="Saring kunci contoh (regex), mis. 'ringkasan|pengingat'")
        parser.add_argument("--host", default="", help="Timpa host SMTP (mis. localhost untuk mailpit)")
        parser.add_argument("--port", type=int, default=0)
        parser.add_argument("--dari", default="", help="Timpa alamat pengirim")

    # ------------------------------------------------------------ utama

    def handle(self, *args, **o):
        if o["ke"].strip().lower() != PENERIMA_UJI:
            raise CommandError(f"Penerima ditolak: perintah ini hanya boleh mengirim ke {PENERIMA_UJI}.")
        bahasa = ("id", "en") if o["bahasa"] == "semua" else (o["bahasa"],)
        folder = Path(o["out"])
        folder.mkdir(parents=True, exist_ok=True)

        koneksi = dari = None
        if o["kirim"]:
            koneksi, dari = self._smtp(o)

        hasil = []
        foto = _png_contoh()
        with (
            override_settings(APP_BASE_URL=URL),
            mock.patch("plane.utils.email_merek._baca_avatar", lambda u: (foto, "png") if u.avatar_asset else None),
        ):
            for b in bahasa:
                for kunci, buat in self._daftar():
                    if o["hanya"] and not re.search(o["hanya"], kunci):
                        continue
                    hasil.append(self._satu(folder, kunci, b, buat, koneksi, dari))
        self._indeks(folder, hasil)

        gagal = [h for h in hasil if h["status"].startswith("GAGAL")]
        self.stdout.write(f"\n{len(hasil)} email dirender ke {folder.resolve()}")
        if o["kirim"]:
            self.stdout.write(f"{len(hasil) - len(gagal)} terkirim ke {PENERIMA_UJI}, {len(gagal)} gagal")
        if gagal:
            raise CommandError(f"{len(gagal)} email gagal")

    def _smtp(self, o):
        from plane.utils.email_merek import koneksi_smtp

        if o["host"]:
            koneksi = get_connection(
                "django.core.mail.backends.smtp.EmailBackend",
                host=o["host"],
                port=o["port"] or 25,
                username="",
                password="",
                timeout=20,
            )
            dari = o["dari"] or "Space Paradise Perkasa <noreply@paradiseperkasa.com>"
        else:
            koneksi, dari = koneksi_smtp(timeout=20)
            if not koneksi.host:
                raise CommandError("SMTP belum diatur di God Mode > Email. Pakai --host/--port untuk server lain.")
            dari = o["dari"] or dari
        try:
            koneksi.open()
        except Exception as e:  # noqa: BLE001
            raise CommandError(f"SMTP {koneksi.host}:{koneksi.port} tidak bisa dihubungi: {e}") from e
        return koneksi, dari

    def _satu(self, folder, kunci, bahasa, buat, koneksi, dari):
        from plane.utils.email_merek import buat_pesan

        subjek, html, teks, gambar, lampiran = buat(bahasa)
        pesan = buat_pesan(
            ke=PENERIMA_UJI,
            subjek=f"[Contoh {bahasa}] {subjek}",
            html=html,
            teks=teks,
            koneksi=koneksi or get_connection("django.core.mail.backends.locmem.EmailBackend"),
            dari=dari or "noreply@paradiseperkasa.com",
            gambar=gambar,
            lampiran=lampiran,
        )
        nama = f"{kunci}-{bahasa}"
        (folder / f"{nama}.html").write_text(self._sisipkan_gambar(html, pesan), encoding="utf-8")
        (folder / f"{nama}.txt").write_text(teks, encoding="utf-8")
        (folder / f"{nama}.eml").write_bytes(pesan.message().as_bytes())
        status = "dirender"
        if koneksi is not None:
            # Pemeriksaan terakhir: apa pun yang terjadi di atas, hanya alamat uji.
            if pesan.to != [PENERIMA_UJI] or pesan.cc or pesan.bcc:
                raise CommandError(f"Penerima tak terduga {pesan.to} {pesan.cc} {pesan.bcc}; dibatalkan.")
            try:
                status = "terkirim" if pesan.send(fail_silently=False) == 1 else "GAGAL: tidak diterima relay"
            except Exception as e:  # noqa: BLE001
                status = f"GAGAL: {e}"
        self.stdout.write(f"  {nama:<34} {status:<12} {subjek}")
        return {"nama": nama, "subjek": subjek, "status": status, "bahasa": bahasa}

    @staticmethod
    def _sisipkan_gambar(html, pesan):
        """cid: tidak terbaca peramban; ganti data: URI supaya pratinjau HTML sama dengan kotak masuk."""
        for g in pesan.gambar:
            uri = f"data:image/{g.subtipe};base64,{base64.b64encode(g.data).decode()}"
            html = html.replace(f"cid:{g.cid}", uri)
        return html

    def _indeks(self, folder, hasil):
        baris = "".join(
            f'<li><a href="{escape(h["nama"])}.html">{escape(h["nama"])}</a> {escape(h["subjek"])} '
            f"<small>({escape(h['status'])})</small></li>"
            for h in hasil
        )
        (folder / "index.html").write_text(
            f'<!doctype html><meta charset="utf-8"><title>Contoh email</title><body style="font-family:sans-serif">'
            f"<h1>Contoh email ({len(hasil)})</h1><ol>{baris}</ol></body>",
            encoding="utf-8",
        )

    # ------------------------------------------------------------ contoh

    def _daftar(self):
        """[(kunci, fungsi(bahasa) -> (subjek, html, teks, gambar, lampiran))]."""
        h = timezone.localtime(timezone.now()).date()
        andi, budi, sari, hartono = _orang("Andi"), _orang("Budi Santoso", foto=True), _orang("Sari"), _orang("Hartono")
        gdg, krm = ("GDG", "Gudang"), ("KRM", "Pengiriman")
        t1 = _tugas(*gdg, 41, "Stock opname rak C", -2, h, status="In Progress", grup="started")
        t2 = _tugas(*gdg, 44, "Rekap barang retur Oktober", 0, h)
        t3 = _tugas(*gdg, 47, "Label ulang palet masuk", 3, h)
        t4 = _tugas(*krm, 12, "Jadwal armada minggu depan", -9, h, prioritas="high")
        t5 = _tugas(*krm, 15, "Konfirmasi resi ekspedisi", 0, h)
        baru = _tugas(
            *gdg,
            52,
            "Audit selisih stok SKU elektronik",
            4,
            h,
            prioritas="high",
            mulai=h,
            deskripsi="Cocokkan stok fisik rak E1-E4 dengan sistem. Selisih di atas 2% dilaporkan dengan foto rak.",
        )
        beres = _tugas(*gdg, 39, "Stock opname rak A", 0, h, status="Done", grup="completed")
        nama_pj = {t1.id: ["Andi"], t2.id: ["Andi"], t3.id: ["Rina"], t4.id: ["Dodi"], t5.id: [], beres.id: ["Andi"]}

        def templat(susun, *arg, gambar=None):
            def f(b):
                g = [] if gambar is None else gambar
                hasil = susun(*arg, b, *([g] if gambar is not None else []))
                subjek, html, teks = hasil
                return subjek, html, teks, g, []

            return f

        from plane.bgtasks import daily_digest_email as dd
        from plane.bgtasks import direktur_digest_email as dr
        from plane.bgtasks.analytic_plot_export import susun_ekspor
        from plane.bgtasks.chat_email import susun_email_pesan
        from plane.bgtasks.deadline_reminder_email import bangun_ics, susun_email_pengingat
        from plane.bgtasks.dormancy_task import susun_peringatan_tidur
        from plane.bgtasks.email_notification_task import (
            _STRINGS_APPROVAL_EN,
            _STRINGS_APPROVAL_ID,
            konteks_persetujuan,
            render_approval,
        )
        from plane.bgtasks.forgot_password_task import susun_lupa_sandi
        from plane.bgtasks.login_activity_retention import susun_peringatan_retensi
        from plane.bgtasks.magic_link_code_task import susun_magic_link
        from plane.bgtasks.penugasan_email import susun_email_penugasan
        from plane.bgtasks.project_add_user_email_task import susun_tambah_project
        from plane.bgtasks.project_invitation_task import susun_undangan_project
        from plane.bgtasks.user_activation_email_task import susun_aktivasi
        from plane.bgtasks.user_deactivation_email_task import susun_deaktivasi
        from plane.bgtasks.user_email_update_task import susun_email_diubah
        from plane.bgtasks.webhook_task import susun_webhook_nonaktif
        from plane.bgtasks.workspace_invitation_task import susun_undangan_workspace
        from plane.utils.email_merek import render_email
        from plane.utils.email_pembaruan import susun_email_pembaruan
        from plane.utils.email_teks import teks as kamus

        ke = PENERIMA_UJI
        undangan = f"{URL}/workspace-invitations/?invitation_id=contoh&slug={SLUG}&token=contoh"

        def lewat_user(susun, *arg):
            """Pengundang berupa nama (bukan User), jadi tampil sebagai avatar inisial."""
            return templat(susun, *arg, gambar=[])

        def uji(b):
            t = kamus("uji", b)
            html, polos = render_email(
                "emails/test_email.html", {"t": t, "judul": t["subjek"], "pratajuk": t["intro"], "email_penerima": ke}, b
            )
            return t["subjek"], html, polos, [], []

        def ekspor(b):
            s, html, polos = susun_ekspor(ke, b)
            return s, html, polos, [], [(f"{SLUG}-analytics.csv", "State,Issue Count\nTodo,12\nDone,30\n", "text/csv")]

        def persetujuan(verb, aktor, alasan=""):
            def f(b):
                s = _STRINGS_APPROVAL_ID if b == "id" else _STRINGS_APPROVAL_EN
                k = konteks_persetujuan(
                    s, verb, aktor.display_name, "GDG-52", baru.name, alasan,
                    f"{URL}/{SLUG}/projects/x/issues/y", f"{URL}/{SLUG}/projects/x/persetujuan",
                )  # fmt: skip
                g = []
                html, polos = render_approval(k, b, aktor, ke, SLUG, g)
                return k["subject"], html, polos, g, []

            return f

        def pembaruan(b):
            issue = NS(
                id=uuid4(), name=t1.name, sequence_id=41,
                project=NS(id=uuid4(), identifier="GDG", workspace=NS(slug=SLUG)),
            )  # fmt: skip
            aktor = [
                {
                    "user": budi,
                    "waktu": "09:12",
                    "changes": {
                        "state": {"old_value": ["Todo"], "new_value": ["In Progress"]},
                        "priority": {"old_value": ["medium"], "new_value": ["high"]},
                        "target_date": {"old_value": [str(h)], "new_value": [str(h + timedelta(days=2))]},
                        "assignees": {"old_value": [], "new_value": ["Andi", "Rina"]},
                    },
                    "komentar": [],
                },
                {
                    "user": sari,
                    "waktu": "10:05",
                    "changes": {},
                    "komentar": ["<p>Rak C sudah dihitung ulang, selisih tinggal <strong>3 unit</strong>.</p>"],
                },
            ]
            s, html, polos, g = susun_email_pembaruan(issue, aktor, URL, b, ke)
            return s, html, polos, g, []

        def penugasan(b):
            g = []
            s, polos, html = susun_email_penugasan(baru, andi, budi, "Supervisor", f"{URL}/{SLUG}/x", b, g)
            ics = bangun_ics(baru, f"GDG-52 {baru.name}", "Contoh", f"{URL}/{SLUG}/x")
            return s, html, polos, g, [("GDG-52.ics", ics, "text/calendar; method=PUBLISH")]

        def pengingat(tugas, titik):
            def f(b):
                s, polos, html = susun_email_pengingat(tugas, andi, titik, "", f"{URL}/{SLUG}/x", bahasa=b)
                ics = bangun_ics(tugas, f"GDG-{tugas.sequence_id} {tugas.name}", "Contoh", f"{URL}/{SLUG}/x")
                return s, html, polos, [], [(f"GDG-{tugas.sequence_id}.ics", ics, "text/calendar; method=PUBLISH")]

            return f

        def ringkasan(penerima, r):
            def f(b):
                s, polos, html = dd.susun_email(penerima, r, h, bahasa=b)
                return s, html, polos, [], []

            return f

        depan_sore = dd.hari_ke_hari_kerja_berikutnya(h)
        sore = dd.kelompokkan([t1, t3], h, depan_sore)
        sore.selesai = [beres]
        r_staf = dd.Ringkasan(peran="Staf", cakupan="Gudang", sendiri=dd.kelompokkan([t1, t2, t3], h))
        r_sore = dd.Ringkasan(
            peran="Supervisor", cakupan="Gudang", diberikan=sore, judul_tim="Departemen Anda", penanggung=nama_pj,
            tim=[dd.GrupTim(nama="Gudang", tugas=dd.kelompokkan([t2], h, depan_sore))], sore=True,
            hari_ke_depan=depan_sore,
        )  # fmt: skip
        r_mgr = dd.Ringkasan(
            peran="Manager", cakupan="Operasional", judul_tim="Divisi Anda", penanggung=nama_pj,
            tim=[
                dd.GrupTim(nama="Pengiriman", tugas=dd.kelompokkan([t4, t5], h)),
                dd.GrupTim(nama="Gudang", tugas=dd.kelompokkan([t1, t2, t3], h)),
            ],
        )  # fmt: skip
        A = dr.Angka
        laporan = dr.Laporan(
            jendela="24 jam terakhir",
            divisi=[
                dr.DivisiLaporan(
                    "Operasional", ["Sari"],
                    [
                        dr.Unit("Pengiriman", ["Dodi"], A(selesai=4, lewat=6, macet=2, hari=3, depan=9)),
                        dr.Unit("Gudang", ["Budi"], A(selesai=7, lewat=3, macet=0, hari=2, depan=11)),
                    ],
                ),
                dr.DivisiLaporan("Finance", ["Lestari"], [dr.Unit("Accounting", [], A(selesai=5, lewat=1, depan=4))]),
            ],
        )  # fmt: skip

        def direktur(b):
            s, polos, html = dr.susun_email(hartono, laporan, h, f"{URL}/{SLUG}", bahasa=b)
            return s, html, polos, [], []

        def obrolan(b):
            g = []
            r = [(budi, 3, "Pak, stok rak C sudah saya cek ulang, hasilnya di lampiran."), (sari, 1, "Rapat jam 2 jadi?")]
            s, polos, html = susun_email_pesan(andi, SLUG, r, b, g)
            return s, html, polos, g, []

        def tidur(b):
            s, polos, html = susun_peringatan_tidur("Proyek Lama", "proyek-lama", 60, 30, b, ke)
            return s, html, polos, [], []

        def retensi(b):
            k = {"akan_dibuang": 1240, "retensi_hari": 90, "ambang_peringatan_hari": 7, "tertua": h - timedelta(days=88)}
            s, polos, html = susun_peringatan_retensi(k, b, ke)
            return s, html, polos, [], []

        return [
            ("01-kode-masuk", templat(susun_magic_link, ke, "482913")),
            ("02-kode-ganti-email", lambda b: (*susun_magic_link(ke, "715204", b, grup="ganti_email"), [], [])),
            ("03-lupa-sandi", templat(susun_lupa_sandi, ke, f"{URL}/accounts/reset-password/?token=contoh")),
            ("04-undangan-workspace", lewat_user(susun_undangan_workspace, ke, "Budi Santoso", "PT Paradise Perkasa", undangan)),
            ("05-undangan-project", lewat_user(susun_undangan_project, ke, "Budi Santoso", "Gudang", undangan)),
            ("06-ditambahkan-project", lewat_user(susun_tambah_project, ke, "Budi Santoso", "Gudang", "PT Paradise Perkasa", f"{URL}/{SLUG}/projects/x/issues")),
            ("07-email-diganti", templat(susun_email_diubah, ke)),
            ("08-akun-aktif", templat(susun_aktivasi, ke, f"{URL}/profile")),
            ("09-akun-nonaktif", templat(susun_deaktivasi, ke, f"{URL}/login")),
            ("10-ekspor-analitik", ekspor),
            ("11-webhook-mati", templat(susun_webhook_nonaktif, ke, "https://hooks.contoh.com/paradise", f"{URL}/{SLUG}/settings/webhooks/x")),
            ("12-email-uji", uji),
            ("13-pembaruan-tugas", pembaruan),
            ("14-persetujuan-diajukan", persetujuan("submitted", andi)),
            ("15-persetujuan-disetujui", persetujuan("approved", budi)),
            ("16-persetujuan-ditolak", persetujuan("rejected", budi, "Foto rak belum dilampirkan, tolong tambahkan.")),
            ("17-tugas-baru", penugasan),
            ("18-pengingat-h3", pengingat(t3, -3)),
            ("19-pengingat-terlambat", pengingat(t1, 2)),
            ("20-ringkasan-pagi-staf", ringkasan(andi, r_staf)),
            ("21-ringkasan-sore-supervisor", ringkasan(budi, r_sore)),
            ("22-ringkasan-pagi-manager", ringkasan(sari, r_mgr)),
            ("23-laporan-direktur", direktur),
            ("24-obrolan", obrolan),
            ("25-workspace-tidur", tidur),
            ("26-retensi-login", retensi),
        ]  # fmt: skip


def baca_eml(path) -> dict:
    """Ringkasan struktur MIME satu .eml (dipakai tes): {jenis: [content-type...], cid: [...]}."""
    pesan = message_from_bytes(Path(path).read_bytes())
    jenis, cid = [], []
    for bagian in pesan.walk():
        jenis.append(bagian.get_content_type())
        if bagian.get("Content-ID"):
            cid.append(bagian.get("Content-ID").strip("<>"))
    return {"jenis": jenis, "cid": cid}

