# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Jejak audit: mencatat SIAPA mengubah APA pada entitas sensitif (akses & konten
# inti). Ditenagai django-auditlog (MIT, jazzband), lihat NOTICE. Aktor + IP
# ditangkap oleh auditlog.middleware.AuditlogMiddleware (lihat settings.MIDDLEWARE).
#
# Field body besar (biner/HTML) sengaja dikecualikan: diff-nya raksasa dan riwayat
# konten halaman sudah dilacak terpisah oleh PageVersion.

from auditlog.registry import auditlog

# Field editor yang tak boleh masuk diff audit
_PAGE_BODY = [
    "description_binary",
    "description_html",
    "description_json",
    "description_stripped",
    "view_props",
    "logo_props",
]
_ISSUE_BODY = [
    "description_binary",
    "description_html",
    "description_json",
    "description_stripped",
]


def register_audit_models():
    """Daftarkan model sensitif ke auditlog. Dipanggil dari DbConfig.ready()."""
    from plane.db.models import (
        Departemen,
        DepartemenProject,
        Divisi,
        Issue,
        JabatanOrganisasi,
        Page,
        PengawasanDivisi,
        Project,
        ProjectMember,
        WorkspaceMember,
    )

    # Perubahan akses/keanggotaan (peran = hak akses)
    auditlog.register(Project)
    auditlog.register(ProjectMember)
    auditlog.register(WorkspaceMember)

    # Hierarki organisasi = hak akses juga: jenjang menentukan siapa boleh menyetujui
    # penugasan dan siapa boleh menugaskan ke siapa. Tanpa baris ini, pertanyaan "siapa
    # yang menaikkan jabatan orang ini" tidak punya jawaban, dan itu justru jenis
    # perubahan yang paling perlu bisa ditelusuri.
    auditlog.register(JabatanOrganisasi)
    auditlog.register(PengawasanDivisi)
    # Struktur divisi -> departemen -> project menentukan jangkauan (KEP-29).
    auditlog.register(Divisi)
    auditlog.register(Departemen)
    auditlog.register(DepartemenProject)

    # Konten inti, metadata saja, bukan isi editor
    auditlog.register(Issue, exclude_fields=_ISSUE_BODY)
    auditlog.register(Page, exclude_fields=_PAGE_BODY)
