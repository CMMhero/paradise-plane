# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: halaman departemen di Wiki (KEP-95)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Halaman (Pages) project departemen, dibaca lewat Wiki.

Ini agregasi BACA saja: halamannya tetap milik project departemen dan tidak
disalin ke tabel Wiki. Folder departemen di Wiki menampilkan halaman project
departemen itu (satu departemen tepat satu project, 0146).

Siapa melihat apa (ditegakkan di sini, di query, bukan di klien):

    halaman publik    semua anggota workspace (sama dengan hak baca Wiki)
    halaman privat    anggota departemen itu (peran apa pun), manager divisinya,
                      direktur, dan admin Wiki (Super Admin); pemiliknya selalu

Halaman yang diarsipkan, dihapus, atau lepas dari project tidak tampil.
Pencarian Wiki ikut mencari halaman (judul dan isi, `cari_halaman`) dengan
saringan izin yang sama. Pohon folder hanya membawa ANGKA halaman per folder
departemen (`jumlah_halaman_per_departemen`), dihitung dengan saringan yang
sama, jadi angka itu tidak pernah memuat halaman privat yang tidak boleh
dilihat (KEP-97).

Mengeklik halaman di Wiki membuka halaman aslinya di project (KEP-97). Modal
baca `WikiHalamanEndpoint` hanya cadangan untuk halaman yang terlihat di Wiki
tapi tidak akan terbuka di project menurut aturan Plane (`can_open_in_project`
False): bukan anggota project, atau halaman privat orang lain.
"""

from types import SimpleNamespace

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.wiki_dasar import Galat, WikiAPIView
from plane.db.models import Departemen, DepartemenProject, Page, ProjectMember, ProjectPage
from plane.utils.wiki_cari import MIN_TOKEN_MIRIP, cuplikan, skor_judul
from plane.utils.wiki_mandiri import pengawas_halaman_privat

_MAKS_HASIL_HALAMAN = 20
_MAKS_KANDIDAT_HALAMAN = 200
_PUBLIK = "public"
_PRIVAT = "private"


def _project_departemen(departemen_id):
    """Id project aktif milik departemen ini, atau None."""
    return (
        DepartemenProject.objects.filter(
            departemen_id=departemen_id,
            project__deleted_at__isnull=True,
        )
        .values_list("project_id", flat=True)
        .first()
    )


def _halaman_terlihat(penilai, project_id, departemen):
    """Queryset halaman project departemen yang boleh dilihat orang ini."""
    qs = Page.objects.filter(
        workspace_id=penilai.workspace_id,
        project_pages__project_id=project_id,
        project_pages__deleted_at__isnull=True,
        archived_at__isnull=True,
    )
    if not penilai.boleh_lihat_halaman_privat(departemen.id, departemen.divisi_id):
        qs = qs.filter(Q(access=Page.PUBLIC_ACCESS) | Q(owned_by_id=penilai.user.id))
    return qs.distinct()


def project_per_departemen(workspace_id):
    """{departemen_id: (project_id, divisi_id)} untuk departemen hidup yang punya
    project hidup. Satu query; aturan yang sama dengan `_project_departemen`."""
    return {
        str(dep_id): (proj_id, div_id)
        for dep_id, proj_id, div_id in DepartemenProject.objects.filter(
            workspace_id=workspace_id,
            project__deleted_at__isnull=True,
            departemen__deleted_at__isnull=True,
        ).values_list("departemen_id", "project_id", "departemen__divisi_id")
    }


def saringan_akses(penilai, peta):
    """(id semua project departemen, Q izin baca halaman) untuk orang ini.

    Satu sumber untuk hitungan di pohon dan pencarian: halaman publik dan milik
    sendiri selalu, halaman privat hanya di project yang wilayahnya boleh ia
    lihat. Q ini harus ditaruh di `filter()` yang SAMA dengan syarat
    `project_pages__*`, supaya Django memakai satu join untuk semuanya."""
    semua_project = [proj for proj, _ in peta.values()]
    privat_boleh = [proj for dep, (proj, div) in peta.items() if penilai.boleh_lihat_halaman_privat(dep, div)]
    akses = Q(access=Page.PUBLIC_ACCESS) | Q(owned_by_id=penilai.user.id)
    if privat_boleh:
        akses |= Q(project_pages__project_id__in=privat_boleh)
    return semua_project, akses


def jumlah_halaman_per_departemen(penilai, peta):
    """{departemen_id: jumlah halaman yang boleh dilihat orang ini}.

    `peta` = hasil `project_per_departemen`. Satu query agregat untuk seluruh
    workspace, bukan satu per folder. Saringannya cermin `_halaman_terlihat`:
    semua syarat relasi `project_pages` ada di SATU `filter()` supaya Django
    memakai satu join yang sama (syarat project, `deleted_at`, dan izin privat
    berlaku untuk baris ProjectPage yang sama).
    """
    if not peta:
        return {}
    semua_project, akses = saringan_akses(penilai, peta)
    baris = (
        Page.objects.filter(
            akses,
            workspace_id=penilai.workspace_id,
            project_pages__project_id__in=semua_project,
            project_pages__deleted_at__isnull=True,
            archived_at__isnull=True,
        )
        .values("project_pages__project_id")
        .annotate(n=Count("id", distinct=True))
    )
    per_project = {str(b["project_pages__project_id"]): b["n"] for b in baris}
    return {dep: per_project.get(str(proj), 0) for dep, (proj, _) in peta.items()}


def _bisa_dibuka(page, user_id, anggota_project, admin, pengawas):
    """Halaman ini akan terbuka di project menurut aturan Plane + KEP-95:
    publik = anggota project; privat = pemilik, plus admin Wiki, direktur, dan
    manager divisinya (`pengawas_halaman_privat`, sama dengan penegak di
    ProjectPagePermission). Admin Wiki melihat project tanpa jadi anggota."""
    if page.owned_by_id == user_id:
        return True
    boleh_akses = page.access == Page.PUBLIC_ACCESS or pengawas
    return boleh_akses and (anggota_project or admin)


class _DasarHalaman(WikiAPIView):
    def halaman_json(self, page, project_id, departemen):
        return {
            "id": str(page.id),
            "name": page.name,
            "access": _PRIVAT if page.access == Page.PRIVATE_ACCESS else _PUBLIK,
            "logo_props": page.logo_props,
            "owned_by": str(page.owned_by_id) if page.owned_by_id else None,
            "updated_at": page.updated_at,
            "project_id": str(project_id),
            "departemen_id": str(departemen.id),
            "departemen_nama": departemen.nama,
        }

    def anggota_project(self, project_id):
        return ProjectMember.objects.filter(
            project_id=project_id, member_id=self.request.user.id, is_active=True
        ).exists()

    def cari_halaman(self, tokens, maks=_MAKS_HASIL_HALAMAN):
        """Halaman project departemen yang cocok dengan semua kata kueri, di judul
        atau isinya, dengan batas lihat yang sama seperti daftar halaman folder.
        Dipanggil di dalam `ambang_mirip()`."""
        peta = project_per_departemen(self.workspace.id)
        if not peta or not tokens:
            return []
        semua_project, akses = saringan_akses(self.penilai, peta)
        cocok = Q()
        for kata in tokens:
            satu = Q(name__icontains=kata) | Q(description_stripped__icontains=kata)
            if len(kata) >= MIN_TOKEN_MIRIP:
                satu |= Q(name__kata_mirip=kata) | Q(description_stripped__kata_mirip=kata)
            cocok &= satu
        kandidat = list(
            Page.objects.filter(
                akses,
                cocok,
                workspace_id=self.workspace.id,
                project_pages__project_id__in=semua_project,
                project_pages__deleted_at__isnull=True,
                archived_at__isnull=True,
            )
            .distinct()
            .order_by("-updated_at")[:_MAKS_KANDIDAT_HALAMAN]
        )
        if not kandidat:
            return []
        urut = sorted(kandidat, key=lambda p: skor_judul(tokens, p.name), reverse=True)[:maks]

        project_halaman = dict(
            ProjectPage.objects.filter(
                page_id__in=[p.id for p in urut], project_id__in=semua_project, deleted_at__isnull=True
            ).values_list("page_id", "project_id")
        )
        dep_per_project = {proj: dep for dep, (proj, _) in peta.items()}
        nama_dep = {
            str(i): n
            for i, n in Departemen.objects.filter(id__in=list(dep_per_project.values())).values_list("id", "nama")
        }
        anggota, pengawas = {}, {}
        hasil = []
        for page in urut:
            project_id = project_halaman.get(page.id)
            if project_id is None:
                continue
            dep_id = dep_per_project.get(project_id)
            departemen = SimpleNamespace(id=dep_id, nama=nama_dep.get(dep_id, ""))
            if project_id not in anggota:
                anggota[project_id] = self.anggota_project(project_id)
            if page.access == Page.PRIVATE_ACCESS and page.owned_by_id != self.request.user.id:
                if project_id not in pengawas:
                    pengawas[project_id] = pengawas_halaman_privat(self.request.user, project_id)
                diawasi = pengawas[project_id]
            else:
                diawasi = False
            potongan, sorot = cuplikan(page.description_stripped or "", tokens)
            hasil.append(
                {
                    **self.halaman_json(page, project_id, departemen),
                    "can_open_in_project": _bisa_dibuka(
                        page, self.request.user.id, anggota[project_id], self.penilai.admin, diawasi
                    ),
                    "cuplikan": potongan,
                    "sorot": sorot,
                }
            )
        return hasil


class WikiHalamanFolderEndpoint(_DasarHalaman):
    """Halaman project departemen untuk satu folder departemen."""

    def get(self, request, slug, folder_id):
        folder = self.folder_atau_404(folder_id)
        kosong = {"departemen": None, "pages": []}
        if not folder.departemen_id:
            return Response(kosong, status=status.HTTP_200_OK)
        departemen = Departemen.objects.filter(id=folder.departemen_id, workspace_id=self.workspace.id).first()
        project_id = _project_departemen(folder.departemen_id) if departemen else None
        if departemen is None or project_id is None:
            return Response(kosong, status=status.HTTP_200_OK)
        halaman = list(
            _halaman_terlihat(self.penilai, project_id, departemen)
            .only("id", "name", "access", "logo_props", "owned_by_id", "updated_at")
            .order_by("-updated_at")
        )
        # Dihitung sekali untuk seluruh daftar, bukan per baris.
        anggota = self.anggota_project(project_id)
        privat_orang_lain = any(p.access == Page.PRIVATE_ACCESS and p.owned_by_id != request.user.id for p in halaman)
        pengawas = privat_orang_lain and pengawas_halaman_privat(request.user, project_id)
        return Response(
            {
                "departemen": {"id": str(departemen.id), "nama": departemen.nama, "project_id": str(project_id)},
                "pages": [
                    {
                        **self.halaman_json(p, project_id, departemen),
                        "can_open_in_project": _bisa_dibuka(p, request.user.id, anggota, self.penilai.admin, pengawas),
                    }
                    for p in halaman
                ],
            },
            status=status.HTTP_200_OK,
        )


class WikiHalamanEndpoint(_DasarHalaman):
    """Satu halaman departemen, hanya-baca, untuk dibaca di dalam Wiki.

    Dipakai web hanya untuk halaman yang tidak bisa dibuka di project
    (`can_open_in_project` False). Halaman di luar project departemen (atau di
    workspace lain) dan halaman yang tidak boleh dilihat sama-sama dijawab 404,
    supaya keberadaannya tidak terbaca dari kode status.
    """

    def get(self, request, slug, page_id):
        tautan = (
            DepartemenProject.objects.filter(
                workspace_id=self.workspace.id,
                project__deleted_at__isnull=True,
                project__project_pages__page_id=page_id,
                project__project_pages__deleted_at__isnull=True,
            )
            .select_related("departemen")
            .first()
        )
        if tautan is None or tautan.departemen.deleted_at is not None:
            raise Galat("Page not found.", status.HTTP_404_NOT_FOUND)
        departemen, project_id = tautan.departemen, tautan.project_id
        page = _halaman_terlihat(self.penilai, project_id, departemen).filter(id=page_id).first()
        if page is None:
            raise Galat("Page not found.", status.HTTP_404_NOT_FOUND)

        pengawas = page.access == Page.PRIVATE_ACCESS and pengawas_halaman_privat(request.user, project_id)
        bisa_dibuka = _bisa_dibuka(
            page, request.user.id, self.anggota_project(project_id), self.penilai.admin, pengawas
        )
        return Response(
            {
                **self.halaman_json(page, project_id, departemen),
                "description_html": page.description_html or "",
                "can_open_in_project": bisa_dibuka,
            },
            status=status.HTTP_200_OK,
        )
