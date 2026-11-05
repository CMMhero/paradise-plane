# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: izin per sumber (KEP-85)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siapa boleh mengubah, mengarsipkan, atau menghapus sesuatu SELAIN work item.

Work item punya aturannya sendiri (`task_access.py`, `galat_ubah_tugas`). Berkas ini
memberi bentuk yang sama ke semua sumber lain, supaya "bukan punyamu, bukan
bawahanmu = tidak bisa diutak-atik" berlaku di mana pun, bukan cuma di papan.

Peran, dari atas:

    Super Admin        selalu boleh
    Admin workspace    selalu boleh (keputusan user 4 Nov 2026: "seperti Super Admin")
    Direktur           atasan semua orang di project yang ia awasi
    Manager            atasan di project divisinya
    Supervisor         atasan di project departemennya
    Staf               hanya miliknya sendiri
    Guest              hanya miliknya sendiri

Role "admin project" milik Plane TIDAK memberi wewenang apa pun di sini: hampir semua
staf kantor ini admin project (jebakan yang sama dengan KEP-27 untuk work item).

Dua jenis aturan, keduanya diatur Super Admin di God Mode > Work rules > Permissions:

- **Isi** (`IZIN_ISI`): sesuatu yang punya pemilik. Pemilik = pembuat/owner, ditambah
  orang yang ditugaskan di dalamnya (lead & anggota module). Pilihan: pemilik +
  atasannya (bawaan), pemilik saja, atau setiap anggota project (Plane asli).
- **Struktur** (`IZIN_STRUKTUR`): milik project, bukan perorangan (state, label,
  setelan, arsip/hapus project, trash). Nilainya jenjang minimum, dan hanya di
  project yang ia awasi (`divisi_diawasi`).

Satu pintu untuk view (`tolak_izin`), satu untuk tampilan (`ringkasan_izin`, dibaca
`GET .../izin-saya/`). Aturan yang ditulis dua kali cepat atau lambat jadi dua aturan.
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from rest_framework import status
from rest_framework.response import Response

from plane.utils.saklar_instance import (
    IZIN_ISI,
    IZIN_PEMILIK_SAJA,
    IZIN_SEMUA_ANGGOTA,
    IZIN_STRUKTUR,
    STRUKTUR_ADMIN_SAJA,
    setelan_angka,
)

_ROLE_ANGGOTA = 15
_ROLE_ADMIN = 20
TINGKAT_SUPERVISOR = 20


def _s(nilai) -> str | None:
    return None if nilai in (None, "") else str(nilai)


class PenilaiIzin:
    """Penilai izin untuk SATU orang di SATU workspace, dibaca sekali per permintaan.

    Endpoint yang menilai banyak baris (daftar, aksi massal) memakai satu penilai,
    jadi status admin, jenjang, dan project yang diawasi tidak dibaca ulang per baris.
    """

    def __init__(self, user, workspace_id):
        self.user = user
        self.workspace_id = workspace_id
        self._cache: dict = {}

    def _sekali(self, kunci, baca):
        if kunci not in self._cache:
            self._cache[kunci] = baca()
        return self._cache[kunci]

    @property
    def anonim(self) -> bool:
        return self.user is None or getattr(self.user, "is_anonymous", True)

    @property
    def admin(self) -> bool:
        """Super Admin atau admin workspace aktif."""

        def baca():
            if self.anonim:
                return False
            from plane.db.models import WorkspaceMember  # noqa: PLC0415
            from plane.db.superadmin import is_super_admin  # noqa: PLC0415

            if is_super_admin(self.user):
                return True
            return WorkspaceMember.objects.filter(
                workspace_id=self.workspace_id, member_id=self.user.id, role=_ROLE_ADMIN, is_active=True
            ).exists()

        return self._sekali("admin", baca)

    @property
    def tingkat(self) -> int:
        from plane.utils.hierarki import tingkat_efektif  # noqa: PLC0415

        return self._sekali("tingkat", lambda: tingkat_efektif(self.user.id, self.workspace_id))

    def tingkat_di(self, project_id) -> int:
        """Jenjang yang berlaku di satu project (KEP-93: peran per tempat)."""
        from plane.utils.hierarki import tingkat_efektif  # noqa: PLC0415

        return self._sekali(
            ("tingkat", str(project_id)), lambda: tingkat_efektif(self.user.id, self.workspace_id, project_id)
        )

    @property
    def diawasi(self) -> set[str]:
        """Project (id teks) yang diawasi orang ini: supervisor/manager/direktur."""
        from plane.utils.hierarki import divisi_diawasi  # noqa: PLC0415

        return self._sekali("diawasi", lambda: {str(p) for p in divisi_diawasi(self.user.id, self.workspace_id)})

    def bawahan(self, project_id) -> set[str]:
        from plane.utils.hierarki import _bawahan_ids  # noqa: PLC0415

        return self._sekali(
            ("bawahan", str(project_id)),
            lambda: {str(u) for u in _bawahan_ids(self.user.id, self.workspace_id, project_id)},
        )

    def anggota_project(self, project_id) -> bool:
        def baca():
            from plane.db.models import ProjectMember  # noqa: PLC0415

            return ProjectMember.objects.filter(
                project_id=project_id,
                member_id=self.user.id,
                role__gte=_ROLE_ANGGOTA,
                is_active=True,
                deleted_at__isnull=True,
            ).exists()

        return self._sekali(("anggota", str(project_id)), baca)

    def aturan(self, kunci: str) -> int:
        return self._sekali(("aturan", kunci), lambda: setelan_angka(kunci))

    # ------------------------------------------------------------------ atasan

    def atasan_dari(self, pemilik_id, project_id=None) -> bool:
        """Apakah saya atasan `pemilik_id` (di project ini, atau di workspace)."""
        if self.tingkat < TINGKAT_SUPERVISOR:
            return False
        pemilik = _s(pemilik_id)
        if project_id is not None:
            if pemilik is None:
                # Tanpa pemilik (dibuat sistem, pembuatnya dihapus): pengawas project
                # yang mengurusnya, supaya barangnya tidak yatim selamanya.
                return str(project_id) in self.diawasi
            return pemilik in self.bawahan(project_id)
        return self._atasan_workspace(pemilik)

    def _atasan_workspace(self, pemilik: str | None) -> bool:
        """Sumber tingkat workspace (view workspace): atasan di salah satu project pemilik."""
        if pemilik is None:
            return False
        from plane.utils.hierarki import divisi_anggota, tingkat_efektif  # noqa: PLC0415

        if tingkat_efektif(pemilik, self.workspace_id) >= self.tingkat:
            return False
        bersama = {str(p) for p in divisi_anggota(pemilik, self.workspace_id)} & self.diawasi
        return any(pemilik in self.bawahan(pid) for pid in bersama)

    # ------------------------------------------------------------------ aturan

    def boleh(
        self,
        kunci: str,
        *,
        project_id=None,
        pemilik_id=None,
        terlibat_ids: Iterable = (),
    ) -> bool:
        """Boleh menjalankan aksi `kunci` atas sumber ini?

        Isi: `pemilik_id` = pembuat/owner; `terlibat_ids` = yang ditugaskan di
        dalamnya (lead & anggota module). Struktur: cukup `project_id`.
        """
        if self.anonim:
            return False
        if self.admin:
            return True
        if kunci in IZIN_STRUKTUR:
            return self._boleh_struktur(kunci, project_id)
        if kunci not in IZIN_ISI:
            raise KeyError(kunci)

        saya = str(self.user.id)
        if saya == _s(pemilik_id) or saya in {str(u) for u in terlibat_ids if u}:
            return True
        aturan = self.aturan(kunci)
        if aturan == IZIN_PEMILIK_SAJA:
            return False
        if aturan == IZIN_SEMUA_ANGGOTA:
            return project_id is None or self.anggota_project(project_id)
        return self.atasan_dari(pemilik_id, project_id)

    def _boleh_struktur(self, kunci: str, project_id) -> bool:
        ambang = self.aturan(kunci)
        if ambang >= STRUKTUR_ADMIN_SAJA or project_id is None:
            return False
        return self.tingkat_di(project_id) >= ambang and str(project_id) in self.diawasi


def penilai_untuk(request, workspace_id) -> PenilaiIzin:
    """Satu penilai per permintaan dan workspace (disimpan di objek request)."""
    simpanan = getattr(request, "_penilai_izin", None)
    if simpanan is None:
        simpanan = {}
        try:
            request._penilai_izin = simpanan
        except AttributeError:
            pass
    kunci = str(workspace_id)
    if kunci not in simpanan:
        simpanan[kunci] = PenilaiIzin(request.user, workspace_id)
    return simpanan[kunci]


# Pesan per jenis aksi. Bahasa Indonesia, sama dengan pesan tolak work item.
_PESAN_ISI = "Hanya pemiliknya, atasannya, atau admin yang dapat {aksi} {benda} ini."
_PESAN_PEMILIK = "Hanya pemiliknya atau admin yang dapat {aksi} {benda} ini."
_PESAN_STRUKTUR = "Anda tidak memiliki wewenang untuk {aksi} {benda} di project ini."

_AKSI = {
    "EDIT": "mengubah",
    "ARCHIVE": "mengarsipkan",
    "DELETE": "menghapus",
    "WORKFLOW": "mengubah",
    "RESTORE": "memulihkan",
    "PURGE": "membuang permanen",
}
_BENDA = {
    "MODULE": "module",
    "PAGE": "page",
    "VIEW": "view",
    "COMMENT": "komentar",
    "WIKI": "materi",
    "PROJECT": "project",
    "TRASH": "isi trash",
}


def pesan_tolak(kunci: str, aturan: int | None = None) -> str:
    """Pesan 403 untuk `kunci` (mis. PERM_MODULE_DELETE)."""
    _, benda, aksi = kunci.split("_", 2)
    kata_aksi = _AKSI.get(aksi, "mengubah")
    kata_benda = _BENDA.get(benda, benda.lower())
    if aksi == "WORKFLOW":
        kata_benda = "alur kerja (state, label, estimate)"
    if kunci in IZIN_STRUKTUR:
        return _PESAN_STRUKTUR.format(aksi=kata_aksi, benda=kata_benda)
    templat = _PESAN_PEMILIK if aturan == IZIN_PEMILIK_SAJA else _PESAN_ISI
    return templat.format(aksi=kata_aksi, benda=kata_benda)


def tolak_izin(
    request,
    kunci: str,
    *,
    workspace_id,
    project_id=None,
    pemilik_id=None,
    terlibat_ids: Iterable = (),
) -> Response | None:
    """Response 403 kalau aksi ini tidak boleh, None kalau boleh. Pintu tunggal untuk view."""
    penilai = penilai_untuk(request, workspace_id)
    if penilai.boleh(kunci, project_id=project_id, pemilik_id=pemilik_id, terlibat_ids=terlibat_ids):
        return None
    aturan = penilai.aturan(kunci) if kunci in IZIN_ISI else None
    return Response({"error": pesan_tolak(kunci, aturan)}, status=status.HTTP_403_FORBIDDEN)


def tolak_izin_project(request, kunci: str, *, slug, project_id) -> Response | None:
    """`tolak_izin` untuk aturan struktur, dengan workspace dibaca dari project di URL.

    Project yang tidak ada di workspace ini dibiarkan lolos (None): view yang
    memanggil yang menjawab 404, supaya pesan "tidak ditemukan" tetap satu sumber.
    """
    from plane.db.models import Project  # noqa: PLC0415

    workspace_id = (
        Project.objects.filter(pk=project_id, workspace__slug=slug).values_list("workspace_id", flat=True).first()
    )
    if workspace_id is None:
        return None
    return tolak_izin(request, kunci, workspace_id=workspace_id, project_id=project_id)


def tolak_izin_module(request, kunci: str, module) -> Response | None:
    """`tolak_izin` untuk satu module: pemilik = pembuat, terlibat = lead + anggota.

    Anggota module baru dibaca kalau jalur murah (admin, pembuat, lead, atasan)
    belum memutuskan, jadi kebanyakan permintaan tidak menambah kueri.
    """
    from plane.db.models import ModuleMember  # noqa: PLC0415

    penilai = penilai_untuk(request, module.workspace_id)
    dasar = {"project_id": module.project_id, "pemilik_id": module.created_by_id}
    if penilai.boleh(kunci, terlibat_ids=[module.lead_id], **dasar):
        return None
    anggota = ModuleMember.objects.filter(module_id=module.id).values_list("member_id", flat=True)
    return tolak_izin(request, kunci, workspace_id=module.workspace_id, terlibat_ids=list(anggota), **dasar)


def tolak_izin_module_ids(request, kunci: str, module_ids: Iterable, *, slug, project_id) -> Response | None:
    """`tolak_izin_module` untuk banyak module sekaligus; berhenti di penolakan pertama.

    Id yang bukan module di project ini dilewati (tidak ada yang bisa diubah).
    """
    from plane.db.models import Module  # noqa: PLC0415

    ids = [m for m in module_ids if m]
    if not ids:
        return None
    for module in Module.objects.filter(pk__in=ids, project_id=project_id, workspace__slug=slug).only(
        "id", "workspace_id", "project_id", "created_by_id", "lead_id"
    ):
        galat = tolak_izin_module(request, kunci, module)
        if galat is not None:
            return galat
    return None


def tolak_izin_komentar(request, kunci: str, komentar) -> Response | None:
    """`tolak_izin` untuk komentar work item. Penulisnya `actor`; `created_by` cadangan
    untuk baris lama/impor yang actor-nya kosong."""
    return tolak_izin(
        request,
        kunci,
        workspace_id=komentar.workspace_id,
        project_id=komentar.project_id,
        pemilik_id=komentar.actor_id or komentar.created_by_id,
    )


def ringkasan_izin(user, workspace_id, project_id: UUID | str | None = None) -> dict:
    """Bahan tampilan untuk menilai sendiri, cermin PERSIS `PenilaiIzin.boleh`.

    Isi dinilai di klien dari `admin`, `aturan`, `bawahan_ids`, dan `anggota`;
    struktur sudah dijawab server per kunci (`struktur`), karena bergantung pada
    project yang diawasi, yang tidak dikirim ke klien.
    """
    penilai = PenilaiIzin(user, workspace_id)
    aturan = {k: penilai.aturan(k) for k in (*IZIN_ISI, *IZIN_STRUKTUR)}
    if penilai.anonim:
        return {"admin": False, "tingkat": None, "aturan": aturan, "bawahan_ids": [], "anggota": False, "struktur": {}}
    hasil = {
        "admin": penilai.admin,
        "tingkat": penilai.tingkat,
        "aturan": aturan,
        "bawahan_ids": [],
        "anggota": False,
        "mengawasi_project": False,
        "struktur": {k: penilai.boleh(k, project_id=project_id) for k in IZIN_STRUKTUR},
    }
    if project_id is not None:
        hasil["bawahan_ids"] = sorted(penilai.bawahan(project_id)) if penilai.tingkat >= TINGKAT_SUPERVISOR else []
        hasil["anggota"] = penilai.anggota_project(project_id)
        hasil["mengawasi_project"] = penilai.tingkat >= TINGKAT_SUPERVISOR and str(project_id) in penilai.diawasi
    return hasil
