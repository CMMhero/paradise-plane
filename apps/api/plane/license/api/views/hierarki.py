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
    Divisi,
    JabatanOrganisasi,
    PengawasanDivisi,
    Project,
    ProjectMember,
    TINGKAT_CHOICES,
    TINGKAT_NAMA,
    TINGKAT_SUPERVISOR,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.license.api.views.base import BaseAPIView
from plane.utils.hierarki import FLAG_GERBANG, gerbang_aktif

_SAH = {nilai for nilai, _ in TINGKAT_CHOICES}
# Angka ini milik ROLE project (20/15/5), bukan tangga jenjang. Menolaknya dengan pesan
# lebih baik daripada membulatkannya: 15 yang dikirim dengan maksud "Member" akan
# tersimpan sebagai "Supervisor" dan memberi kewenangan yang tidak diminta, tanpa error.
_SALAH_KAPAL = {
    15: "15 adalah ROLE project (Member), bukan jenjang. Pakai 10 untuk Member.",
    5: "5 adalah ROLE project (Guest). Jenjang terendah adalah 10 (Member).",
}

# Akun yang bukan karyawan: akun uji yang pernah dibuat di workspace produksi.
# Disaring HANYA dari hitungan "88 karyawan", supaya angkanya bisa dibandingkan
# dengan brief tanpa menipu siapa pun. Daftar mentahnya tetap lengkap.
_AKUN_UJI = {"tester@paradiseperkasa.com"}

# Ambang "perlu dilihat": berapa divisi yang membuat baris `role = 20` seseorang
# patut dicurigai sebagai warisan, bukan penunjukan. 5 dipilih karena admin divisi
# yang sah memimpin 1–2 divisi (terukur: maksimum 2 di luar warisan).
_AMBANG_ADMIN_LINTAS = 5


def _ganti_departemen_anggota(workspace, user, tingkat_efektif, ingin, sumber="manual"):
    """Jadikan `ingin` tepat himpunan departemen tempat user ini ditempatkan.

    Keputusan user 2026-10-23: supervisor boleh ditempatkan di lebih dari satu
    departemen (satu baris `JabatanOrganisasi` per departemen, tanpa konsep
    "utama" vs "tambahan"). Dipanggil di dalam `tunda_sinkron()` + transaksi
    pemanggil. Baris ber-divisi (manager) tidak disentuh di sini.
    """
    sekarang = {}
    for j in JabatanOrganisasi.objects.filter(
        workspace=workspace, member=user, divisi__isnull=True
    ):
        sekarang.setdefault(str(j.departemen_id), j)
    ingin = {str(d) for d in ingin}
    for did, obj in sekarang.items():
        if did not in ingin:
            obj.delete()  # soft delete: riwayat penempatan tetap ada
    for did in ingin - set(sekarang):
        lama = JabatanOrganisasi.all_objects.filter(
            workspace=workspace, member=user, departemen_id=did
        ).first()
        if lama is None:
            JabatanOrganisasi.objects.create(
                workspace=workspace, member=user, tingkat=tingkat_efektif,
                departemen_id=did, divisi=None, sumber=sumber)
        else:
            lama.deleted_at = None
            lama.tingkat = tingkat_efektif
            lama.divisi = None
            lama.save(update_fields=["deleted_at", "tingkat", "divisi", "updated_at"])


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
            return Response({"error": "Workspace tidak ditemukan."}, status=404)

        hanya_tanpa_atasan = request.query_params.get("hanya_tanpa_atasan") in ("1", "true", "ya")
        divisi_saring = request.query_params.get("divisi")

        projects = {}
        nama_project = {}
        for p in Project.objects.filter(workspace=workspace, deleted_at__isnull=True).only("id", "identifier", "name"):
            projects[p.id] = p.identifier
            nama_project[p.identifier] = p.name

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
        for uid, dep, div in JabatanOrganisasi.objects.filter(workspace=workspace).values_list(
            "member_id", "departemen_id", "divisi_id"
        ):
            if dep:
                dept_orang.setdefault(uid, set()).add(str(dep))
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
            tingkat = peta.get(uid)
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
                    # None = jenjang BELUM DIISI. Sengaja bukan 0 dan bukan "Member":
                    # "datanya kurang" tidak boleh diam-diam berarti "dia staf".
                    "tingkat": tingkat,
                    "tingkat_nama": TINGKAT_NAMA.get(tingkat) if tingkat is not None else None,
                    "sumber": sumber.get(uid),
                    "divisi": sorted(divisi),
                    "divisi_diawasi": sorted(pengawasan.get(uid, set())),
                    # Penempatan (id record, bukan project). None = belum ditempatkan.
                    # Multi-departemen: semua baris departemen orang ini.
                    "departemen_id": utama,
                    "divisi_id": sorted(div_orang.get(uid, set()))[0] if div_orang.get(uid) else None,
                    "departemen_ids": dept_ids,
                    "punya_atasan": punya_atasan,
                }
            )

        total = len(baris)
        punya_jenjang_total = sum(1 for b in baris if b["tingkat"] is not None)
        tanpa_atasan = [b for b in baris if not b["punya_atasan"]]

        if hanya_tanpa_atasan:
            baris = tanpa_atasan
        if divisi_saring:
            baris = [b for b in baris if divisi_saring in b["divisi"]]
        baris.sort(key=lambda b: ((b["tingkat"] is None), -(b["tingkat"] or 0), b["email"]))

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
                    {"id": str(d.id), "kode": d.kode, "nama": d.nama, "divisi_id": str(d.divisi_id)}
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
          "tingkat": 10|20|30|40|null,       # null = jenjang dicabut ("belum diisi")
          "sumber": "...",                    # opsional, default "manual"
          "catatan": "...",                   # opsional
          "pengawasan": ["<project_id>", ...] # opsional: MENGGANTI seluruh baris pengawasan
          "departemen_ids": ["<dep_id>", ...] # opsional: MENGGANTI himpunan departemen
                                                 # orang ini (satu baris jabatan per
                                                 # departemen; supervisor boleh banyak).
                                                 # Kunci tidak dikirim = jangan sentuh.
          "departemen_id": "<dep_id>"|null   # opsional: singkatan satu departemen;
                                                 # DITOLAK (400) kalau orangnya sudah
                                                 # multi-departemen (pakai daftar).
        }
        ```

        `pengawasan` hanya dikirim kalau memang diubah -- bedanya penting, karena
        "tidak dikirim" berarti "jangan sentuh", sedangkan "dikirim kosong" berarti
        "cabut semua".
        """
        from django.db import transaction

        member_id = request.data.get("member_id")
        if not member_id:
            return Response({"error": "member_id wajib dikirim."}, status=400)

        user = User.objects.filter(pk=member_id).first()
        if user is None:
            return Response({"error": "User tidak ditemukan."}, status=404)

        workspace = Workspace.objects.filter(deleted_at__isnull=True).order_by("created_at").first()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=404)

        # --- tingkat -------------------------------------------------------
        if "tingkat" in request.data:
            tingkat = request.data.get("tingkat")
            if tingkat is not None:
                try:
                    tingkat = int(tingkat)
                except (TypeError, ValueError):
                    return Response({"error": "tingkat harus angka atau null."}, status=400)
                if tingkat in _SALAH_KAPAL:
                    return Response({"error": _SALAH_KAPAL[tingkat]}, status=400)
                if tingkat not in _SAH:
                    return Response(
                        {"error": f"tingkat tidak dikenal. Pilihan: {sorted(_SAH)}."}, status=400
                    )
        else:
            tingkat = "tidak-diubah"

        # --- validasi pengawasan sebelum menulis apa pun -------------------
        pengawasan = None
        if "pengawasan" in request.data:
            diminta = request.data.get("pengawasan") or []
            if not isinstance(diminta, list):
                return Response({"error": "pengawasan harus daftar id project."}, status=400)
            sah = set(
                Project.objects.filter(workspace=workspace, deleted_at__isnull=True).values_list("id", flat=True)
            )
            asing = [str(pid) for pid in diminta if str(pid) not in {str(s) for s in sah}]
            if asing:
                # Gagal-tertutup: id yang tidak dikenal lebih mungkin salah kirim daripada
                # niat, dan menyimpannya berarti memberi kewenangan atas project asing.
                return Response(
                    {"error": f"Project tidak dikenal di workspace ini: {', '.join(asing)}."}, status=400
                )
            pengawasan = [pid for pid in diminta]

        # --- penempatan departemen (multi-baris, 2026-10-23) ----------------
        # `departemen_ids`: daftar PENGGANTI himpunan departemen orang ini (satu
        # baris jabatan per departemen; supervisor boleh banyak, staf umumnya satu).
        # Kunci tidak dikirim = jangan sentuh. Daftar kosong = cabut semua baris.
        # `departemen_id` tunggal: singkatan untuk yang SEKARANG cuma punya <=1 baris;
        # kalau orangnya sudah multi-departemen, pakai `departemen_ids` (400).
        dept_ids = "tidak-diubah"
        if "departemen_ids" in request.data:
            diminta = request.data.get("departemen_ids") or []
            if not isinstance(diminta, list):
                return Response({"error": "departemen_ids harus daftar id departemen."}, status=400)
            sah_dep = {
                str(did)
                for did in Departemen.objects.filter(workspace=workspace).values_list("id", flat=True)
            }
            asing_dep = [str(d) for d in diminta if str(d) not in sah_dep]
            if asing_dep:
                return Response(
                    {"error": f"Departemen tidak dikenal di workspace ini: {', '.join(asing_dep)}."}, status=400
                )
            dept_ids = {str(d) for d in diminta}
            if len(dept_ids) > 1:
                # Multi-departemen hanya untuk supervisor (keputusan user 2026-10-23).
                # Staf/manager/direktur satu penempatan; kalau butuh lebih, naikkan
                # dulu jenjangnya ke supervisor di request yang sama.
                if tingkat != "tidak-diubah":
                    efektif = tingkat
                else:
                    efektif = (
                        JabatanOrganisasi.objects.filter(workspace=workspace, member=user)
                        .order_by("-tingkat")
                        .values_list("tingkat", flat=True)
                        .first()
                    )
                if efektif is None:
                    return Response(
                        {"error": "Isi jenjangnya dulu sebelum menempatkan orang ini."}, status=400
                    )
                if efektif != TINGKAT_SUPERVISOR:
                    return Response(
                        {"error": "Hanya supervisor yang boleh memegang beberapa departemen."},
                        status=400,
                    )

        # Turun jenjang di bawah supervisor sambil memegang >1 departemen DITOLAK:
        # rapikan dulu ke satu departemen (dua request eksplisit), jangan diam-diam.
        if isinstance(tingkat, int) and tingkat < TINGKAT_SUPERVISOR:
            banyak = JabatanOrganisasi.objects.filter(
                workspace=workspace, member=user, divisi__isnull=True
            ).count()
            if banyak > 1:
                return Response(
                    {"error": "Turun jenjang butuh satu departemen dulu; rapikan lewat departemen_ids."},
                    status=400,
                )

        # --- penempatan divisi manager (tetap satu kunci) ------------------
        penempatan = {}
        for kunci, model, label in (("divisi_id", Divisi, "Divisi"),):
            if kunci not in request.data:
                continue
            nilai = request.data.get(kunci)
            if nilai and not model.objects.filter(workspace=workspace, pk=nilai).exists():
                return Response({"error": f"{label} tidak ditemukan di workspace ini."}, status=400)
            penempatan[kunci] = nilai or None

        # --- singkatan satu departemen (kompatibilitas editor) -----------
        # `departemen_id` = "jadikan ini satu-satunya departemen". Untuk yang
        # SUDAH multi-departemen DITOLAK (400): menimpa diam-diam berarti
        # mencabut departemen lain tanpa diminta. Editor God Mode mengirim
        # `departemen_ids` lengkap untuk kasus itu.
        if "departemen_id" in request.data and dept_ids == "tidak-diubah":
            nilai = request.data.get("departemen_id")
            if nilai and not Departemen.objects.filter(workspace=workspace, pk=nilai).exists():
                return Response({"error": "Departemen tidak ditemukan di workspace ini."}, status=400)
            ada = JabatanOrganisasi.objects.filter(
                workspace=workspace, member=user, divisi__isnull=True
            ).count()
            if ada > 1:
                return Response(
                    {"error": "Orang ini memegang beberapa departemen; kirim departemen_ids lengkap."},
                    status=400,
                )
            dept_ids = {str(nilai)} if nilai else set()

        with transaction.atomic():
            from plane.db.jangkauan import sinkronkan_satu, tunda_sinkron  # noqa: PLC0415

            with tunda_sinkron():
                # `all_objects` + hidupkan kembali, BUKAN get_or_create dengan manager
                # bawaan: manager bawaan menyaring baris ber-deleted_at, jadi ia akan
                # membuat baris BARU untuk pasangan yang pernah dicabut dan menabrak
                # constraint unik -- jebakan A21, yang di proyek ini sudah pernah
                # memakan satu sesi penuh.
                baris_aktif = list(
                    JabatanOrganisasi.objects.filter(workspace=workspace, member=user).order_by(
                        "departemen_id", "divisi_id"
                    )
                )
                if tingkat is None:
                    # Cabut jenjang = cabut SEMUA baris penempatan (dulu cuma baris
                    # pertama yang tercabut; sisanya yatim dan jangkauannya hidup).
                    for b in baris_aktif:
                        b.delete()  # soft delete: riwayat SIAPA mencabut tetap ada
                elif tingkat != "tidak-diubah" or penempatan or dept_ids != "tidak-diubah":
                    if tingkat == "tidak-diubah" and not baris_aktif:
                        if penempatan or (dept_ids != "tidak-diubah" and dept_ids):
                            return Response({"error": "Isi jenjangnya dulu sebelum menempatkan orang ini."}, status=400)
                    else:
                        if tingkat != "tidak-diubah":
                            tingkat_efektif = tingkat
                        elif baris_aktif:
                            tingkat_efektif = max(b.tingkat for b in baris_aktif)
                        else:
                            # Tanpa baris + tanpa tingkat: hanyaDept_ids kosong yang
                            # tersisa (tidak ada yang perlu dihapus) -> lewati.
                            tingkat_efektif = None
                        if penempatan or tingkat != "tidak-diubah":
                            # `all_objects` + hidupkan kembali, BUKAN get_or_create dengan
                            # manager bawaan: manager bawaan menyaring baris ber-deleted_at,
                            # jadi ia akan membuat baris BARU untuk pasangan yang pernah
                            # dicabut dan menabrak constraint unik (jebakan A21).
                            baris = JabatanOrganisasi.all_objects.filter(
                                workspace=workspace, member=user
                            ).first()
                            if baris is None:
                                baris = JabatanOrganisasi.objects.create(
                                    workspace=workspace,
                                    member=user,
                                    tingkat=tingkat_efektif,
                                    sumber=(request.data.get("sumber") or "manual"),
                                    catatan=(request.data.get("catatan") or ""),
                                )
                                baris_aktif.append(baris)
                            else:
                                if baris.deleted_at is not None:
                                    # Jenjang yang dihidupkan lagi TIDAK membawa penempatan
                                    # lamanya: akses lama tidak boleh kembali tanpa diminta.
                                    baris.departemen_id = None
                                    baris.divisi_id = None
                                baris.deleted_at = None
                            baris.tingkat = tingkat_efektif
                            baris.sumber = request.data.get("sumber") or baris.sumber
                            baris.catatan = request.data.get("catatan") or ""
                            for kunci, nilai in penempatan.items():
                                setattr(baris, kunci, nilai)
                            baris.save(
                                update_fields=[
                                    "deleted_at",
                                    "tingkat",
                                    "sumber",
                                    "catatan",
                                    "departemen",
                                    "divisi",
                                    "updated_at",
                                ]
                            )
                            if baris not in baris_aktif:
                                baris_aktif.append(baris)
                            # Tingkat baru berlaku untuk SEMUA baris orang ini.
                            for b in baris_aktif:
                                if b.pk != baris.pk and b.tingkat != tingkat_efektif:
                                    JabatanOrganisasi.objects.filter(pk=b.pk).update(
                                        tingkat=tingkat_efektif)
                        if dept_ids != "tidak-diubah" and tingkat_efektif is not None:
                            _ganti_departemen_anggota(
                                workspace, user, tingkat_efektif,
                                dept_ids, request.data.get("sumber") or "manual")

                if pengawasan is not None:
                    sekarang = {
                        str(pid)
                        for pid in PengawasanDivisi.objects.filter(workspace=workspace, member=user).values_list(
                            "project_id", flat=True
                        )
                    }
                    ingin = {str(pid) for pid in pengawasan}
                    for pid in sekarang - ingin:
                        obj = PengawasanDivisi.objects.filter(workspace=workspace, member=user, project_id=pid).first()
                        if obj:
                            obj.delete()
                    for pid in ingin - sekarang:
                        lama = PengawasanDivisi.all_objects.filter(
                            workspace=workspace, member=user, project_id=pid
                        ).first()
                        if lama is None:
                            PengawasanDivisi.objects.create(workspace=workspace, member=user, project_id=pid)
                        else:
                            lama.deleted_at = None
                            lama.save(update_fields=["deleted_at", "updated_at"])

            sinkronkan_satu(workspace.id, user.id)

        semua = list(
            JabatanOrganisasi.objects.filter(workspace=workspace, member=user)
            .order_by("departemen_id", "divisi_id")
            .values_list("tingkat", "departemen_id", "divisi_id")
        )
        tingkat_sekarang = max((t for t, _, _ in semua), default=None)
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
                    "tingkat_nama": TINGKAT_NAMA.get(tingkat_sekarang) if tingkat_sekarang is not None else None,
                    "pengawasan": sorted(
                        str(pid)
                        for pid in PengawasanDivisi.objects.filter(workspace=workspace, member=user).values_list(
                            "project_id", flat=True
                        )
                    ),
                }
            }
        )
