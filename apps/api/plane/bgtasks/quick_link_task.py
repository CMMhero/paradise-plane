# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi judul & favicon quick link lama (KEP-82)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Quick link yang dibuat sebelum KEP-82 belum punya judul situs & favicon.

Daftar quick link memicu task ini untuk baris yang belum pernah diambil, jadi link
lama terisi sendiri tanpa migrasi yang menembak internet. Link baru diisi langsung
saat dibuat, tidak lewat sini.
"""

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import QuickLinkBersama, WorkspaceUserLink
from plane.utils.exception_logger import log_exception
from plane.utils.quick_link import ambil_dari_situs, perlu_diisi

JENIS_PRIBADI = "pribadi"
JENIS_BERSAMA = "bersama"
_MODEL = {JENIS_PRIBADI: WorkspaceUserLink, JENIS_BERSAMA: QuickLinkBersama}
MAKS_PER_TASK = 50


@shared_task
def isi_metadata_quick_link(jenis: str, ids: list[str]) -> None:
    model = _MODEL.get(jenis)
    if model is None:
        return
    for link in model.objects.filter(id__in=ids[:MAKS_PER_TASK]):
        # Diperiksa ulang: dua tab yang dibuka bersamaan memicu dua task untuk baris sama.
        if not perlu_diisi(link.metadata):
            continue
        try:
            link.metadata = {**(link.metadata or {}), **ambil_dari_situs(link.url)}
            link.save(update_fields=["metadata", "updated_at"])
        except Exception as e:  # noqa: BLE001 - satu link rusak tidak boleh menghentikan sisanya
            log_exception(e, warning=True)
