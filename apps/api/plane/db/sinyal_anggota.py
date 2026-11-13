# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: sinyal "anggota project berubah"
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Keanggotaan project berubah = layar orang yang terkena ikut menyegarkan diri.

Mendengar `ProjectMember` yang disimpan atau dihapus satu per satu (tambah,
ubah peran, keluarkan, keluar sendiri). Penulisan MASSAL (`bulk_create`,
`bulk_update`, `QuerySet.update`) tidak memicu signal Django, jadi jalur massal
yang penting (tambah anggota lewat layar, terima undangan) memanggil
`siarkan_anggota_project` sendiri. Sinkron jenjang organisasi yang menulis lewat
`update()` tidak menyiarkan apa pun; layar mengejarnya lewat jam cadangan.

Menelan galatnya sendiri: lihat `plane/utils/sinyal_data.py`.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from plane.db.models import ProjectMember
from plane.utils.sinyal_data import siarkan_anggota_project


@receiver(post_save, sender=ProjectMember)
@receiver(post_delete, sender=ProjectMember)
def anggota_project_berubah(sender, instance, **kwargs):
    siarkan_anggota_project(instance.project_id, user_ids=[instance.member_id])
