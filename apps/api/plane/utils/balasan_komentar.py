# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: balasan komentar (utas satu tingkat)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Balasan pada komentar work item.

`IssueComment.parent` sudah ada di model dari upstream, tetapi tak ada yang
mengisi atau membacanya. Aturan yang dipakai sekarang:

- Utas hanya SATU tingkat. Membalas sebuah balasan menempelkan balasan baru ke
  AKAR utas (induk dari balasan itu). Orang yang dibalas disebut lewat mention
  di isi komentar, jadi ia tetap dikabari.
- Induk harus komentar yang masih hidup pada work item yang SAMA. UUID dari work
  item lain, komentar yang sudah dihapus, atau nilai bukan UUID ditolak.
- `parent` tidak bisa diubah sesudah komentar dibuat (hanya-baca di serializer).
- Menghapus induk ikut menghapus balasannya (lihat `hapus_balasan`). Pilihan ini
  disengaja: jalur hapus lunak model sudah menjalar ke anak lewat
  `soft_delete_related_objects`, dan Trash memulihkan induk bersama anaknya.
  Memutus balasan jadi komentar mandiri akan membuatnya kehilangan konteks.
"""

from uuid import UUID

from plane.db.models import IssueComment


def induk_balasan(workspace_slug: str, project_id, issue_id, parent_id) -> IssueComment | None:
    """Akar utas tempat balasan baru harus menempel, atau None bila `parent_id` tak sah.

    `IssueComment.objects` sudah menyaring baris yang dihapus lunak.
    """
    try:
        parent_uuid = UUID(str(parent_id))
    except (TypeError, ValueError, AttributeError):
        return None
    induk = IssueComment.objects.filter(
        pk=parent_uuid,
        issue_id=issue_id,
        project_id=project_id,
        workspace__slug=workspace_slug,
    ).first()
    if induk is None or induk.parent_id is None:
        return induk
    # Membalas sebuah balasan: naik ke akar. Akar yang sudah dihapus = tidak sah.
    return IssueComment.objects.filter(pk=induk.parent_id, issue_id=issue_id, project_id=project_id).first()


def hapus_balasan(induk: IssueComment) -> int:
    """Hapus lunak semua balasan hidup milik `induk`. Panggil SESUDAH `induk.delete()`.

    Urutannya penting: Trash memulihkan anak yang `deleted_at >= deleted_at` induk,
    jadi anak harus dihapus belakangan. Tiap balasan dihapus lewat `delete()` model
    (bukan `update()` massal) supaya reaksi dan deskripsinya ikut dibersihkan.
    """
    jumlah = 0
    for balasan in IssueComment.objects.filter(parent_id=induk.pk):
        balasan.delete()
        jumlah += 1
    return jumlah
