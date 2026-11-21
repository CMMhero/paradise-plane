# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bidang tugas yang dikunci atau dibuka per peran
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bidang mana yang diubah sebuah tulisan tugas, dan apakah God Mode mengizinkannya.

Dua aturan God Mode (area B):

    TASK_FIELDS_LOCKED_FOR_STAFF   bidang yang tidak bisa diubah staf (di bawah Leader)
    TASK_FIELDS_OPEN_TO_MEMBERS    bidang yang bisa diubah anggota project mana pun,
                                   walau ia tidak terlibat di tugas itu

Penegaknya satu: `galat_ubah_tugas` di utils/hierarki.py, yang dipanggil PATCH tugas
dan serializer tugas. Bawaan keduanya kosong, dan selama kosong modul ini tidak
membaca apa pun dari database.

Kenapa "benar-benar berubah", bukan "ada di payload": beberapa layar mengirim ulang
isi formulir yang tidak disentuh (alasan yang sama dengan `tenggat_diubah`). Kunci
payload yang tidak dikenal tidak pernah dianggap bidang terbuka.
"""

from dataclasses import dataclass

from plane.utils import aturan
from plane.utils.aturan.area_tugas import PILIHAN_BIDANG, TASK_FIELDS_LOCKED_FOR_STAFF, TASK_FIELDS_OPEN_TO_MEMBERS

# Kunci payload (web app dan API v1) -> bidang aturan.
_KUNCI_BIDANG = {
    "name": "name",
    "description_html": "description",
    "description_binary": "description",
    "description_json": "description",
    "description": "description",
    "description_stripped": "description",
    "state_id": "state",
    "state": "state",
    "priority": "priority",
    "start_date": "start_date",
    "label_ids": "labels",
    "labels": "labels",
    "estimate_point": "estimate",
    "parent_id": "parent",
    "parent": "parent",
}
# Ikut terkirim saat kartu diseret; bukan isi tugas.
_KUNCI_NETRAL = frozenset({"sort_order"})
_LABEL_BIDANG = dict(PILIHAN_BIDANG)


@dataclass(frozen=True)
class BidangDiubah:
    bidang: frozenset
    # Ada kunci lain yang ikut diubah (bukan bidang di atas, bukan netral).
    lain: bool


def _id(nilai):
    nilai = getattr(nilai, "pk", nilai)
    return None if nilai in (None, "") else str(nilai)


def _tanggal(nilai):
    return None if nilai in (None, "") else str(nilai)[:10]


def _berubah(issue, kunci, nilai) -> bool:
    if kunci == "name":
        return str(nilai) != (issue.name or "")
    if kunci == "description_html":
        return (nilai or "") != (issue.description_html or "")
    if kunci in ("description_binary", "description_json", "description", "description_stripped"):
        # Tanpa description_html tidak ada yang bisa dibandingkan dengan aman.
        return True
    if kunci in ("state_id", "state"):
        return _id(nilai) != _id(issue.state_id)
    if kunci == "priority":
        return str(nilai) != str(issue.priority)
    if kunci == "start_date":
        return _tanggal(nilai) != _tanggal(issue.start_date)
    if kunci in ("label_ids", "labels"):
        from plane.db.models import IssueLabel  # noqa: PLC0415

        baru = {_id(v) for v in (nilai or [])}
        lama = {str(v) for v in IssueLabel.objects.filter(issue_id=issue.id).values_list("label_id", flat=True)}
        return baru != lama
    if kunci == "estimate_point":
        return _id(nilai) != _id(issue.estimate_point_id)
    return _id(nilai) != _id(issue.parent_id)


def bidang_diubah(issue, data):
    """`BidangDiubah` untuk tulisan `data` ke `issue`, atau None.

    None kalau tidak ada payload, atau kalau kedua aturan bidang masih kosong
    (bawaan): tidak ada yang perlu dinilai, jadi tidak ada kueri.
    """
    if issue is None or not hasattr(data, "keys"):
        return None
    if not aturan.get_list(TASK_FIELDS_LOCKED_FOR_STAFF) and not aturan.get_list(TASK_FIELDS_OPEN_TO_MEMBERS):
        return None
    from plane.utils.task_access import tenggat_diubah  # noqa: PLC0415

    bidang, lain = set(), False
    for kunci in data.keys():
        if kunci in _KUNCI_NETRAL:
            continue
        if kunci == "target_date":
            lain = lain or tenggat_diubah(issue, data)
            continue
        nama = _KUNCI_BIDANG.get(kunci)
        if nama is None:
            lain = True
        elif nama not in bidang and _berubah(issue, kunci, data.get(kunci)):
            bidang.add(nama)
    return BidangDiubah(frozenset(bidang), lain)


def galat_bidang_staf(staf, diubah):
    """Pesan galat kalau `staf` mengubah bidang yang dikunci untuk staf, selain itu None."""
    if not staf or diubah is None or not diubah.bidang:
        return None
    terkunci = [k for k in aturan.get_list(TASK_FIELDS_LOCKED_FOR_STAFF) if k in diubah.bidang]
    if not terkunci:
        return None
    return f"Staf tidak dapat mengubah bidang ini: {', '.join(_LABEL_BIDANG[k] for k in terkunci)}."


def hanya_bidang_terbuka(diubah) -> bool:
    """True kalau tulisan ini hanya mengubah bidang yang dibuka untuk semua anggota project."""
    if diubah is None or not diubah.bidang or diubah.lain:
        return False
    return diubah.bidang <= set(aturan.get_list(TASK_FIELDS_OPEN_TO_MEMBERS))
