# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi data demo, bagian milik tiap orang
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Yang dilihat tiap orang di sidebar & Home: pin menu, favorit, sticky, quick link.

Berkas berawalan `_` supaya Django tidak membacanya sebagai command.

Pin sidebar sengaja diisi PENUH. Bawaan upstream untuk akun baru hanya Drafts,
Your Work, Stickies, Quick links; sisanya (Views, Analytics, Archives) baru
muncul kalau orangnya menyematkannya sendiri. Untuk demo, menu yang tersembunyi
terbaca sebagai "datanya kosong", padahal cuma belum disematkan.
"""

# Module imports
from plane.db.models import Sticky, UserFavorite, WorkspaceUserLink, WorkspaceUserPreference

STICKY = [
    ("Ingat", "<p>Kirim laporan mingguan ke atasan setiap Jumat sebelum jam 15.00.</p>", "#fef3c7"),
    ("Rapat", "<p>Rapat koordinasi divisi: Senin 09.00, ruang meeting lt. 2.</p>", "#dbeafe"),
    ("To do", "<ul><li><p>Cek email klien</p></li><li><p>Update progres tugas</p></li></ul>", "#dcfce7"),
]

QUICK_LINK = [
    ("Google Drive divisi", "https://drive.google.com"),
    ("Email kantor", "https://mail.google.com"),
    ("Kalender tim", "https://calendar.google.com"),
]


def isi_pribadi(ws, user, project, rng):
    """Pin sidebar penuh, project departemennya jadi favorit, plus sticky & quick link."""
    _pin_sidebar(ws, user)
    if project is not None:
        UserFavorite.objects.get_or_create(
            workspace=ws,
            user=user,
            entity_type="project",
            entity_identifier=project.id,
            defaults={"project": project, "name": project.name},
        )
    for i, (nama, isi, warna) in enumerate(rng.sample(STICKY, k=rng.randint(1, 2))):
        Sticky.objects.create(
            workspace=ws,
            owner=user,
            name=nama,
            description_html=isi,
            background_color=warna,
            sort_order=65535 + i * 1000,
        )
    for judul, url in rng.sample(QUICK_LINK, k=2):
        WorkspaceUserLink.objects.create(workspace=ws, owner=user, title=judul, url=url)


def _pin_sidebar(ws, user):
    kunci = [k for k, _ in WorkspaceUserPreference.UserPreferenceKeys.choices]
    for i, k in enumerate(kunci):
        WorkspaceUserPreference.objects.update_or_create(
            workspace=ws,
            user=user,
            key=k,
            # Active cycles ikut dicabut bersama Cycles (KEP-50), jadi tidak disematkan.
            defaults={"is_pinned": k != "active_cycles", "sort_order": 65535 + i * 10000},
        )
