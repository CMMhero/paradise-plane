# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: struktur organisasi di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Struktur divisi -> departemen -> project dari God Mode (KEP-29, KEP-32).

    GET    /api/instances/organisasi/                         pohon lengkap
    POST   /api/instances/organisasi/divisi/                  {kode, nama}
    PATCH  /api/instances/organisasi/divisi/<id>/             {kode?, nama?}
    DELETE /api/instances/organisasi/divisi/<id>/
    POST   /api/instances/organisasi/departemen/              {divisi_id, kode, nama}
    PATCH  /api/instances/organisasi/departemen/<id>/         {divisi_id?, kode?, nama?, project_ids?}
    DELETE /api/instances/organisasi/departemen/<id>/

Penempatan orang (departemen / divisi manager) ditulis lewat
`POST /api/instances/hierarki/`, di baris jenjangnya, bukan di sini.
Departemen tambahan supervisor (KEP-32) juga lewat sana (`departemen_ids`).

KEP-32: satu departemen tepat satu project. Membuat departemen langsung membuat
atau mengadopsi project-nya (identifier = kode tanpa strip, mis. FIN-FIN ->
FINFIN); menaruh project kedua DITOLAK (400). Hapus departemen yang projectnya
masih punya tugas DITOLAK (409); project kosong ikut diarsipkan.

Hapus DITOLAK selama masih ada orangnya (utama maupun tambahan). Kaskade diam-diam
akan mencabut akses puluhan orang dari satu klik.
"""

# Python imports
import re

# Django imports
from django.db import transaction
from django.db.models import Q

# Third Party imports
from rest_framework.response import Response

# Module imports
from plane.db.jangkauan import sinkronkan_workspace, tunda_sinkron
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    SupervisorDepartemen,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_NAMA,
    TINGKAT_SUPERVISOR,
    Workspace,
)
from plane.license.api.views.base import BaseAPIView

BATAS_KODE = 20


def _workspace_utama():
    return Workspace.objects.filter(deleted_at__isnull=True).order_by("created_at").first()


def _kode_nama(data, wajib):
    """(kode, nama, galat). Kode dinormalkan ke huruf besar tanpa spasi tepi."""
    kode = (data.get("kode") or "").strip().upper() if "kode" in data or wajib else None
    nama = (data.get("nama") or "").strip() if "nama" in data or wajib else None
    if kode is not None and not kode:
        return None, None, "kode wajib diisi."
    if kode is not None and len(kode) > BATAS_KODE:
        return None, None, f"kode maksimal {BATAS_KODE} karakter."
    if nama is not None and not nama:
        return None, None, "nama wajib diisi."
    return kode, nama, None


def _identifier_dari_kode(kode):
    """Identifier project dari kode departemen (KEP-32).

    Identifier project melarang `-` (dan sederet karakter lain), jadi strip
    penghubung dibuang: `FIN-FIN` -> `FINFIN`. Maksimal 12 karakter mengikuti
    kolom `Project.identifier`; kode yang lebih panjang wajib dipadatkan manual.
    Kembalikan (identifier, galat).
    """
    ident = (kode or "").replace("-", "").replace(" ", "").upper()
    if not ident:
        return None, "kode tidak menyisakan identifier project yang sah."
    if len(ident) > 12:
        return None, f"kode {kode} terlalu panjang untuk identifier project (maks 12 huruf tanpa strip)."
    if re.match(Project.FORBIDDEN_IDENTIFIER_CHARS_PATTERN, ident):
        return None, f"kode {kode} mengandung karakter yang dilarang di identifier project."
    return ident, None


def _adopsi_atau_buat_project(dep, actor, workspace):
    """Pastikan departemen baru punya tepat satu project (KEP-32: project ikut departemen).

    Kalau project ber-identifier sama sudah ada dan belum berdepartemen -> dipetakan
    (adopsi, bukan digandakan). Kalau belum ada -> dibuat lewat serializer yang sama
    dengan flow "project baru" di UI (validasi + state bawaan sama), pembuatnya jadi
    admin, lalu dipetakan. Melempar ValueError berisi pesan siap tampil kalau gagal;
    pemanggil membungkus semuanya dalam satu transaksi dengan pembuatan departemennya.
    """
    from plane.app.permissions import ROLE  # noqa: PLC0415
    from plane.app.serializers import ProjectSerializer  # noqa: PLC0415
    from plane.db.membership import jadikan_anggota_project  # noqa: PLC0415
    from plane.db.models import DEFAULT_STATES, State  # noqa: PLC0415

    ident, galat = _identifier_dari_kode(dep.kode)
    if galat:
        raise ValueError(galat)

    semua = list(Project.all_objects.filter(workspace=workspace, identifier=ident))
    aktif = next((p for p in semua if p.deleted_at is None), None)
    if aktif is not None:
        pemetaan = DepartemenProject.objects.filter(project=aktif).first()
        if pemetaan is not None:
            raise ValueError(f"Project {ident} sudah milik departemen {pemetaan.departemen.kode}.")
        DepartemenProject.objects.create(workspace=workspace, departemen=dep, project=aktif)
        jadikan_anggota_project(aktif.pk, actor.id, ROLE.ADMIN.value, workspace_id=workspace.id)
        return aktif

    if semua:
        raise ValueError(
            f"Identifier {ident} dipakai project arsip/terhapus. Buka arsipnya dulu atau pakai kode lain."
        )

    ser = ProjectSerializer(
        data={
            "name": dep.nama,
            "identifier": ident,
            "description": f"Ruang kerja {dep.kode} {dep.nama} (dibuat otomatis dari departemen).",
            "created_by": str(actor.id),
        },
        context={"workspace_id": str(workspace.id)},
    )
    if not ser.is_valid():
        raise ValueError(f"Project untuk {dep.kode} gagal dibuat: {dict(ser.errors)}.")
    project = ser.save()
    Project.objects.filter(pk=project.pk).update(created_by=actor)
    jadikan_anggota_project(project.pk, actor.id, ROLE.ADMIN.value, workspace_id=workspace.id)
    State.objects.bulk_create(
        [
            State(
                name=state["name"],
                color=state["color"],
                project=project,
                sequence=state["sequence"],
                workspace=workspace,
                group=state["group"],
                default=state.get("default", False),
                created_by=actor,
            )
            for state in DEFAULT_STATES
        ]
    )
    DepartemenProject.objects.create(workspace=workspace, departemen=dep, project=project)
    return project


def pohon_organisasi(workspace):
    """Pohon divisi -> departemen -> project + project yang belum punya departemen."""
    projects = {
        p.id: p for p in Project.objects.filter(workspace=workspace, deleted_at__isnull=True).only("id", "identifier", "name")
    }
    peta = {}
    for dep_id, pid in DepartemenProject.objects.filter(workspace=workspace).values_list("departemen_id", "project_id"):
        if pid in projects:
            peta.setdefault(dep_id, []).append(projects[pid])
    # Orang per departemen (staf/supervisor) dan manager per divisi, satu query.
    orang_dep, manager_div = {}, {}
    for j in JabatanOrganisasi.objects.filter(workspace=workspace).filter(
        Q(departemen__isnull=False) | Q(divisi__isnull=False)
    ).select_related("member"):
        baris = {
            "id": str(j.member_id),
            "nama": j.member.display_name or j.member.email,
            "email": j.member.email,
            "tingkat": j.tingkat,
            "tingkat_nama": TINGKAT_NAMA.get(j.tingkat),
        }
        # Tempat yang BERLAKU menurut jenjang (lihat `jangkauan_hierarki`): manager
        # dihitung di divisinya, yang lain di departemennya. Isian sisa tidak ditampilkan
        # sebagai keanggotaan supaya layar tidak menjanjikan akses yang tidak ada.
        if j.tingkat >= TINGKAT_DIREKTUR:
            continue
        if j.tingkat >= TINGKAT_MANAGER:
            if j.divisi_id:
                manager_div.setdefault(j.divisi_id, []).append(baris)
        elif j.departemen_id:
            orang_dep.setdefault(j.departemen_id, []).append(baris)

    # Supervisor TAMBAHAN (KEP-32): tampil di tiap departemen yang dia awasi, supaya
    # kartu departemen jujur tentang siapa yang bisa menyetujui di sana.
    tambahan = {}
    for member_id, dep_id in SupervisorDepartemen.objects.filter(workspace=workspace).values_list(
        "member_id", "departemen_id"
    ):
        tambahan.setdefault(member_id, set()).add(dep_id)
    if tambahan:
        jabatan = {
            j.member_id: j
            for j in JabatanOrganisasi.objects.filter(workspace=workspace, member_id__in=tambahan.keys()).select_related(
                "member"
            )
        }
        for member_id, dep_ids in tambahan.items():
            j = jabatan.get(member_id)
            if j is None or j.tingkat < TINGKAT_SUPERVISOR or j.tingkat >= TINGKAT_MANAGER:
                continue  # yatim/tingkat tak berlaku: jangkauan mengabaikannya juga
            baris = {
                "id": str(j.member_id),
                "nama": j.member.display_name or j.member.email,
                "email": j.member.email,
                "tingkat": j.tingkat,
                "tingkat_nama": TINGKAT_NAMA.get(j.tingkat),
                "tambahan": True,
            }
            for dep_id in dep_ids:
                sudah = {a["id"] for a in orang_dep.get(dep_id, [])}
                if baris["id"] not in sudah:
                    orang_dep.setdefault(dep_id, []).append(baris)

    def _project(p):
        return {"id": str(p.id), "identifier": p.identifier, "name": p.name}

    departemen_per_divisi = {}
    for d in Departemen.objects.filter(workspace=workspace).order_by("nama"):
        departemen_per_divisi.setdefault(d.divisi_id, []).append(
            {
                "id": str(d.id),
                "kode": d.kode,
                "nama": d.nama,
                "jumlah_orang": len(orang_dep.get(d.id, [])),
                "anggota": sorted(orang_dep.get(d.id, []), key=lambda b: (-b["tingkat"], b["nama"].lower())),
                "projects": [_project(p) for p in sorted(peta.get(d.id, []), key=lambda p: p.name)],
            }
        )
    berdepartemen = {p.id for daftar in peta.values() for p in daftar}
    return {
        "divisi": [
            {
                "id": str(v.id),
                "kode": v.kode,
                "nama": v.nama,
                "manager": sorted(manager_div.get(v.id, []), key=lambda b: b["nama"].lower()),
                "departemen": departemen_per_divisi.get(v.id, []),
            }
            for v in Divisi.objects.filter(workspace=workspace).order_by("nama")
        ],
        "tanpa_departemen": [
            _project(p) for p in sorted(projects.values(), key=lambda p: p.name) if p.id not in berdepartemen
        ],
    }


class InstanceOrganisasiEndpoint(BaseAPIView):
    def get(self, request):
        workspace = _workspace_utama()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=404)
        return Response(pohon_organisasi(workspace))


class InstanceDivisiEndpoint(BaseAPIView):
    def post(self, request):
        workspace = _workspace_utama()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=404)
        kode, nama, galat = _kode_nama(request.data, wajib=True)
        if galat:
            return Response({"error": galat}, status=400)
        if Divisi.objects.filter(workspace=workspace, kode=kode).exists():
            return Response({"error": f"Kode divisi {kode} sudah dipakai."}, status=400)
        Divisi.objects.create(workspace=workspace, kode=kode, nama=nama)
        return Response(pohon_organisasi(workspace), status=201)

    def patch(self, request, pk):
        divisi = Divisi.objects.filter(pk=pk).first()
        if divisi is None:
            return Response({"error": "Divisi tidak ditemukan."}, status=404)
        kode, nama, galat = _kode_nama(request.data, wajib=False)
        if galat:
            return Response({"error": galat}, status=400)
        if kode and Divisi.objects.filter(workspace_id=divisi.workspace_id, kode=kode).exclude(pk=pk).exists():
            return Response({"error": f"Kode divisi {kode} sudah dipakai."}, status=400)
        divisi.kode = kode or divisi.kode
        divisi.nama = nama or divisi.nama
        divisi.save(update_fields=["kode", "nama", "updated_at"])
        return Response(pohon_organisasi(divisi.workspace))

    def delete(self, request, pk):
        divisi = Divisi.objects.filter(pk=pk).first()
        if divisi is None:
            return Response({"error": "Divisi tidak ditemukan."}, status=404)
        if Departemen.objects.filter(divisi=divisi).exists():
            return Response({"error": "Pindahkan atau hapus departemennya dulu."}, status=409)
        if JabatanOrganisasi.objects.filter(divisi=divisi).exists():
            return Response({"error": "Masih ada manager yang ditempatkan di divisi ini."}, status=409)
        workspace = divisi.workspace
        divisi.delete()
        return Response(pohon_organisasi(workspace))


class InstanceDepartemenEndpoint(BaseAPIView):
    def post(self, request):
        workspace = _workspace_utama()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=404)
        divisi = Divisi.objects.filter(workspace=workspace, pk=request.data.get("divisi_id")).first()
        if divisi is None:
            return Response({"error": "Divisi tidak ditemukan."}, status=400)
        kode, nama, galat = _kode_nama(request.data, wajib=True)
        if galat:
            return Response({"error": galat}, status=400)
        if Departemen.objects.filter(workspace=workspace, kode=kode).exists():
            return Response({"error": f"Kode departemen {kode} sudah dipakai."}, status=400)
        # KEP-32: project mengikuti departemen. Pembuatan + pemetaan project-nya satu
        # transaksi dengan departemennya: gagal di project = tidak ada yang tertulis.
        try:
            with transaction.atomic(), tunda_sinkron():
                dep = Departemen.objects.create(workspace=workspace, divisi=divisi, kode=kode, nama=nama)
                _adopsi_atau_buat_project(dep, request.user, workspace)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        sinkronkan_workspace(workspace.id)
        return Response(pohon_organisasi(workspace), status=201)

    def patch(self, request, pk):
        dep = Departemen.objects.filter(pk=pk).first()
        if dep is None:
            return Response({"error": "Departemen tidak ditemukan."}, status=404)
        kode, nama, galat = _kode_nama(request.data, wajib=False)
        if galat:
            return Response({"error": galat}, status=400)
        if kode and Departemen.objects.filter(workspace_id=dep.workspace_id, kode=kode).exclude(pk=pk).exists():
            return Response({"error": f"Kode departemen {kode} sudah dipakai."}, status=400)

        divisi = None
        if "divisi_id" in request.data:
            divisi = Divisi.objects.filter(workspace_id=dep.workspace_id, pk=request.data.get("divisi_id")).first()
            if divisi is None:
                return Response({"error": "Divisi tidak ditemukan."}, status=400)

        project_ids = None
        if "project_ids" in request.data:
            diminta = request.data.get("project_ids")
            if not isinstance(diminta, list):
                return Response({"error": "project_ids harus daftar id project."}, status=400)
            if len(diminta) > 1:
                # KEP-32: satu departemen tepat satu project. Project lama yang
                # digabung (payung) diarsipkan dulu lewat skrip D4/pengaturan
                # project, bukan ditumpuk di sini.
                return Response(
                    {"error": "Satu departemen tepat satu project. Arsipkan dulu project yang tidak dipakai."},
                    status=400,
                )
            sah = {
                str(pid)
                for pid in Project.objects.filter(workspace_id=dep.workspace_id, deleted_at__isnull=True).values_list(
                    "id", flat=True
                )
            }
            asing = [str(pid) for pid in diminta if str(pid) not in sah]
            if asing:
                return Response({"error": f"Project tidak dikenal: {', '.join(asing)}."}, status=400)
            project_ids = {str(pid) for pid in diminta}

        # Satu sinkron di akhir, bukan satu per baris pemetaan.
        with transaction.atomic(), tunda_sinkron():
            dep.kode = kode or dep.kode
            dep.nama = nama or dep.nama
            if divisi is not None:
                dep.divisi = divisi
            dep.save(update_fields=["kode", "nama", "divisi", "updated_at"])
            if project_ids is not None:
                _ganti_project(dep, project_ids)
        sinkronkan_workspace(dep.workspace_id)
        return Response(pohon_organisasi(dep.workspace))

    def delete(self, request, pk):
        dep = Departemen.objects.filter(pk=pk).first()
        if dep is None:
            return Response({"error": "Departemen tidak ditemukan."}, status=404)
        if JabatanOrganisasi.objects.filter(departemen=dep).exists():
            return Response({"error": "Masih ada orang yang ditempatkan di departemen ini."}, status=409)
        if SupervisorDepartemen.objects.filter(departemen=dep).exists():
            return Response({"error": "Masih ada supervisor tambahan di departemen ini."}, status=409)
        # KEP-32: hapus departemen ikut mengarsipkan project-nya yang kosong —
        # project tanpa tugas tidak ada yang kehilangan apa-apa. Project yang masih
        # punya tugas TETAP ditolak: isinya harus dipindahkan manual dulu.
        from django.utils import timezone  # noqa: PLC0415

        for baris in DepartemenProject.objects.filter(departemen=dep).select_related("project"):
            terbuka = Issue.objects.filter(
                project=baris.project, deleted_at__isnull=True, archived_at__isnull=True
            ).count()
            if terbuka:
                return Response(
                    {
                        "error": f"Project {baris.project.identifier} masih punya {terbuka} tugas. "
                        "Pindahkan dulu tugasnya sebelum menghapus departemen ini."
                    },
                    status=409,
                )
        workspace = dep.workspace
        with transaction.atomic(), tunda_sinkron():
            for baris in DepartemenProject.objects.filter(departemen=dep):
                Project.objects.filter(pk=baris.project_id, archived_at__isnull=True).update(
                    archived_at=timezone.now()
                )
                baris.delete(soft=False)
            dep.delete()
        sinkronkan_workspace(workspace.id)
        return Response(pohon_organisasi(workspace))


def _ganti_project(dep, project_ids):
    """Jadikan `project_ids` tepat project milik departemen ini.

    Project yang sebelumnya milik departemen LAIN dipindah ke sini (satu project
    tepat satu departemen). Project yang dikeluarkan jadi tanpa departemen.
    """
    sekarang = {str(pid) for pid in DepartemenProject.objects.filter(departemen=dep).values_list("project_id", flat=True)}
    for baris in DepartemenProject.objects.filter(departemen=dep):
        if str(baris.project_id) not in project_ids:
            baris.delete(soft=False)
    for pid in project_ids - sekarang:
        # Hard delete baris lama project ini (di departemen lain): pemetaan tidak
        # butuh riwayat sendiri, jejaknya sudah ada di auditlog.
        DepartemenProject.all_objects.filter(project_id=pid).delete()  # manager biasa = hard delete
        DepartemenProject.objects.create(workspace_id=dep.workspace_id, departemen=dep, project_id=pid)


class InstanceDepartemenDariProjectEndpoint(BaseAPIView):
    """Jadikan project lama (bekas "divisi = project") sebuah departemen, sekaligus orangnya.

        GET  ?project_id=<uuid>   anggota aktif project itu + jenjang & penempatan sekarang
        POST {project_id, divisi_id, kode?, nama?, member_ids: [...]}

    Satu transaksi: buat departemen, petakan project, tempatkan orang yang dipilih,
    dan tandai keanggotaan lama mereka di project itu sebagai akses hierarki. Tanpa
    tanda itu keanggotaan lama tetap "eksplisit" dan TIDAK ikut dicabut saat orangnya
    pindah departemen nanti (KEP-29, catatan migrasi).

    Manager & direktur dilewati: jangkauan mereka bukan departemen. Orang yang
    jenjangnya belum diisi ditempatkan sebagai staf, sama dengan editor Member.
    """

    def get(self, request):
        workspace = _workspace_utama()
        project = Project.objects.filter(workspace=workspace, pk=request.query_params.get("project_id")).first()
        if project is None:
            return Response({"error": "Project tidak ditemukan."}, status=404)
        jabatan = {
            j.member_id: j
            for j in JabatanOrganisasi.objects.filter(workspace=workspace).select_related("departemen", "divisi")
        }
        hasil = []
        for pm in (
            ProjectMember.objects.filter(project=project, is_active=True, member__is_active=True)
            .select_related("member")
            .order_by("member__display_name")
        ):
            j = jabatan.get(pm.member_id)
            hasil.append(
                {
                    "id": str(pm.member_id),
                    "nama": pm.member.display_name or pm.member.email,
                    "email": pm.member.email,
                    "tingkat": j.tingkat if j else None,
                    "tingkat_nama": TINGKAT_NAMA.get(j.tingkat) if j else None,
                    "departemen": f"{j.departemen.kode} {j.departemen.nama}" if j and j.departemen else None,
                    # Manager/direktur tidak ditempatkan di departemen; UI menampilkannya tak tercentang.
                    "bisa_ditempatkan": j is None or j.tingkat < TINGKAT_MANAGER,
                }
            )
        return Response(
            {"project": {"id": str(project.id), "identifier": project.identifier, "name": project.name}, "anggota": hasil}
        )

    def post(self, request):
        workspace = _workspace_utama()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=404)
        project = Project.objects.filter(
            workspace=workspace, pk=request.data.get("project_id"), deleted_at__isnull=True
        ).first()
        if project is None:
            return Response({"error": "Project tidak ditemukan."}, status=400)
        if DepartemenProject.objects.filter(project=project).exists():
            return Response({"error": f"{project.identifier} sudah punya departemen."}, status=400)
        divisi = Divisi.objects.filter(workspace=workspace, pk=request.data.get("divisi_id")).first()
        if divisi is None:
            return Response({"error": "Divisi tidak ditemukan."}, status=400)

        data = {"kode": request.data.get("kode") or project.identifier, "nama": request.data.get("nama") or project.name}
        kode, nama, galat = _kode_nama(data, wajib=True)
        if galat:
            return Response({"error": galat}, status=400)
        if Departemen.objects.filter(workspace=workspace, kode=kode).exists():
            return Response({"error": f"Kode departemen {kode} sudah dipakai."}, status=400)

        diminta = request.data.get("member_ids") or []
        if not isinstance(diminta, list):
            return Response({"error": "member_ids harus daftar id."}, status=400)
        anggota_project = {
            str(uid)
            for uid in ProjectMember.objects.filter(project=project, is_active=True).values_list("member_id", flat=True)
        }
        asing = [str(u) for u in diminta if str(u) not in anggota_project]
        if asing:
            # Gagal-tertutup: impor ini hanya untuk orang yang MEMANG sudah di project itu.
            return Response({"error": f"Bukan anggota aktif {project.identifier}: {', '.join(asing)}."}, status=400)

        from plane.db.jangkauan import tandai_otomatis  # noqa: PLC0415

        ditempatkan, dilewati = [], []
        with transaction.atomic(), tunda_sinkron():
            dep = Departemen.objects.create(workspace=workspace, divisi=divisi, kode=kode, nama=nama)
            DepartemenProject.objects.create(workspace=workspace, departemen=dep, project=project)
            for uid in {str(u) for u in diminta}:
                baris = JabatanOrganisasi.all_objects.filter(workspace=workspace, member_id=uid).first()
                if baris is not None and baris.deleted_at is None and baris.tingkat >= TINGKAT_MANAGER:
                    dilewati.append(uid)
                    continue
                if baris is None:
                    JabatanOrganisasi.objects.create(
                        workspace=workspace, member_id=uid, tingkat=TINGKAT_MEMBER, departemen=dep, sumber="impor-project"
                    )
                else:
                    if baris.deleted_at is not None:
                        baris.deleted_at, baris.tingkat, baris.divisi_id = None, TINGKAT_MEMBER, None
                    baris.departemen = dep
                    baris.save(update_fields=["deleted_at", "tingkat", "divisi", "departemen", "updated_at"])
                tandai_otomatis(workspace.id, project.id, uid)
                ditempatkan.append(uid)
        sinkronkan_workspace(workspace.id)
        return Response(
            {"pohon": pohon_organisasi(workspace), "ditempatkan": len(ditempatkan), "dilewati": len(dilewati)},
            status=201,
        )
