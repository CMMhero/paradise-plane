# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi data demo, obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kanal, DM, balasan, reaksi, dan lampiran obrolan untuk data demo.

Berkas berawalan `_` supaya Django tidak membacanya sebagai command.

Ditulis lewat model yang sama dengan `ChatPesanEndpoint`: `ruang_dm` untuk DM
(langganan kedua pihak lahir bersamanya), `pesan_terakhir_pada` didenormalisasi,
`catat_pesan_dm` menulis baris Inbox penerima. Status baca disetel sengaja tidak
seragam: pesan terakhir di sebagian ruang dibiarkan belum dibaca supaya lencana
Chat dan daftar percakapan terlihat seperti dipakai orang.

Super Admin pemilik instance ikut di kanal umum dan menerima DM dari direktur,
supaya akun yang paling sering membuka aplikasi tidak melihat Chat kosong.
"""

# Python imports
from datetime import timedelta

# Third party imports
from crum import impersonate

# Module imports
from plane.db.management.commands import _demo_berkas as berkas
from plane.db.management.commands import _demo_data as data
from plane.db.models import FileAsset, Langganan, PesanLangsung, ReaksiPesan, Ruang
from plane.utils.chat_ruang import ruang_dm

TOPIK_KANAL = "seed-demo"

PERCAKAPAN_UMUM = [
    ("direktur0", "Selamat pagi semua. Target kuartal IV sudah dibagikan ke tiap divisi, mohon dipelajari ya."),
    ("manager:SLS", "Siap Pak. Tim Sales sudah breakdown per wilayah, nanti saya kirim ringkasannya."),
    ("manager:HRGA", "Pengingat: pengumpulan form penilaian kinerja paling lambat Jumat ini."),
    ("staf:WH:0", "Info gudang: pengiriman ke Jabodetabek hari ini mundur 2 jam karena hujan."),
    ("manager:IT", "Maintenance server file malam ini 22.00 - 23.00, akses folder bersama sementara mati."),
    ("staf:SLS-DOM:1", "Terima kasih infonya Pak."),
    ("direktur1", "Mohon semua divisi update progres di Paradise Task Tracker sebelum rapat Senin."),
]

PERCAKAPAN_PENGUMUMAN = [
    ("manager:HRGA", "Libur bersama akhir tahun: 24 - 26 Desember. Mohon atur cuti dengan atasan masing-masing."),
    ("manager:HRGA", "Pelatihan K3 untuk karyawan produksi dijadwalkan Rabu depan di aula lantai 1."),
    ("direktur0", "Selamat untuk tim Sales yang melampaui target Oktober. Kerja bagus!"),
]

PERCAKAPAN_DIVISI = [
    ("manager", "Tim, tolong cek tugas yang lewat tenggat di papan masing-masing hari ini."),
    ("spv", "Siap, saya rekap dan kabari sore ini."),
    ("staf0", "Tugas saya yang tertunda tinggal satu, menunggu data dari divisi lain."),
    ("spv", "Oke, kalau perlu bantuan eskalasi bilang saja."),
    ("manager", "Rapat mingguan pindah ke Kamis jam 10 ya."),
    ("staf1", "Noted Pak."),
]

PERCAKAPAN_DM = [
    ("a", "Halo, tugas yang kemarin sudah sampai mana?"),
    ("b", "Sudah sekitar 70%, sisa finalisasi laporan. Besok pagi saya kirim."),
    ("a", "Sip. Kalau ada kendala kabari ya."),
    ("b", "Baik, terima kasih."),
]

REAKSI = ["👍", "🙏", "🎉", "✅", "👀"]


def isi_obrolan(cmd):
    """Isi Chat untuk perusahaan demo. `cmd` = instance Command seed (punya peta orang & rng)."""
    ws, rng, now = cmd.ws, cmd.rng, cmd.now
    semua = _semua_orang(cmd)
    peta = _peta_peran(cmd)

    umum = _kanal(ws, cmd.actor, "Umum", "Obrolan seluruh karyawan", Ruang.Tipe.KANAL, [*semua, cmd.actor])
    pengumuman = _kanal(
        ws, cmd.actor, "Pengumuman", "Info resmi dari manajemen dan HR", Ruang.Tipe.KANAL, [*semua, cmd.actor]
    )
    _isi_ruang(cmd, umum, [(peta[k], t) for k, t in PERCAKAPAN_UMUM], now - timedelta(days=3), lampiran=True)
    _isi_ruang(cmd, pengumuman, [(peta[k], t) for k, t in PERCAKAPAN_PENGUMUMAN], now - timedelta(days=6))

    for kode, nama, deps in data.ORGANISASI:
        manager = cmd.manager[kode]
        spv = cmd.supervisor[deps[0][0]]
        staf = cmd.staf[deps[0][0]]
        anggota = {manager, *cmd.direktur}
        for dep, _ in deps:
            anggota |= {cmd.supervisor[dep], *cmd.staf[dep]}
        ruang = _kanal(ws, manager, f"Divisi {nama}", f"Koordinasi internal divisi {nama}", Ruang.Tipe.PRIVAT, anggota)
        peran = {"manager": manager, "spv": spv, "staf0": staf[0], "staf1": staf[1 % len(staf)]}
        mulai = now - timedelta(days=rng.randint(1, 4), hours=rng.randint(0, 8))
        _isi_ruang(cmd, ruang, [(peran[k], t) for k, t in PERCAKAPAN_DIVISI], mulai)

    pasangan = [(cmd.direktur[0], cmd.actor), (cmd.direktur[1], cmd.actor)]
    for dep, spv in cmd.supervisor.items():
        pasangan += [(spv, s) for s in rng.sample(cmd.staf[dep], k=min(2, len(cmd.staf[dep])))]
    for kode, _, deps in data.ORGANISASI:
        pasangan.append((cmd.manager[kode], cmd.supervisor[deps[0][0]]))
    for a, b in dict.fromkeys(pasangan):  # supervisor dua departemen jangan dobel
        ruang = ruang_dm(ws.id, a.id, b.id)
        mulai = now - timedelta(days=rng.randint(0, 5), hours=rng.randint(1, 20))
        _isi_ruang(cmd, ruang, [({"a": a, "b": b}[k], t) for k, t in PERCAKAPAN_DM], mulai, dm=(a, b))


def _semua_orang(cmd):
    orang = [*cmd.direktur, *cmd.manager.values(), *cmd.supervisor_user.values()]
    return orang + [u for users in cmd.staf.values() for u in users]


def _peta_peran(cmd):
    """Kunci pendek di naskah percakapan -> user. `staf:WH:0` = staf pertama departemen WH."""
    peta = {f"direktur{i}": u for i, u in enumerate(cmd.direktur)}
    peta |= {f"manager:{k}": u for k, u in cmd.manager.items()}
    for dep, users in cmd.staf.items():
        peta |= {f"staf:{dep}:{i}": u for i, u in enumerate(users)}
    return peta


def _kanal(ws, pembuat, nama, topik, tipe, anggota):
    with impersonate(pembuat):
        ruang = Ruang.objects.create(workspace=ws, tipe=tipe, nama=nama, topik=topik)
        Langganan.objects.bulk_create([Langganan(ruang=ruang, user=u) for u in dict.fromkeys(anggota)])
    return ruang


def _isi_ruang(cmd, ruang, naskah, mulai, dm=None, lampiran=False):
    """Tulis naskah ke ruang, mundur ke `mulai`, lalu setel status baca tiap pelanggan."""
    from plane.utils.inbox_chat import catat_pesan_dm  # noqa: PLC0415

    rng, waktu, pesan_list = cmd.rng, mulai, []
    for i, (pengirim, isi) in enumerate(naskah):
        waktu = min(waktu + timedelta(minutes=rng.randint(4, 140)), cmd.now - timedelta(minutes=5))
        penerima = None
        if dm:
            penerima = dm[1] if pengirim == dm[0] else dm[0]
        balas = pesan_list[-1] if pesan_list and i == 1 and not dm else None
        with impersonate(pengirim):
            p = PesanLangsung.objects.create(
                workspace=ruang.workspace,
                ruang=ruang,
                pengirim=pengirim,
                penerima=penerima,
                isi=isi,
                balasan_ke=balas,
            )
        PesanLangsung.objects.filter(pk=p.pk).update(created_at=waktu, updated_at=waktu)
        p.created_at = waktu
        pesan_list.append(p)
        if penerima is not None:
            catat_pesan_dm(p)
        if rng.random() < 0.35:
            for u in rng.sample(_pelanggan(ruang), k=min(2, len(_pelanggan(ruang)))):
                if u != pengirim:
                    ReaksiPesan.objects.get_or_create(pesan=p, user=u, emoji=rng.choice(REAKSI))
        if lampiran and i == 0:
            _lampirkan(cmd, p, pengirim)

    Ruang.objects.filter(pk=ruang.pk).update(pesan_terakhir_pada=waktu)
    _status_baca(cmd, ruang, pesan_list, dm)


def _pelanggan(ruang):
    return [lg.user for lg in Langganan.objects.filter(ruang=ruang).select_related("user")[:20]]


def _status_baca(cmd, ruang, pesan_list, dm):
    """Pengirim pesan terakhir sudah membaca semuanya; sekitar 40% sisanya punya pesan belum dibaca."""
    terakhir = pesan_list[-1]
    for lg in Langganan.objects.filter(ruang=ruang):
        if lg.user_id == terakhir.pengirim_id or cmd.rng.random() > 0.4:
            batas = terakhir.created_at
        else:
            batas = pesan_list[max(0, len(pesan_list) - 3)].created_at - timedelta(seconds=1)
        Langganan.objects.filter(pk=lg.pk).update(dibaca_sampai=batas)
    if dm:
        # DM juga punya `dibaca_pada` per pesan; samakan dengan batas baca penerimanya.
        for p in pesan_list:
            batas = (
                Langganan.objects.filter(ruang=ruang, user_id=p.penerima_id)
                .values_list("dibaca_sampai", flat=True)
                .first()
            )
            if batas and p.created_at <= batas:
                PesanLangsung.objects.filter(pk=p.pk).update(dibaca_pada=p.created_at + timedelta(minutes=3))


def _lampirkan(cmd, pesan, pengirim):
    data = berkas.pdf(
        "Target Kuartal IV 2026",
        [
            "PT Paradise Perkasa (data demo)",
            "",
            "Sales & Marketing   : Rp 12,5 M",
            "Operasional         : efisiensi biaya 8%",
            "Finance & Accounting: tutup buku maks. tanggal 5",
            "HR & GA             : rekrutmen 12 posisi",
            "Teknologi Informasi : portal pelanggan v2 rilis Desember",
        ],
    )
    berkas.unggah(
        cmd.ws,
        pengirim,
        "target-q4-2026.pdf",
        data,
        "application/pdf",
        FileAsset.EntityTypeContext.CHAT_ATTACHMENT,
        entity_identifier=str(pesan.id),
    )
