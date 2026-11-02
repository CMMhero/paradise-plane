# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: navigasi & tata letak per member dari God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Navigasi sidebar dan tata letak work item SATU member, dibaca/diubah dari God Mode.

Pasangan dari bagian `navigasi` dan `work_items` di `bawaan_member.py`: bawaan
mengatur akun baru, modul ini mengatur akun yang sudah ada.

- Navigasi tersimpan per workspace (`WorkspaceUserPreference`,
  `WorkspaceUserProperties`). Dibaca dari workspace utama; ditulis ke SEMUA
  workspace tempat orangnya aktif, supaya hasilnya sama di mana pun ia membuka.
- Tata letak tersimpan per project (`ProjectUserProperty.display_filters`).
  Dibaca sebagai tata letak terbanyak; ditulis ke semua project miliknya.
"""

from collections import Counter

from django.db.models import Max

from plane.utils.bawaan_member import baca_bawaan, filter_tampilan


def _workspace_aktif(user):
    from plane.db.models import Workspace

    return list(
        Workspace.objects.filter(
            workspace_member__member=user,
            workspace_member__is_active=True,
            workspace_member__deleted_at__isnull=True,
            deleted_at__isnull=True,
        )
        .distinct()
        .order_by("created_at")
    )


def baca_tampilan(user) -> dict:
    """`{"navigasi": {...}, "work_items": {...}}` milik `user`. Yang belum pernah
    ditulis (orangnya belum pernah membuka aplikasi) jatuh ke bawaan God Mode,
    persis nilai yang akan ia dapat saat pertama kali membuka."""
    from plane.db.models import ProjectUserProperty, WorkspaceUserPreference, WorkspaceUserProperties

    bawaan = baca_bawaan()
    nav = {
        "pinned": dict(bawaan["navigasi"]["pinned"]),
        "project_mode": bawaan["navigasi"]["project_mode"],
        "project_limit": bawaan["navigasi"]["project_limit"],
    }
    workspace = _workspace_aktif(user)
    if workspace:
        utama = workspace[0]
        for kunci, semat in WorkspaceUserPreference.objects.filter(
            user=user, workspace=utama, key__in=list(nav["pinned"])
        ).values_list("key", "is_pinned"):
            nav["pinned"][kunci] = semat
        properti = WorkspaceUserProperties.objects.filter(user=user, workspace=utama).first()
        if properti:
            nav["project_mode"] = properti.navigation_control_preference
            nav["project_limit"] = properti.navigation_project_limit

    tata_letak = Counter(
        (df or {}).get("layout")
        for df in ProjectUserProperty.objects.filter(user=user).values_list("display_filters", flat=True)
        if isinstance(df, dict)
    )
    tata_letak.pop(None, None)
    jumlah_project = sum(tata_letak.values())
    return {
        "navigasi": nav,
        "work_items": {
            "layout": tata_letak.most_common(1)[0][0] if tata_letak else bawaan["work_items"]["layout"],
            # Lebih dari satu tata letak = orangnya memilih berbeda per project.
            # UI memberi tahu bahwa menyimpan akan menyamakan semuanya.
            "campuran": len(tata_letak) > 1,
            "jumlah_project": jumlah_project,
        },
    }


def ubah_navigasi(user, nav: dict) -> None:
    """Tulis navigasi yang SUDAH diperiksa (`periksa_navigasi`) ke semua workspace user."""
    from plane.db.models import WorkspaceUserPreference, WorkspaceUserProperties

    for ws in _workspace_aktif(user):
        semat = nav.get("pinned") or {}
        if semat:
            akhir = (
                WorkspaceUserPreference.objects.filter(user=user, workspace=ws).aggregate(m=Max("sort_order"))["m"]
                or 55535
            )
            for i, (kunci, nilai) in enumerate(semat.items()):
                baris = WorkspaceUserPreference.objects.filter(user=user, workspace=ws, key=kunci).first()
                if baris is None:
                    WorkspaceUserPreference.objects.create(
                        user=user, workspace=ws, key=kunci, is_pinned=nilai, sort_order=akhir + (i + 1) * 10000
                    )
                elif baris.is_pinned != nilai:
                    baris.is_pinned = nilai
                    baris.save(update_fields=["is_pinned", "updated_at"])
        kolom = {}
        if "project_mode" in nav:
            kolom["navigation_control_preference"] = nav["project_mode"]
        if "project_limit" in nav:
            kolom["navigation_project_limit"] = nav["project_limit"]
        if kolom:
            properti, _ = WorkspaceUserProperties.objects.get_or_create(user=user, workspace=ws)
            for nama, nilai in kolom.items():
                setattr(properti, nama, nilai)
            properti.save(update_fields=[*kolom, "updated_at"])


def ubah_tata_letak(user, layout: str) -> int:
    """Samakan tata letak work item di semua project `user`. Kembalikan jumlah baris yang berubah."""
    from plane.db.models import ProjectUserProperty

    berubah = []
    for prop in ProjectUserProperty.objects.filter(user=user).only("id", "display_filters"):
        lama = prop.display_filters if isinstance(prop.display_filters, dict) else {}
        baru = filter_tampilan(layout, lama)
        if baru != lama:
            prop.display_filters = baru
            berubah.append(prop)
    ProjectUserProperty.objects.bulk_update(berubah, ["display_filters"], batch_size=200)
    return len(berubah)
