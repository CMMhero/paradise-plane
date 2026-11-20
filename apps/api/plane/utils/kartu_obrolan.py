# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kabar aktivitas sebagai kartu obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kabar aktivitas yang relevan untuk seseorang, sebagai kartu di DM obrolan.

## Ke mana kartunya dikirim

KEP-90 (5 Nov 2026): kalau aksinya punya pelaku manusia yang bukan penerimanya
sendiri, kartu masuk DM antara PELAKU dan ORANG YANG TERDAMPAK, dengan pelaku
sebagai pengirim. "Siapa yang terdampak" = penerima baris Notification
(assignee, penyetuju, pembuat, yang disebut), jadi tiap orang dapat DM-nya
sendiri. Pelaku melihat kartu itu di DM-nya sebagai pesan keluar.

Yang tidak punya lawan bicara (aksi sistem/otomasi, pelaku bot, aksi atas tugas
sendiri) TIDAK dijadikan kartu. Dulu kartu itu masuk ruang kabar pribadi
"Paradise"; ruang itu dihapus atas permintaan user (migrasi 0181). Kabarnya
tetap sampai lewat inbox dan email.

`ENABLE_TUGAS_KE_DM` mati = tidak ada kartu sama sekali. Penugasan tetap lewat
`tugas_ke_dm_task` (kartu dengan rincian lengkap), jadi di sini dilewati selama
saklar menyala supaya tidak dobel.

## Pemicunya

Baris `Notification` yang sudah lolos aturan bisnis dan saklar inbox penerima
(`notification_task`, `notifikasi_persetujuan`). Modul ini TIDAK memutuskan
siapa yang berhak dikabari; yang tidak menerima baris inbox tidak menerima kartu.

## Biaya

Satu putaran notifikasi = satu kueri tugas (+project, state), satu kueri
assignee, satu kueri bot, lalu satu DM dan satu INSERT per kartu.

Semua fungsi publik menelan galatnya sendiri: kartu obrolan tidak boleh
menggagalkan notifikasi aslinya.
"""

import logging

from plane.db.models import Issue, IssueAssignee, JenisPesan, PesanLangsung, User
from plane.utils.akses_privat import penonton_tugas_ids
from plane.utils.chat_ruang import ruang_dm
from plane.utils.kanal_sistem import kirim_pesan_sistem
from plane.utils.obrolan_siaran import siarkan
from plane.utils.teks_html import teks_polos

logger = logging.getLogger("plane.worker")

BATAS_CUPLIKAN = 200
BATAS_ASSIGNEE = 5
# Kolom aktivitas yang nilainya HTML editor, bukan teks biasa. Kabar lebur
# (`gabungan.perubahan`) tidak pernah memuat keduanya: komentar hanya dihitung
# dan deskripsi tidak dilebur (gabung_kabar.KOLOM_LANGSUNG).
KOLOM_HTML = frozenset({"comment", "description"})


def _potong(teks) -> str:
    return teks if len(teks) <= BATAS_CUPLIKAN else teks[: BATAS_CUPLIKAN - 1] + "…"


def _cuplikan(teks) -> str:
    return _potong(" ".join(str(teks or "").split()))


def _cuplikan_kolom(field, nilai) -> str:
    """Cuplikan nilai satu kolom. HTML editor jadi teks dengan `@Nama` dan baris
    per paragraf; nilai lain (nama state, label) cukup dirapikan spasinya."""
    if field in KOLOM_HTML:
        return _potong(teks_polos(nilai))
    return _cuplikan(nilai)


def jenis_dari_notifikasi(notif) -> str:
    """Pilih jenis kartu dari satu baris Notification. '' = tidak dikirim."""
    data = notif.data or {}
    aktivitas = data.get("issue_activity") or {}
    field = aktivitas.get("field")
    if field == "approval":
        return JenisPesan.PERSETUJUAN
    if (notif.sender or "").endswith(":mentioned"):
        return JenisPesan.MENTION
    # Kabar lebur (utils/gabung_kabar.py): ada perubahan kolom = kartu pembaruan,
    # hanya komentar = kartu komentar.
    gabungan = data.get("gabungan") or {}
    if gabungan.get("perubahan") and notif.entity_name == "issue":
        return JenisPesan.PEMBARUAN
    if field == "comment":
        return JenisPesan.KOMENTAR
    if field == "assignees" and str(aktivitas.get("new_identifier")) == str(notif.receiver_id):
        return JenisPesan.TUGAS
    if notif.entity_name == "issue":
        return JenisPesan.PEMBARUAN
    return ""


def _tugas_ke_dm_aktif() -> bool:
    from plane.utils.saklar_instance import ENABLE_TUGAS_KE_DM, saklar_aktif  # noqa: PLC0415

    try:
        return saklar_aktif(ENABLE_TUGAS_KE_DM)
    except Exception:  # noqa: BLE001
        return True


def data_tugas(issue, assignee_ids=None) -> dict:
    """Bagian `tugas` dan `project` muatan kartu. Murni dari objek yang sudah dimuat."""
    project = issue.project
    state = issue.state
    return {
        "project": {"id": str(project.id), "nama": project.name, "identifier": project.identifier},
        "tugas": {
            "id": str(issue.id),
            "nomor": f"{project.identifier}-{issue.sequence_id}",
            "judul": _cuplikan(issue.name),
            "state": state.name if state else "",
            "state_group": state.group if state else "",
            "prioritas": issue.priority or "",
            "tenggat": issue.target_date.isoformat() if issue.target_date else None,
            "assignees": [str(a) for a in (assignee_ids or [])][:BATAS_ASSIGNEE],
        },
    }


def _muat_tugas(issue_ids) -> tuple:
    """({str(issue_id): Issue}, {str(issue_id): [assignee]}).

    Kunci SELALU string. `notification_task` membangun baris Notification di
    memori dengan `entity_identifier` berupa string, sedangkan baris yang dibaca
    dari database membawa UUID. Kunci UUID membuat setiap kartu dari jalur
    Celery (komentar, sebutan, pembaruan) terlewat diam-diam, padahal uji yang
    membaca baris dari database lolos.
    """
    ids = {str(i) for i in issue_ids}
    issues = {
        str(i.id): i for i in Issue.objects.filter(id__in=ids).select_related("project", "project__workspace", "state")
    }
    assignees = {}
    for issue_id, user_id in IssueAssignee.objects.filter(issue_id__in=ids).values_list("issue_id", "assignee_id"):
        assignees.setdefault(str(issue_id), []).append(user_id)
    return issues, assignees


BATAS_PERUBAHAN = 6


def _ringkas_gabungan(notif) -> dict:
    """Bagian `detail` kartu untuk kabar lebur: jumlah komentar dan daftar perubahan."""
    gabungan = (notif.data or {}).get("gabungan") or {}
    if not gabungan:
        return {}
    perubahan = []
    for p in (gabungan.get("perubahan") or [])[:BATAS_PERUBAHAN]:
        if "tambah" in p or "hapus" in p:
            perubahan.append(
                {
                    "field": p.get("field") or "",
                    "tambah": [_cuplikan(x) for x in (p.get("tambah") or [])][:BATAS_ASSIGNEE],
                    "hapus": [_cuplikan(x) for x in (p.get("hapus") or [])][:BATAS_ASSIGNEE],
                }
            )
        else:
            perubahan.append(
                {"field": p.get("field") or "", "lama": _cuplikan(p.get("lama")), "baru": _cuplikan(p.get("baru"))}
            )
    return {"jumlah_komentar": int(gabungan.get("komentar") or 0), "perubahan": perubahan}


def _detail(jenis, notif) -> dict:
    aktivitas = (notif.data or {}).get("issue_activity") or {}
    if jenis == JenisPesan.KOMENTAR:
        return {"komentar": _cuplikan_kolom("comment", aktivitas.get("new_value")), **_ringkas_gabungan(notif)}
    if jenis == JenisPesan.PEMBARUAN:
        field = aktivitas.get("field") or ""
        return {
            "field": field,
            "lama": _cuplikan_kolom(field, aktivitas.get("old_value")),
            "baru": _cuplikan_kolom(field, aktivitas.get("new_value")),
            **_ringkas_gabungan(notif),
        }
    if jenis == JenisPesan.PERSETUJUAN:
        return {"verb": aktivitas.get("verb") or ""}
    return {}


def ringkasan(jenis, muatan) -> str:
    """`isi` cadangan untuk pencarian dan peramban lama. Bahasa Inggris, singkat."""
    tugas = muatan.get("tugas") or {}
    judul = f"{tugas.get('nomor', '')} {tugas.get('judul', '')}".strip()
    label = {
        JenisPesan.TUGAS: "Assigned to you",
        JenisPesan.MENTION: "You were mentioned",
        JenisPesan.KOMENTAR: "New comment",
        JenisPesan.PEMBARUAN: "Work item updated",
        JenisPesan.PERSETUJUAN: "Approval",
    }.get(jenis, "Update")
    return f"{label}: {judul}"


def kirim_kartu_notifikasi(notifs, persetujuan=None) -> int:
    """Satu kartu per baris Notification yang relevan. Mengembalikan jumlahnya.

    `persetujuan` = {"id", "status", "keputusan", "alasan"}, hanya untuk baris
    persetujuan; tanpanya tombol Approve/Reject tidak bisa memanggil apa pun.
    """
    try:
        return _kirim(list(notifs), persetujuan)
    except Exception:  # noqa: BLE001
        logger.exception("kartu-obrolan: gagal mengirim kartu dari %s notifikasi", len(list(notifs or [])))
        return 0


def _kirim(notifs, persetujuan) -> int:
    if not _tugas_ke_dm_aktif():
        return 0
    pilihan = []
    for n in notifs:
        jenis = jenis_dari_notifikasi(n)
        if not jenis or n.receiver_id is None or n.entity_identifier is None:
            continue
        # Penugasan sudah jadi kartu di DM pemberi tugas (`tugas_ke_dm_task`); jangan dobel.
        if jenis == JenisPesan.TUGAS:
            continue
        pilihan.append((jenis, n))
    bot = _id_bot({n.triggered_by_id for _, n in pilihan if n.triggered_by_id})
    pilihan = [(jenis, n) for jenis, n in pilihan if _pelaku_manusia_lain(n, bot)]
    if not pilihan:
        return 0

    issues, assignees = _muat_tugas({n.entity_identifier for _, n in pilihan})
    jumlah = 0
    for jenis, n in pilihan:
        issue = issues.get(str(n.entity_identifier))
        if issue is None:
            continue
        # P29: kartu tugas privat hanya untuk yang boleh melihatnya, apa pun asal barisnya.
        if issue.is_private and not penonton_tugas_ids(issue, [n.receiver_id]):
            continue
        muatan = _muatan(jenis, n, issue, assignees)
        if jenis == JenisPesan.PERSETUJUAN and persetujuan:
            muatan["persetujuan"] = {k: (str(v) if v is not None else None) for k, v in persetujuan.items()}
        # KEP-90: kartu masuk DM pelaku <-> orang yang terdampak, pelaku sebagai
        # pengirim. Id kartu yang ditetapkan notification_task: kabar yang dilebur
        # ke baris ini nanti menyunting kartu yang sama (`perbarui_kartu_notifikasi`).
        kirim_pesan_sistem(
            ruang_dm(n.workspace_id, n.triggered_by_id, n.receiver_id),
            jenis,
            muatan,
            ringkasan(jenis, muatan),
            pengirim_id=n.triggered_by_id,
            penerima_id=n.receiver_id,
            pesan_id=(n.data or {}).get("kartu_id"),
        )
        jumlah += 1
    return jumlah


def _muatan(jenis, n, issue, assignees) -> dict:
    return {
        "aksi": jenis,
        "aktor": str(n.triggered_by_id) if n.triggered_by_id else None,
        # Siapa yang diberi kabar. Pembaca kartu perlu tahu ini untuk
        # kalimat penugasan ("Anda menugaskan X" vs "X menugaskan Anda").
        "penerima": str(n.receiver_id),
        "workspace_slug": issue.project.workspace.slug,
        **data_tugas(issue, assignees.get(str(issue.id))),
        "detail": _detail(jenis, n),
    }


def perbarui_kartu_notifikasi(diperbarui, dihapus=()) -> int:
    """Sunting di tempat kartu milik baris Notification yang baru dilebur.

    Satu rentetan suntingan = satu kartu yang isinya selalu terkini, bukan satu
    kartu per aktivitas. Baris yang semua perubahannya batal (A -> B -> A)
    kartunya diberi tanda `batal` alih-alih dihapus: menghapus meninggalkan
    batu nisan "pesan dihapus" yang lebih membingungkan daripada kabarnya.
    Kartu yang tidak ditemukan (dikirim sebelum fitur ini, atau tidak pernah
    dikirim karena saklar) dilewati. Menelan galatnya sendiri.
    """
    try:
        return _perbarui(list(diperbarui or []), list(dihapus or []))
    except Exception:  # noqa: BLE001
        logger.exception("kartu-obrolan: gagal menyunting kartu dari %s notifikasi", len(list(diperbarui or [])))
        return 0


def _perbarui(diperbarui, dihapus) -> int:
    peta = {str((n.data or {}).get("kartu_id")): (n, False) for n in diperbarui if (n.data or {}).get("kartu_id")}
    peta.update({str((n.data or {}).get("kartu_id")): (n, True) for n in dihapus if (n.data or {}).get("kartu_id")})
    if not peta:
        return 0
    kartu = {
        str(p.id): p
        for p in PesanLangsung.objects.filter(pk__in=list(peta), jenis__in=[JenisPesan.PEMBARUAN, JenisPesan.KOMENTAR])
    }
    if not kartu:
        return 0
    issues, assignees = _muat_tugas({peta[k][0].entity_identifier for k in kartu})
    jumlah = 0
    for kunci, pesan in kartu.items():
        n, batal = peta[kunci]
        muatan = dict(pesan.muatan or {})
        if batal:
            muatan["detail"] = {**(muatan.get("detail") or {}), "batal": True}
        else:
            issue = issues.get(str(n.entity_identifier))
            jenis = jenis_dari_notifikasi(n)
            if issue is None or jenis not in (JenisPesan.PEMBARUAN, JenisPesan.KOMENTAR):
                continue
            muatan = _muatan(jenis, n, issue, assignees)
            pesan.jenis = jenis
        pesan.muatan = muatan
        pesan.isi = ringkasan(pesan.jenis, muatan)
        pesan.save(update_fields=["muatan", "jenis", "isi", "updated_at"])
        siarkan(pesan.ruang_id, "sunting", None)
        jumlah += 1
    return jumlah


def _id_bot(user_ids) -> set:
    """Id pelaku yang bot (impor, integrasi). Kartunya tidak dikirim: DM dengan
    bot adalah percakapan yang tidak bisa dibalas siapa pun."""
    if not user_ids:
        return set()
    return {str(u) for u in User.objects.filter(id__in=user_ids, is_bot=True).values_list("id", flat=True)}


def _pelaku_manusia_lain(notif, bot_ids) -> bool:
    """Kartu ini punya pelaku manusia yang BUKAN penerimanya sendiri."""
    pelaku = notif.triggered_by_id
    return bool(pelaku) and str(pelaku) != str(notif.receiver_id) and str(pelaku) not in bot_ids


def tandai_persetujuan_diputuskan(persetujuan_id, status) -> int:
    """Kartu permintaan persetujuan yang sudah diputuskan kehilangan tombolnya.

    Diperbarui di tempat, bukan dibiarkan basi: tanpa ini atasan kedua menekan
    Approve pada kartu lama lalu menerima galat "sudah disetujui".
    """
    try:
        jumlah = 0
        for pesan in PesanLangsung.objects.filter(
            jenis=JenisPesan.PERSETUJUAN, muatan__persetujuan__id=str(persetujuan_id)
        ):
            muatan = dict(pesan.muatan or {})
            muatan["persetujuan"] = {**(muatan.get("persetujuan") or {}), "status": status}
            pesan.muatan = muatan
            pesan.save(update_fields=["muatan", "updated_at"])
            siarkan(pesan.ruang_id, "sunting", None)
            jumlah += 1
        return jumlah
    except Exception:  # noqa: BLE001
        logger.exception("kartu-obrolan: gagal menandai persetujuan %s", persetujuan_id)
        return 0
