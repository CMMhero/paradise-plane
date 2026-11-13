# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: hierarki organisasi di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`GET /api/instances/hierarki/` — baca-saja: jenjang, pengawasan, siapa yang belum punya atasan.

Rancangan + pertanyaan yang belum dijawab: `.herdr/hierarki-desain.md`.

## Kenapa baca-saja

Yang mengisi jenjang dan "divisi yang dia bawahi" **belum diputuskan user** (pertanyaan
#4 di rancangan). Membuat endpoint tulis sekarang berarti memilih salah satu jawaban
diam-diam. Yang bisa dijawab tanpa keputusan itu justru pertanyaan yang paling berguna:
**siapa saja yang jenjangnya belum diisi, dan siapa yang tidak punya atasan** — persis
angka yang dibutuhkan user sebelum menyalakan aturan apa pun.

## Kenapa di God Mode

Jenjang seluruh perusahaan adalah data lintas divisi. Satu-satunya tempat yang memang
lintas divisi di sistem ini adalah God Mode (`InstanceAdmin`, B1) — dan kalimat user
sendiri menyebut superadmin IT "untuk mengurus dan maintain system". Endpoint ini
memakai `BaseAPIView` God Mode, jadi izinnya sudah `InstanceAdminPermission` — satu
tempat yang menentukan, bukan dekorator per view.

## Kenapa angkanya dihitung dari JENJANG, bukan dari `ProjectMember.role`

`role = 20` hari ini juga dimiliki 5 akun NON-SuperAdmin di ~27 divisi masing-masing
(dibuat 31 Juli oleh skrip dan 5 Agustus oleh `bintang.ramadhan@`). Jadi `role = 20`
**bukan** sinyal "atasan" — memakainya akan memberi setiap divisi 5 atasan palsu tanpa
satu pun error. Endpoint ini sengaja melaporkan keadaan itu di `admin_lintas_divisi`
supaya orang berikutnya tidak perlu menemukannya lagi.
"""

# Third Party imports
from rest_framework.response import Response

# Module imports
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    JabatanOrganisasi,
    PengawasanDivisi,
    Project,
    ProjectMember,
    TINGKAT_CHOICES,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_NAMA,
    TINGKAT_SUPERVISOR,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.db.penempatan import (
    PERAN_DEPARTEMEN_SAH,
    departemen_dalam_divisi,
    penempatan_sekarang,
    peran_departemen_sekarang,
    setel_penempatan,
)
from plane.license.api.views.base import BaseAPIView
from plane.utils.hierarki import FLAG_GERBANG, gerbang_aktif

_SAH = {nilai for nilai, _ in TINGKAT_CHOICES}
# Angka ini milik ROLE project (20/15/5), bukan tangga jenjang. Menolaknya dengan pesan
# lebih baik daripada membulatkannya: 15 yang dikirim dengan maksud "Member" akan
# tersimpan sebagai "Supervisor" dan memberi kewenangan yang tidak diminta, tanpa error.
_SALAH_KAPAL = {
    15: "15 is a project ROLE (Member), not a level. Use 10 for Member.",
    5: "5 is a project ROLE (Guest). The lowest level is 10 (Member).",
}

# Akun yang bukan karyawan: akun uji yang pernah dibuat di workspace produksi.
# Disaring HANYA dari hitungan "88 karyawan", supaya angkanya bisa dibandingkan
# dengan brief tanpa menipu siapa pun. Daftar mentahnya tetap lengkap.
_AKUN_UJI = {"tester@paradiseperkasa.com"}

# Ambang "perlu dilihat": berapa divisi yang membuat baris `role = 20` seseorang
# patut dicurigai sebagai warisan, bukan penunjukan. 5 dipilih karena admin divisi
# yang sah memimpin 1–2 divisi (terukur: maksimum 2 di luar warisan).
_AMBANG_ADMIN_LINTAS = 5


def dep_ditambah_ids(baru, lama):
    """Departemen yang BARU ditambahkan permintaan ini (bukan yang sudah dipegang)."""
    return set(baru) - set(lama)


class InstanceHierarkiEndpoint(BaseAPIView):
    """Ringkasan hierarki satu workspace, baca-saja."""

    def get(self, request):
        slug = request.query_params.get("workspace")
        if slug:
            workspace = Workspace.objects.filter(slug=slug, deleted_at__isnull=True).first()
        else:
            # Tanpa parameter: workspace paling tua. Bukan yang paling baru, karena
            # workspace uji biasanya dibuat belakangan.
            workspace = Workspace.objects.filter(deleted_at__isnull=True).order_by("created_at").first()
        if workspace is None:
            return Response({"error": "Workspace not found."}, status=404)

        hanya_tanpa_atasan = request.query_params.get("hanya_tanpa_atasan") in ("1", "true", "ya")
        divisi_saring = request.query_params.get("divisi")

        projects = {}
        nama_project = {}
        for p in Project.objects.filter(workspace=workspace, deleted_at__isnull=True).only("id", "identifier", "name"):
            projects[p.id] = p.identifier
            nama_project[p.identifier] = p.name

        project_per_dep = {}
        for dep_id, pid in DepartemenProject.objects.filter(workspace=workspace).values_list(
            "departemen_id", "project_id"
        ):
            if pid in projects:
                project_per_dep.setdefault(dep_id, []).append(projects[pid])

        # --- satu query per tabel, bukan per orang ---------------------------
        anggota_ids = list(
            WorkspaceMember.objects.filter(workspace=workspace, is_active=True).values_list("member_id", flat=True)
        )
        users = {u.id: u for u in User.objects.filter(id__in=anggota_ids)}

        peta = {}
        for uid, tingkat in JabatanOrganisasi.objects.filter(workspace=workspace).values_list(
            "member_id", "tingkat"
        ):
            if uid not in peta or tingkat > peta[uid]:
                peta[uid] = tingkat
        sumber = dict(JabatanOrganisasi.objects.filter(workspace=workspace).values_list("member_id", "sumber"))
        # Multi-baris: satu orang bisa ditempatkan di beberapa departemen (satu baris
        # per departemen). Utama = yang pertama (kompatibilitas baca); daftar lengkap
        # ada di `departemen_ids` tiap baris anggota.
        dept_orang = {}
        div_orang = {}
        peran_orang = {}
        for uid, dep, div, t in JabatanOrganisasi.objects.filter(workspace=workspace).values_list(
            "member_id", "departemen_id", "divisi_id", "tingkat"
        ):
            if dep:
                dept_orang.setdefault(uid, set()).add(str(dep))
                # KEP-93: peran orang ini DI departemen itu (manager = Staf/Supervisor).
                peran_orang.setdefault(uid, {})[str(dep)] = t
            if div:
                div_orang.setdefault(uid, set()).add(str(div))

        divisi_orang = {}
        for uid, pid in ProjectMember.objects.filter(
            workspace=workspace, is_active=True, member_id__in=anggota_ids
        ).values_list("member_id", "project_id"):
            if pid in projects:
                divisi_orang.setdefault(uid, set()).add(projects[pid])

        pengawasan = {}
        for pid, uid in PengawasanDivisi.objects.filter(workspace=workspace).values_list("project_id", "member_id"):
            if pid in projects:
                pengawasan.setdefault(uid, set()).add(projects[pid])

        # Tingkat tertinggi per divisi, dihitung sekali. "Punya atasan" = ada orang
        # LAIN di salah satu divisinya yang tingkatnya lebih tinggi.
        tingkat_tertinggi_per_divisi = {}
        for uid, tingkat in peta.items():
            for d in divisi_orang.get(uid, set()):
                sekarang = tingkat_tertinggi_per_divisi.get(d)
                if sekarang is None or tingkat > sekarang[1]:
                    tingkat_tertinggi_per_divisi[d] = (uid, tingkat)

        baris = []
        for uid in anggota_ids:
            u = users.get(uid)
            if u is None:
                continue
            # Tanpa baris jabatan = Staf (bawaan, 4 Nov 2026). `tingkat_bawaan` menandai
            # bahwa jenjangnya bukan hasil keputusan siapa pun, supaya laporan tetap bisa
            # membedakannya.
            tingkat = peta.get(uid, TINGKAT_MEMBER)
            divisi = divisi_orang.get(uid, set())

            punya_atasan = False
            for d in divisi:
                tertinggi = tingkat_tertinggi_per_divisi.get(d)
                if tertinggi and tertinggi[0] != uid and tingkat is not None and tertinggi[1] > tingkat:
                    punya_atasan = True
                    break

            dept_ids = sorted(dept_orang.get(uid, set()))
            utama = dept_ids[0] if dept_ids else None
            baris.append(
                {
                    "id": str(uid),
                    "email": u.email,
                    "display_name": u.display_name,
                    "is_active": u.is_active,
                    "tingkat": tingkat,
                    "tingkat_nama": TINGKAT_NAMA.get(tingkat),
                    # True = belum pernah ada yang menetapkan jenjangnya; dihitung Staf.
                    "tingkat_bawaan": uid not in peta,
                    "sumber": sumber.get(uid),
                    "divisi": sorted(divisi),
                    "divisi_diawasi": sorted(pengawasan.get(uid, set())),
                    # Penempatan (id record, bukan project). None = belum ditempatkan.
                    # Multi-departemen: semua baris departemen orang ini.
                    "departemen_id": utama,
                    "divisi_id": sorted(div_orang.get(uid, set()))[0] if div_orang.get(uid) else None,
                    "departemen_ids": dept_ids,
                    "divisi_ids": sorted(div_orang.get(uid, set())),
                    "peran_departemen": peran_orang.get(uid, {}),
                    "punya_atasan": punya_atasan,
                }
            )

        total = len(baris)
        punya_jenjang_total = sum(1 for b in baris if not b["tingkat_bawaan"])
        tanpa_atasan = [b for b in baris if not b["punya_atasan"]]

        if hanya_tanpa_atasan:
            baris = tanpa_atasan
        if divisi_saring:
            baris = [b for b in baris if divisi_saring in b["divisi"]]
        baris.sort(key=lambda b: (-b["tingkat"], b["email"]))

        # Pelanggaran yang HARUS terlihat: baris `role = 20` di banyak divisi.
        role20 = {}
        for uid, pid in ProjectMember.objects.filter(
            workspace=workspace, is_active=True, role=20, member_id__in=anggota_ids
        ).values_list("member_id", "project_id"):
            if pid in projects:
                role20.setdefault(uid, set()).add(projects[pid])
        admin_lintas = sorted(
            (
                {
                    "id": str(uid),
                    "email": users[uid].email if uid in users else None,
                    "jumlah_divisi": len(divs),
                }
                for uid, divs in role20.items()
                if len(divs) >= _AMBANG_ADMIN_LINTAS
            ),
            key=lambda x: -x["jumlah_divisi"],
        )

        return Response(
            {
                "workspace": {"id": str(workspace.id), "slug": workspace.slug, "name": workspace.name},
                # Peta identifier → UUID project. POST `pengawasan` meminta UUID,
                # tapi baris anggota memakai identifier (lebih mudah dibaca); tanpa
                # peta ini UI God Mode tak bisa mengirim pengawasan. Aditif murni.
                "projects": {identifier: str(pid) for pid, identifier in projects.items()},
                # Nama tampil divisi ({identifier: name}) untuk pemilih God Mode.
                # Aditif: `projects` tidak diubah supaya pemanggil lama tak pecah.
                "project_names": nama_project,
                # Pilihan penempatan KEP-29. Pohon lengkapnya: GET /api/instances/organisasi/.
                "departemen_pilihan": [
                    {
                        "id": str(d.id),
                        "kode": d.kode,
                        "nama": d.nama,
                        "divisi_id": str(d.divisi_id),
                        # Identifier project departemen ini (KEP-76): editor menyaring
                        # "akses project lain" dari project yang sudah otomatis.
                        "projects": project_per_dep.get(d.id, []),
                    }
                    for d in Departemen.objects.filter(workspace=workspace).order_by("nama")
                ],
                "divisi_pilihan": [
                    {"id": str(v.id), "kode": v.kode, "nama": v.nama}
                    for v in Divisi.objects.filter(workspace=workspace).order_by("nama")
                ],
                "gerbang_aktif": gerbang_aktif(),
                "flag_gerbang": FLAG_GERBANG,
                "tingkat": {str(k): v for k, v in TINGKAT_NAMA.items()},
                "ringkasan": {
                    "anggota_workspace": total,
                    "punya_jenjang": punya_jenjang_total,
                    "belum_diisi": total - punya_jenjang_total,
                    "pengawasan_eksplisit": sum(len(v) for v in pengawasan.values()),
                    "tanpa_atasan": len(tanpa_atasan),
                    "tanpa_atasan_tanpa_akun_uji": sum(1 for b in tanpa_atasan if b["email"] not in _AKUN_UJI),
                    "divisi_berpenyetuju": sum(
                        1
                        for d in set(projects.values())
                        if any(
                            peta.get(uid) is not None
                            and peta[uid] >= TINGKAT_SUPERVISOR
                            and d in divisi_orang.get(uid, set())
                            for uid in anggota_ids
                        )
                    ),
                    "divisi_total": len(set(projects.values())),
                },
                "admin_lintas_divisi": admin_lintas,
                "anggota": baris,
            }
        )

    def post(self, request):
        """Setel jenjang (dan/atau "divisi yang dia bawahi") satu orang.

        Ini satu-satunya jalan menulis hierarki, dan sengaja hanya di God Mode: keputusan
        user 2026-10-15 menetapkan bahwa **God Mode** yang mengisi jenjang. Tanpa endpoint
        ini, tabelnya mustahil diisi dan seluruh aturan hierarki berhenti sebagai kode mati
        -- 88 dari 88 orang belum berjenjang.

        Perubahan jenjang = perubahan HAK AKSES (siapa boleh menyetujui, siapa boleh
        menugaskan), jadi ia masuk jejak audit begitu kedua model ini terdaftar di
        `plane/db/audit.py`.

        Badan permintaan:

        ```
        { "member_id": "<uuid>",
          "tingkat": 10|20|30|35|40|null,    # null = jenjang + semua tempat dicabut,
                                                 # orangnya kembali Staf tanpa tempat
          "sumber": "...",                    # opsional, default "manual"
          "catatan": "...",                   # opsional
          "departemen_ids": ["<dep_id>", ...] # opsional: MENGGANTI himpunan departemen
                                                 # (jenjang apa pun boleh banyak)
          "divisi_ids": ["<div_id>", ...]     # opsional: MENGGANTI himpunan divisi
                                                 # yang dipimpin (manager ke atas)
          "departemen_id": "<dep_id>"|null   # singkatan: TAMBAH satu departemen
                                                 # (null = cabut semua departemen)
          "divisi_id": "<div_id>"|null       # singkatan: TAMBAH satu divisi
                                                 # (null = cabut semua divisi)
          "peran_departemen": {"<dep_id>": 10|20}  # opsional, KEP-93: peran per departemen
          "pertahankan_peran": true         # opsional: `tingkat` tidak menyeragamkan
                                                 # peran departemen yang lain
        }
        ```

        Aturan KEP-76 (tidak ada lagi galat "rapikan dulu"): menambah tempat tidak
        pernah memindahkan tempat lama; orang tanpa jenjang yang ditempatkan jadi
        Staf (departemen) atau Manager (divisi); memimpin divisi tanpa mengirim
        jenjang menaikkan ke Manager; turun di bawah Manager mencabut divisinya
        (dilaporkan di `divisi_dilepas`), departemennya tetap.
        Supervisor/manager yang dicabut dari tempat terakhirnya jatuh ke Staf; selama
        masih memegang satu tempat mana pun, jenjangnya tetap (KEP-86).

        `pengawasan` hanya dikirim kalau memang diubah -- bedanya penting, karena
        "tidak dikirim" berarti "jangan sentuh", sedangkan "dikirim kosong" berarti
        "cabut semua".
        """
        from django.db import transaction

        member_id = request.data.get("member_id")
        if not member_id:
            return Response({"error": "member_id is required."}, status=400)

        user = User.objects.filter(pk=member_id).first()
        if user is None:
            return Response({"error": "User not found."}, status=404)

        workspace = Workspace.objects.filter(deleted_at__isnull=True).order_by("created_at").first()
        if workspace is None:
            return Response({"error": "Workspace not found."}, status=404)

        # --- tingkat -------------------------------------------------------
        if "tingkat" in request.data:
            tingkat = request.data.get("tingkat")
            if tingkat is not None:
                try:
                    tingkat = int(tingkat)
                except (TypeError, ValueError):
                    return Response({"error": "tingkat must be a number or null."}, status=400)
                if tingkat in _SALAH_KAPAL:
                    return Response({"error": _SALAH_KAPAL[tingkat]}, status=400)
                if tingkat not in _SAH:
                    return Response(
                        {"error": f"Unknown tingkat. Options: {sorted(_SAH)}."}, status=400
                    )
        else:
            tingkat = "tidak-diubah"

        # "Supervised divisions" dibuang (KEP-93): resolver tidak membacanya lagi, jadi
        # menulisnya hanya menyimpan data mati. Ditolak terang, bukan diabaikan diam-diam.
        if "pengawasan" in request.data:
            return Response(
                {"error": "Supervised divisions were removed. Authority comes from placements."},
                status=400,
            )

        # --- penempatan (KEP-76): satu daftar tempat, menambah != memindah ------
        # `departemen_ids` / `divisi_ids`: daftar PENGGANTI (kosong = cabut semua
        # tempat jenis itu). Singkatan `departemen_id` / `divisi_id`: nilai = TAMBAH
        # satu tempat (tidak memindahkan yang lama), null = cabut semua tempat jenis
        # itu. Kunci tidak dikirim = jangan sentuh.
        tingkat_lama, dep_lama, div_lama = penempatan_sekarang(workspace.id, user.id)
        sah_dep = {str(d) for d in Departemen.objects.filter(workspace=workspace).values_list("id", flat=True)}
        sah_div = {str(v) for v in Divisi.objects.filter(workspace=workspace).values_list("id", flat=True)}

        def _daftar(kunci_daftar, kunci_satu, lama, sah, label):
            """(himpunan baru, galat|None, menambah_baru)."""
            if kunci_daftar in request.data:
                diminta = request.data.get(kunci_daftar) or []
                if not isinstance(diminta, list):
                    return lama, f"{kunci_daftar} must be a list of ids.", False
                baru = {str(x) for x in diminta}
            elif kunci_satu in request.data:
                nilai = request.data.get(kunci_satu)
                baru = (lama | {str(nilai)}) if nilai else set()
            else:
                return lama, None, False
            asing = sorted(baru - sah)
            if asing:
                return lama, f"Unknown {label} in this workspace: {', '.join(asing)}.", False
            return baru, None, bool(baru - lama)

        dep_baru, galat, _ = _daftar("departemen_ids", "departemen_id", dep_lama, sah_dep, "departments")
        if galat:
            return Response({"error": galat}, status=400)
        div_baru, galat, div_ditambah = _daftar("divisi_ids", "divisi_id", div_lama, sah_div, "divisions")
        if galat:
            return Response({"error": galat}, status=400)
        tempat_diubah = dep_baru != dep_lama or div_baru != div_lama

        # KEP-93: peran per departemen (hanya bermakna untuk manager ke atas).
        peran_departemen = None
        if "peran_departemen" in request.data:
            diminta = request.data.get("peran_departemen") or {}
            if not isinstance(diminta, dict):
                return Response({"error": "peran_departemen must be an object of department id to level."}, status=400)
            peran_departemen = {}
            for dep_id, nilai in diminta.items():
                if str(dep_id) not in sah_dep:
                    return Response({"error": f"Unknown department in this workspace: {dep_id}."}, status=400)
                try:
                    nilai = int(nilai)
                except (TypeError, ValueError):
                    nilai = None
                if nilai not in PERAN_DEPARTEMEN_SAH:  # tidak ada manager departemen
                    return Response(
                        {"error": "A department role is Staff (10) or Supervisor (20), never Manager."},
                        status=400,
                    )
                peran_departemen[str(dep_id)] = nilai
            peran_lama = peran_departemen_sekarang(workspace.id, user.id)
            if any(peran_lama.get(d) != v for d, v in peran_departemen.items()):
                tempat_diubah = True

        # Jenjang efektif. Tidak pernah menolak hanya karena urutan langkah:
        # orang tanpa jenjang yang ditempatkan jadi Staf (departemen) atau Manager
        # (divisi); memimpin divisi baru menaikkan jenjang ke Manager kalau jenjang
        # tidak ikut dikirim.
        if tingkat is None:
            tingkat_baru = None
        elif tingkat != "tidak-diubah":
            tingkat_baru = tingkat
            if div_ditambah and tingkat_baru < TINGKAT_MANAGER:
                return Response(
                    {"error": "Only a manager or director can lead a division. Pick Manager as the level."},
                    status=400,
                )
        elif tingkat_lama is not None:
            tingkat_baru = tingkat_lama
            if div_ditambah and tingkat_baru < TINGKAT_MANAGER:
                tingkat_baru = TINGKAT_MANAGER
        elif div_baru:
            tingkat_baru = TINGKAT_MANAGER
        elif dep_baru:
            tingkat_baru = TINGKAT_MEMBER
        else:
            tingkat_baru = "tidak-diubah"  # tidak ada apa pun untuk ditulis

        # KEP-93: manager tidak duduk di departemen divisi yang ia pimpin. Menambahkannya
        # = ditolak (jelas salah niat); departemen lama yang tertelan divisi yang BARU
        # dipimpin = dilepas dan dilaporkan, karena divisinya sudah menjangkaunya.
        departemen_dilepas = set()
        if tingkat_baru not in (None, "tidak-diubah") and tingkat_baru >= TINGKAT_MANAGER:
            tertelan = departemen_dalam_divisi(dep_baru, div_baru)
            if tertelan & dep_ditambah_ids(dep_baru, dep_lama):
                return Response(
                    {
                        "error": (
                            f"{user.display_name} already leads this department's division as manager. "
                            "There is no department manager role."
                        ),
                        "kode": "sudah-memimpin-divisi",
                    },
                    status=400,
                )
            departemen_dilepas = tertelan
            dep_baru = dep_baru - tertelan

        divisi_dilepas = set()
        with transaction.atomic():
            from plane.db.jangkauan import sinkronkan_satu, tunda_sinkron  # noqa: PLC0415

            with tunda_sinkron():
                # Jenjang yang sama dikirim ulang tetap menyeragamkan peran departemen
                # yang menyimpang (KEP-93), jadi ia juga dihitung perubahan.
                peran_menyimpang = (
                    tingkat_baru not in (None, "tidak-diubah")
                    and "tingkat" in request.data
                    and not request.data.get("pertahankan_peran")
                    and tingkat_baru < TINGKAT_MANAGER
                    and any(t != tingkat_baru for t in peran_departemen_sekarang(workspace.id, user.id).values())
                )
                if tingkat_baru != "tidak-diubah" and (
                    tingkat_baru != tingkat_lama or tempat_diubah or peran_menyimpang or "catatan" in request.data
                ):
                    divisi_dilepas = setel_penempatan(
                        workspace,
                        user,
                        tingkat_baru,
                        dep_baru,
                        div_baru,
                        sumber=request.data.get("sumber") or "manual",
                        catatan=request.data.get("catatan") if "catatan" in request.data else None,
                        peran_departemen=peran_departemen,
                        # Jenjang dipilih eksplisit = semua departemen ikut (KEP-93),
                        # kecuali `pertahankan_peran`: jenjang turun karena manager
                        # dipindah ke departemen divisinya sendiri (papan), peran
                        # departemen lainnya tetap.
                        seragam="tingkat" in request.data and not request.data.get("pertahankan_peran"),
                    )

            sinkronkan_satu(workspace.id, user.id)

        semua = list(
            JabatanOrganisasi.objects.filter(workspace=workspace, member=user)
            .order_by("departemen_id", "divisi_id")
            .values_list("tingkat", "departemen_id", "divisi_id")
        )
        peran_semua = {str(d): t for t, d, _ in semua if d}
        tingkat_sekarang = max((t for t, _, _ in semua), default=TINGKAT_MEMBER)
        dept_semua = sorted({str(d) for _, d, _ in semua if d})
        divisi_semua = sorted({str(v) for _, _, v in semua if v})
        utama_skr = dept_semua[0] if dept_semua else None
        return Response(
            {
                "member": {
                    "id": str(user.id),
                    "email": user.email,
                    "nama": user.display_name,
                    "tingkat": tingkat_sekarang,
                    "departemen_id": utama_skr,
                    "divisi_id": divisi_semua[0] if divisi_semua else None,
                    "departemen_ids": dept_semua,
                    "divisi_ids": divisi_semua,
                    # Divisi yang dicabut otomatis karena jenjangnya turun di bawah
                    # Manager (KEP-76). UI menampilkannya, bukan menolak simpan.
                    "divisi_dilepas": sorted(divisi_dilepas),
                    # Departemen yang tertelan divisi yang kini ia pimpin (KEP-93).
                    "departemen_dilepas": sorted(departemen_dilepas),
                    "peran_departemen": peran_semua,
                    "tingkat_nama": TINGKAT_NAMA.get(tingkat_sekarang) if tingkat_sekarang is not None else None,
                }
            }
        )
