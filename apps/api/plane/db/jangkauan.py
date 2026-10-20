# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jangkauan hierarki -> keanggotaan project
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Jadikan jangkauan hierarki (KEP-29) baris `ProjectMember` yang nyata.

Plane memutuskan "boleh lihat project ini?" lewat `ProjectMember` di puluhan
tempat. Daripada menambal semuanya, jangkauan jenjang ditulis menjadi
keanggotaan biasa, persis pola direktur (`plane/db/direktur.py`) dan Super Admin
(B1). Bedanya: di sini keanggotaan juga DICABUT saat jangkauannya hilang.

## Aturan yang tidak boleh dilanggar

* Hanya baris yang tercatat di `AksesHierarki` yang boleh diubah atau dicabut.
  Keanggotaan yang sudah ada tanpa catatan adalah pengecualian eksplisit (KEP-29)
  dan dibiarkan apa adanya, termasuk role-nya.
* Struktur belum aktif (belum ada `Divisi`) = tidak melakukan apa pun. Tidak ada
  pencabutan massal karena tabel organisasi kosong.
* Pencabutan = `is_active=False`, sama dengan endpoint keanggotaan God Mode
  (`license/api/views/divisi.py`), jadi riwayat dan tugasnya tetap ada.
"""

# Python imports
import threading
from contextlib import contextmanager

# Django imports
from django.db.models.signals import post_save
from django.dispatch import receiver

_lokal = threading.local()


@contextmanager
def tunda_sinkron():
    """Matikan sinkron per-signal selama blok; pemanggil wajib sinkron sekali di akhir.

    Dipakai skrip migrasi dan endpoint yang menulis banyak baris sekaligus, supaya
    25 baris pemetaan tidak memicu 25 sinkron seluruh workspace.
    """
    sebelumnya = getattr(_lokal, "tunda", False)
    _lokal.tunda = True
    try:
        yield
    finally:
        _lokal.tunda = sebelumnya


def _ditunda():
    return getattr(_lokal, "tunda", False)


def sinkronkan_satu(workspace_id, user_id):
    """Samakan keanggotaan otomatis satu orang dengan jangkauannya. Kembalikan jumlah perubahan."""
    from plane.db.membership import jadikan_anggota_project
    from plane.db.models import AksesHierarki, ProjectMember
    from plane.utils.hierarki import jangkauan_hierarki, struktur_aktif

    if not struktur_aktif(workspace_id):
        return 0

    ingin = jangkauan_hierarki(user_id, workspace_id)
    tercatat = set(
        AksesHierarki.objects.filter(workspace_id=workspace_id, member_id=user_id).values_list("project_id", flat=True)
    )
    aktif = set(
        ProjectMember.objects.filter(
            workspace_id=workspace_id, member_id=user_id, is_active=True
        ).values_list("project_id", flat=True)
    )

    berubah = 0
    for pid, role in ingin.items():
        if pid in aktif and pid not in tercatat:
            continue  # keanggotaan eksplisit: jangan disentuh
        _, ada_ubah = jadikan_anggota_project(pid, user_id, role, workspace_id=workspace_id)
        berubah += 1 if ada_ubah else 0
        if pid not in tercatat:
            tandai_otomatis(workspace_id, pid, user_id)

    for pid in tercatat - set(ingin):
        berubah += ProjectMember.objects.filter(project_id=pid, member_id=user_id, is_active=True).update(
            is_active=False
        )
        AksesHierarki.objects.filter(project_id=pid, member_id=user_id).delete()
    return berubah


def tandai_otomatis(workspace_id, project_id, user_id):
    """Catat (project, user) sebagai akses hierarki. Skrip migrasi memakainya untuk
    "mengadopsi" keanggotaan lama yang memang lahir dari struktur, supaya ikut
    dicabut saat orangnya pindah departemen."""
    from plane.db.models import AksesHierarki

    # all_objects + hidupkan: baris yang pernah dicabut menempati slot unik (jebakan A21).
    lama = AksesHierarki.all_objects.filter(project_id=project_id, member_id=user_id).first()
    if lama is None:
        AksesHierarki.objects.create(workspace_id=workspace_id, project_id=project_id, member_id=user_id)
    elif lama.deleted_at is not None:
        AksesHierarki.all_objects.filter(pk=lama.pk).update(deleted_at=None)


def sinkronkan_workspace(workspace_id):
    """Sinkron semua orang yang berjenjang atau pernah diberi akses otomatis."""
    from plane.db.models import AksesHierarki, JabatanOrganisasi

    ids = set(JabatanOrganisasi.objects.filter(workspace_id=workspace_id).values_list("member_id", flat=True))
    # Orang yang jenjangnya sudah dicabut tetap disapu, supaya aksesnya ikut dicabut.
    ids |= set(AksesHierarki.objects.filter(workspace_id=workspace_id).values_list("member_id", flat=True))
    return sum(sinkronkan_satu(workspace_id, uid) for uid in ids)


@receiver(post_save, sender="db.JabatanOrganisasi")
def jabatan_berubah(sender, instance, **kwargs):
    """Jenjang/penempatan berubah (atau dicabut lewat soft delete) -> sinkron orangnya."""
    if not _ditunda():
        sinkronkan_satu(instance.workspace_id, instance.member_id)


@receiver(post_save, sender="db.DepartemenProject")
@receiver(post_save, sender="db.Departemen")
@receiver(post_save, sender="db.Divisi")
def struktur_berubah(sender, instance, **kwargs):
    """Project pindah departemen, departemen pindah divisi, atau record dihapus -> sinkron workspace."""
    if not _ditunda():
        sinkronkan_workspace(instance.workspace_id)
