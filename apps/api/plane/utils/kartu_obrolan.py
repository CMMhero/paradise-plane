# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kabar aktivitas sebagai kartu obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kabar aktivitas yang relevan untuk seseorang, sebagai kartu di ruang "Paradise".

## Ke mana kartunya dikirim

KEP-90 (5 Nov 2026, permintaan user, membalik aturan lama): kalau aksinya punya
pelaku manusia yang bukan penerimanya sendiri, kartu masuk DM antara PELAKU dan
ORANG YANG TERDAMPAK, dengan pelaku sebagai pengirim. "Siapa yang terdampak" =
penerima baris Notification (assignee, penyetuju, pembuat, yang disebut), jadi
tiap orang dapat DM-nya sendiri. Pelaku melihat kartu itu di DM-nya sebagai
pesan keluar.

Ruang kabar pribadi (`kabar:<user_id>`, nama "Paradise") tetap dipakai untuk
yang tak punya lawan bicara: aksi sistem/otomasi (tanpa pelaku), pelaku bot,
dan aksi atas tugas sendiri.

Satu saklar untuk keduanya: `ENABLE_TUGAS_KE_DM`. Mati = semua kartu kembali ke
ruang kabar. Penugasan tetap lewat `tugas_ke_dm_task` (kartu dengan rincian
lengkap), jadi di sini dilewati selama saklar menyala supaya tidak dobel.

## Pemicunya

Baris `Notification` yang sudah lolos aturan bisnis dan saklar inbox penerima
(`notification_task`, `notifikasi_persetujuan`), plus undangan project
(`project_add_user_email`). Modul ini TIDAK memutuskan siapa yang berhak dikabari;
yang tidak menerima baris inbox tidak menerima kartu.

## Biaya

Satu putaran notifikasi = satu kueri tugas (+project, state), satu kueri
assignee, satu kueri ruang kabar yang sudah ada, lalu satu INSERT per kartu.
Tidak ada kueri per baris.

Semua fungsi publik menelan galatnya sendiri: kartu obrolan tidak boleh
menggagalkan notifikasi aslinya.
"""

import logging

from plane.db.models import (
    AWALAN_KABAR,
    Issue,
    IssueAssignee,
    JenisPesan,
    PesanLangsung,
    Ruang,
    User,
)
from plane.utils.chat_ruang import ruang_dm
from plane.utils.kanal_sistem import kirim_pesan_sistem, kunci_kabar, ruang_kabar
from plane.utils.obrolan_siaran import siarkan

logger = logging.getLogger("plane.worker")

BATAS_CUPLIKAN = 200
BATAS_ASSIGNEE = 5


def _cuplikan(teks) -> str:
    rapi = " ".join(str(teks or "").split())
    return rapi if len(rapi) <= BATAS_CUPLIKAN else rapi[: BATAS_CUPLIKAN - 1] + "…"


def jenis_dari_notifikasi(notif) -> str:
    """Pilih jenis kartu dari satu baris Notification. '' = tidak dikirim."""
    data = notif.data or {}
    aktivitas = data.get("issue_activity") or {}
    field = aktivitas.get("field")
    if field == "approval":
        return JenisPesan.PERSETUJUAN
    if (notif.sender or "").endswith(":mentioned"):
        return JenisPesan.MENTION
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


def _peta_ruang_kabar(workspace_id, user_ids) -> dict:
    """Ruang kabar yang sudah ada, satu kueri; yang belum ada dibuat satu per satu."""
    ada = {
        r.kunci_sistem[len(AWALAN_KABAR) :]: r
        for r in Ruang.objects.filter(workspace_id=workspace_id, kunci_sistem__in=[kunci_kabar(u) for u in user_ids])
    }
    return {str(u): ada.get(str(u)) or ruang_kabar(workspace_id, u) for u in user_ids}


def _detail(jenis, notif) -> dict:
    aktivitas = (notif.data or {}).get("issue_activity") or {}
    if jenis == JenisPesan.KOMENTAR:
        return {"komentar": _cuplikan(aktivitas.get("new_value"))}
    if jenis == JenisPesan.PEMBARUAN:
        return {
            "field": aktivitas.get("field") or "",
            "lama": _cuplikan(aktivitas.get("old_value")),
            "baru": _cuplikan(aktivitas.get("new_value")),
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
        JenisPesan.PROJECT: "Added to project",
    }.get(jenis, "Update")
    if jenis == JenisPesan.PROJECT:
        return f"{label}: {(muatan.get('project') or {}).get('nama', '')}"
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
    tugas_dm = None
    pilihan = []
    for n in notifs:
        jenis = jenis_dari_notifikasi(n)
        if not jenis or n.receiver_id is None or n.entity_identifier is None:
            continue
        # Penugasan sudah jadi kartu di DM pemberi tugas; jangan dobel.
        if jenis == JenisPesan.TUGAS and str(n.triggered_by_id) != str(n.receiver_id):
            tugas_dm = _tugas_ke_dm_aktif() if tugas_dm is None else tugas_dm
            if tugas_dm:
                continue
        pilihan.append((jenis, n))
    if not pilihan:
        return 0

    issues, assignees = _muat_tugas({n.entity_identifier for _, n in pilihan})
    dm = _tugas_ke_dm_aktif() if tugas_dm is None else tugas_dm
    bot = _id_bot({n.triggered_by_id for _, n in pilihan if n.triggered_by_id}) if dm else set()
    lewat_dm = {id(n) for _, n in pilihan if dm and _pelaku_manusia_lain(n, bot)}
    per_ws = {}
    for _, n in pilihan:
        if id(n) not in lewat_dm:
            per_ws.setdefault(str(n.workspace_id), set()).add(str(n.receiver_id))
    ruang = {ws: _peta_ruang_kabar(ws, ids) for ws, ids in per_ws.items()}

    jumlah = 0
    for jenis, n in pilihan:
        issue = issues.get(str(n.entity_identifier))
        if issue is None:
            continue
        muatan = {
            "aksi": jenis,
            "aktor": str(n.triggered_by_id) if n.triggered_by_id else None,
            # Siapa yang diberi kabar. Pembaca kartu perlu tahu ini untuk
            # kalimat penugasan ("Anda menugaskan X" vs "X menugaskan Anda").
            "penerima": str(n.receiver_id),
            "workspace_slug": issue.project.workspace.slug,
            **data_tugas(issue, assignees.get(str(issue.id))),
            "detail": _detail(jenis, n),
        }
        if jenis == JenisPesan.PERSETUJUAN and persetujuan:
            muatan["persetujuan"] = {k: (str(v) if v is not None else None) for k, v in persetujuan.items()}
        if id(n) in lewat_dm:
            # KEP-90: kartu masuk DM pelaku <-> orang yang terdampak, pelaku
            # sebagai pengirim. Tiap penerima notifikasi dapat DM-nya sendiri.
            tujuan = ruang_dm(n.workspace_id, n.triggered_by_id, n.receiver_id)
            kirim_pesan_sistem(
                tujuan,
                jenis,
                muatan,
                ringkasan(jenis, muatan),
                pengirim_id=n.triggered_by_id,
                penerima_id=n.receiver_id,
            )
        else:
            tujuan = ruang[str(n.workspace_id)][str(n.receiver_id)]
            kirim_pesan_sistem(tujuan, jenis, muatan, ringkasan(jenis, muatan))
        jumlah += 1
    return jumlah


def _id_bot(user_ids) -> set:
    """Id pelaku yang bot (impor, integrasi). Kartunya tetap ke ruang kabar:
    DM dengan bot adalah percakapan yang tidak bisa dibalas siapa pun."""
    if not user_ids:
        return set()
    return {str(u) for u in User.objects.filter(id__in=user_ids, is_bot=True).values_list("id", flat=True)}


def _pelaku_manusia_lain(notif, bot_ids) -> bool:
    """Kartu ini punya pelaku manusia yang BUKAN penerimanya sendiri."""
    pelaku = notif.triggered_by_id
    return bool(pelaku) and str(pelaku) != str(notif.receiver_id) and str(pelaku) not in bot_ids


def kartu_ditambahkan_ke_project(project_member, pengundang_id) -> None:
    """Kartu "ditambahkan ke project" untuk anggota baru project."""
    try:
        from plane.utils.preferensi_email import boleh  # noqa: PLC0415

        penerima_id = project_member.member_id
        if str(penerima_id) == str(pengundang_id) or not boleh(penerima_id, "inbox_assigned"):
            return
        project = project_member.project
        muatan = {
            "aksi": JenisPesan.PROJECT,
            "aktor": str(pengundang_id) if pengundang_id else None,
            "workspace_slug": project.workspace.slug,
            "project": {"id": str(project.id), "nama": project.name, "identifier": project.identifier},
            "peran": project_member.role,
        }
        ruang = ruang_kabar(project.workspace_id, penerima_id)
        kirim_pesan_sistem(ruang, JenisPesan.PROJECT, muatan, ringkasan(JenisPesan.PROJECT, muatan))
    except Exception:  # noqa: BLE001
        logger.exception("kartu-obrolan: gagal mengirim kartu project untuk %s", getattr(project_member, "id", "?"))


def kartu_disebut_di_obrolan(pesan, ruang, penerima_ids) -> int:
    """Kartu "X menyebutmu di #kanal" ke ruang kabar tiap orang yang disebut.

    Hanya untuk kanal. Di DM orangnya sudah menerima pesannya sendiri, jadi kartu
    kedua cuma gema. Saklar `inbox_mention` dihormati, sama dengan sebutan di
    komentar work item.
    """
    try:
        from plane.utils.preferensi_email import penyaring  # noqa: PLC0415

        # Id dibiarkan bertipe UUID: `penyaring` mencocokkan preferensi lewat
        # kunci UUID, dan string membuatnya diam-diam jatuh ke bawaan.
        tujuan = penyaring({u for u in penerima_ids if str(u) != str(pesan.pengirim_id)}, "inbox_mention")
        if not tujuan:
            return 0
        from plane.utils.rujukan_obrolan import kanal_privat_milik, samarkan  # noqa: PLC0415

        urut = sorted(tujuan, key=str)
        peta = _peta_ruang_kabar(ruang.workspace_id, urut)
        # KEP-91: cuplikan disamarkan PER PENERIMA. Rujukan #kanal-privat di
        # pesan tidak boleh terbaca lewat kartu oleh yang bukan anggotanya.
        # Satu kueri keanggotaan untuk semua penerima.
        privat = kanal_privat_milik(urut, [pesan.muatan])
        for uid in urut:
            teks, _ = samarkan(pesan.isi, pesan.muatan, uid, boleh=privat.get(str(uid), set()))
            muatan = {
                "aksi": JenisPesan.MENTION,
                "aktor": str(pesan.pengirim_id) if pesan.pengirim_id else None,
                "workspace_slug": ruang.workspace.slug,
                "obrolan": {
                    "ruang_id": str(ruang.id),
                    "nama": ruang.nama or "",
                    "tipe": ruang.tipe,
                    "pesan_id": str(pesan.id),
                },
                "detail": {"komentar": _cuplikan(teks)},
            }
            isi = f"You were mentioned in #{ruang.nama or ''}: {_cuplikan(teks)}"
            kirim_pesan_sistem(peta[str(uid)], JenisPesan.MENTION, muatan, isi)
        return len(tujuan)
    except Exception:  # noqa: BLE001
        logger.exception("kartu-obrolan: gagal mengirim kartu sebutan untuk pesan %s", getattr(pesan, "id", "?"))
        return 0


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
