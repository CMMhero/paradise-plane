# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: antrean persetujuan penugasan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`persetujuan-penugasan/` — antrean persetujuan + keputusan.

Keputusan user 2026-10-15 (`.herdr/hierarki-desain.md` §12):

* Yang butuh persetujuan **hanya jabatan member** yang menugaskan ke dirinya sendiri.
* Yang menyetujui adalah **atasan pembuat di divisinya** -- supervisor, manager, atau
  direktur. Siapa pun yang tingkatnya lebih tinggi dari pembuat dan mengawasi divisi itu.
* Tugasnya **tetap muncul** dengan indikator; baris di `persetujuan_penugasan` itulah
  indikatornya (tugasnya TIDAK dipindah ke Triage dan TIDAK disembunyikan).

## Kenapa satu endpoint dengan dua sudut pandang

Orang yang sama bisa menjadi **pemohon** di satu tugas dan **penyetuju** di tugas lain.
Memisahkannya jadi dua endpoint membuat daftar "tugas saya yang belum disetujui"
(muncul + indikator) mustahil ditampilkan bersama daftar "yang perlu saya setujui".
Query param `?peran=pemohon|penyetuju` memilih sudut pandangnya; tanpa param, keduanya
digabung dan tiap baris menyebut perannya.

## Kenapa kewenangan diperiksa ULANG saat keputusan diambil

Daftar calon penyetuju bisa berubah antara saat tugas dibuat dan saat tombolnya ditekan
(orang pindah divisi, jenjangnya berubah, atau ia sendiri yang jadi pemohon). Kalau
kewenangan hanya diperiksa waktu menampilkan daftar, siapa pun yang menyimpan id-nya bisa
memutuskan. Karena itu `setujui`/`tolak` memanggil `calon_penyetuju()` lagi -- dan
**menolak kalau tidak ada di daftar** (gagal ke arah aman, prinsip #3).
"""

# Django imports
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import ProjectEntityPermission
from plane.db.models import (
    PersetujuanPenugasan,
    Project,
    STATUS_PERSETUJUAN_DISETUJUI,
    STATUS_PERSETUJUAN_DITOLAK,
    STATUS_PERSETUJUAN_MENUNGGU,
)
from plane.utils.hierarki import calon_penyetuju, gerbang_aktif, tingkat_anggota


def _q_daftar(user):
    """Baris milik saya (apa pun statusnya) ATAU yang masih menunggu keputusan."""
    return Q(pemohon=user) | Q(status=STATUS_PERSETUJUAN_MENUNGGU)


def _serial(baris, peran, boleh_memutuskan):
    """Daftar-putih. Sengaja BUKAN `fields = "__all__"`.

    Yang menyeberang cuma nomor & judul tugas, status keputusan, dan daftar calon
    penyetuju. Tidak ada assignee lain, label, atau isi deskripsi -- alasan yang sama
    dengan proyeksi lintas divisi (`.herdr/crossdiv-desain.md` §3 poin 2).
    """
    return {
        "id": str(baris.id),
        "peran_saya": peran,
        "tugas": {
            "id": str(baris.issue_id),
            # Nomor tugas dirakit dari identifier project + sequence_id, sama seperti yang
            # dilakukan serializer bawaan Plane (`Issue` tidak punya kolom `identifier`).
            "nomor": (
                f"{baris.issue.project.identifier}-{baris.issue.sequence_id}"
                if baris.issue_id and baris.issue.project_id
                else None
            ),
            "judul": baris.issue.name if baris.issue_id else None,
        },
        "pemohon": {
            "id": str(baris.pemohon_id),
            "email": baris.pemohon.email if baris.pemohon_id else None,
            "nama": baris.pemohon.display_name if baris.pemohon_id else None,
        },
        "status": baris.status,
        "alasan": baris.alasan,
        "diputuskan_oleh": str(baris.diputuskan_oleh_id) if baris.diputuskan_oleh_id else None,
        "diputuskan_pada": baris.diputuskan_pada,
        "boleh_saya_putuskan": boleh_memutuskan,
        # Dihitung ULANG saat dibaca, BUKAN disimpan: begitu God Mode mengisi jenjang
        # orangnya, label "belum ada penyetuju" hilang sendiri tanpa ada yang perlu
        # membersihkan data lama.
        "penyetuju_di_divisi": [
            {"id": str(uid), "tingkat": tingkat_anggota(uid, baris.workspace_id)}
            for uid in calon_penyetuju(baris.workspace_id, baris.project_id)
        ],
        "created_at": baris.created_at,
    }


class PenggunaBisaDitugaskanEndpoint(BaseAPIView):
    """`GET` siapa saja yang boleh saya assign di project ini.

    Keputusan user: dropdown assignee berisi "hanya user kita, atau bawahan
    kita". Staf → `[diri sendiri]`. Atasan → diri sendiri + bawahan (tingkat
    lebih rendah di divisi yang dia awasi). Direktur/Super Admin → seluruh
    anggota project. Server pemegang keputusan; UI hanya menampilkan daftar ini
    supaya tidak ada pilihan yang pasti ditolak.
    """

    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id):
        from plane.db.models import ProjectMember, User  # noqa: PLC0415
        from plane.utils.hierarki import (  # noqa: PLC0415
            _bawahan_ids,
            divisi_anggota,
            gerbang_aktif,
            tingkat_anggota,
        )
        from plane.db.superadmin import is_super_admin  # noqa: PLC0415
        from plane.db.models import TINGKAT_DIREKTUR, TINGKAT_SUPERVISOR  # noqa: PLC0415

        project = Project.objects.filter(pk=project_id).first()
        if project is None:
            return Response({"error": "Project tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        saya = request.user.id
        if not gerbang_aktif() or is_super_admin(request.user):
            anggota = list(
                ProjectMember.objects.filter(project_id=project_id, is_active=True).values_list(
                    "member_id", flat=True
                )
            )
            return Response(
                {
                    "mode": "semua",
                    "tingkat_saya": tingkat_anggota(saya, project.workspace_id),
                    "user_ids": [str(u) for u in anggota],
                }
            )

        tingkat = tingkat_anggota(saya, project.workspace_id)
        if tingkat is not None and tingkat >= TINGKAT_DIREKTUR:
            anggota = list(
                ProjectMember.objects.filter(project_id=project_id, is_active=True).values_list(
                    "member_id", flat=True
                )
            )
            return Response({"mode": "semua", "tingkat_saya": tingkat, "user_ids": [str(u) for u in anggota]})
        if tingkat is not None and tingkat >= TINGKAT_SUPERVISOR:
            bawahan = _bawahan_ids(saya, project.workspace_id, project_id)
            # BUG 2026-10-16: tadinya `u in divisi_anggota(u, …)` — id USER
            # dibandingkan ke himpunan id PROJECT, jadi selalu False dan
            # dropdown atasan selalu kosong. Yang benar: bawahan itu anggota
            # PROJECT INI.
            boleh = {saya} | {
                u for u in bawahan if str(project_id) in {str(p) for p in divisi_anggota(u, project.workspace_id)}
            }
            # Batasi ke anggota project ini (bawahan di divisi lain tak relevan).
            anggota = set(
                ProjectMember.objects.filter(project_id=project_id, is_active=True).values_list(
                    "member_id", flat=True
                )
            )
            boleh &= anggota
            users = {u.id: u for u in User.objects.filter(id__in=boleh)}
            return Response(
                {
                    "mode": "bawahan",
                    "tingkat_saya": tingkat,
                    "users": [
                        {
                            "id": str(uid),
                            "nama": users[uid].display_name if uid in users else None,
                            "email": users[uid].email if uid in users else None,
                        }
                        for uid in sorted(boleh, key=lambda u: (u != saya, str(u)))
                    ],
                }
            )
        return Response(
            {
                "mode": "diri-sendiri",
                "tingkat_saya": tingkat,
                "users": [{"id": str(saya), "nama": request.user.display_name, "email": request.user.email}],
            }
        )


class PersetujuanPenugasanEndpoint(BaseAPIView):
    """`GET` daftar · `POST` putuskan (setujui/tolak)."""

    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id):
        from plane.db.superadmin import is_super_admin  # noqa: PLC0415

        sudut = request.query_params.get("peran")
        if sudut not in (None, "pemohon", "penyetuju"):
            return Response({"error": "peran harus 'pemohon' atau 'penyetuju'."}, status=status.HTTP_400_BAD_REQUEST)

        project = Project.objects.filter(pk=project_id).first()
        if project is None:
            return Response({"error": "Project tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        dasar = (
            PersetujuanPenugasan.objects.filter(project_id=project_id)
            .select_related("issue", "issue__project", "pemohon")
        )
        # `?tugas=<issue_id>`: dipakai indikator di sidebar work item. Tanpa ini,
        # komponen itu harus mengunduh SELURUH antrean project hanya untuk menjawab
        # "tugas yang sedang saya buka ini statusnya apa".
        tugas = request.query_params.get("tugas")
        if tugas:
            dasar = dasar.filter(issue_id=tugas)
        if sudut == "pemohon":
            dasar = dasar.filter(pemohon=request.user)
        elif sudut == "penyetuju":
            dasar = dasar.filter(status=STATUS_PERSETUJUAN_MENUNGGU)
        else:
            dasar = dasar.filter(_q_daftar(request.user))

        hasil = []
        for baris in dasar:
            penyetuju = calon_penyetuju(baris.workspace_id, baris.project_id)
            # Super Admin boleh memutuskan sebagai jalan keluar (B1) -- sama seperti
            # kunci persetujuan yang meloloskan Super Admin. Tanpa ini, antrean yang
            # belum punya atasan terdaftar (struktur divisi masih diisi) menggantung
            # tanpa ada seorang pun yang bisa memutusnya, termasuk IT sendiri.
            # Routing tetap milik hierarki: daftar penyetuju di bawah tidak berubah.
            boleh = (request.user.id in penyetuju or is_super_admin(request.user)) and baris.status == STATUS_PERSETUJUAN_MENUNGGU
            hasil.append(
                _serial(
                    baris,
                    "pemohon" if baris.pemohon_id == request.user.id else "penyetuju",
                    boleh,
                )
            )

        return Response(
            {
                "gerbang_aktif": gerbang_aktif(),
                "tingkat_saya": tingkat_anggota(request.user.id, project.workspace_id),
                "jumlah": len(hasil),
                "hasil": hasil,
            }
        )

    @transaction.atomic
    def post(self, request, slug, project_id, pk=None):
        aksi = request.data.get("aksi")
        if aksi == "ajukan-ulang":
            return self.ajukan_ulang(request, slug, project_id, pk=pk)
        if aksi not in ("setujui", "tolak"):
            return Response(
                {"error": "aksi harus 'setujui', 'tolak', atau 'ajukan-ulang'."}, status=status.HTTP_400_BAD_REQUEST
            )
        if pk is None:
            return Response({"error": "Id permintaan wajib dikirim."}, status=status.HTTP_400_BAD_REQUEST)

        baris = (
            PersetujuanPenugasan.objects.filter(pk=pk, project_id=project_id)
            .select_related("issue", "issue__project", "pemohon")
            .first()
        )
        if baris is None:
            return Response({"error": "Permintaan persetujuan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if baris.status != STATUS_PERSETUJUAN_MENUNGGU:
            return Response({"error": f"Permintaan ini sudah {baris.status}."}, status=status.HTTP_400_BAD_REQUEST)

        # Diperiksa ULANG di sini, bukan dipercaya dari daftar: kewenangan bisa berubah
        # antara menampilkan daftar dan menekan tombol. Super Admin lolos sebagai
        # jalan keluar (B1), cermin pengecualian yang sama di kunci persetujuan.
        from plane.db.superadmin import is_super_admin  # noqa: PLC0415

        penyetuju = calon_penyetuju(baris.workspace_id, baris.project_id)
        if request.user.id not in penyetuju and not is_super_admin(request.user):
            return Response(
                {"error": "Anda bukan atasan pembuat di divisi ini, jadi tidak dapat memutuskan."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if baris.pemohon_id == request.user.id:
            return Response(
                {"error": "Pembuat tugas tidak dapat menyetujui tugasnya sendiri."},
                status=status.HTTP_403_FORBIDDEN,
            )

        alasan = (request.data.get("alasan") or "").strip()
        if aksi == "tolak" and not alasan:
            # Penolakan tanpa alasan memaksa orang menebak, dan tebakan atas alasan orang
            # lain adalah cara termurah kehilangan kepercayaan.
            return Response({"error": "Alasan penolakan wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        baris.status = STATUS_PERSETUJUAN_DISETUJUI if aksi == "setujui" else STATUS_PERSETUJUAN_DITOLAK
        baris.diputuskan_oleh = request.user
        baris.diputuskan_pada = timezone.now()
        baris.alasan = alasan
        baris.save(update_fields=["status", "diputuskan_oleh", "diputuskan_pada", "alasan", "updated_at"])

        if aksi == "tolak" and baris.issue_id:
            # Keputusan user 2026-10-16 (menggantikan 2026-10-15): tugas yang
            # ditolak KEMBALI ke draft tak-terlihat (`is_draft=True` sudah
            # dikecualikan semua queryset papan), bukan tetap muncul. Staf
            # mengajukan ulang dari tab "Pengajuan saya" (aksi `ajukan-ulang`).
            # Assignee SENGAJA tidak dicabut: jejak siapa mengerjakan apa tetap
            # ada, dan pengajuan-ulang tidak perlu menebak penerimanya.
            from plane.db.models import Issue  # noqa: PLC0415

            Issue.objects.filter(pk=baris.issue_id).update(is_draft=True)

        # Ditolak TIDAK menghapus tugasnya — hanya disembunyikan dari papan
        # (lihat di atas). Dihapus berarti pekerjaan yang sudah dimulai hilang
        # tanpa jejak.
        return Response(_serial(baris, "penyetuju", False))

    @transaction.atomic
    def ajukan_ulang(self, request, slug, project_id, pk=None):
        """Staf mengajukan ulang tugasnya yang ditolak (kembali ke antrean).

        Hanya PEMOHON yang boleh: atasan tidak perlu mengajukan untuk orang
        lain, dan orang lain tidak boleh mengutak-atik draft orang. Efeknya:
        `is_draft=False` (muncul lagi di papan) + baris menunggu BARU (riwayat
        penolakan tetap utuh — tidak menimpa baris lama).
        """
        if pk is None:
            return Response({"error": "Id permintaan wajib dikirim."}, status=status.HTTP_400_BAD_REQUEST)

        baris = (
            PersetujuanPenugasan.objects.filter(pk=pk, project_id=project_id)
            .select_related("issue", "issue__project", "pemohon")
            .first()
        )
        if baris is None:
            return Response({"error": "Permintaan persetujuan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if baris.pemohon_id != request.user.id:
            return Response(
                {"error": "Hanya pembuat tugas ini yang dapat mengajukan ulang."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if baris.status != STATUS_PERSETUJUAN_DITOLAK:
            return Response(
                {"error": "Hanya permintaan yang ditolak yang dapat diajukan ulang."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from plane.db.models import Issue, PersetujuanPenugasan as Baris  # noqa: PLC0415
        from plane.utils.hierarki import butuh_persetujuan  # noqa: PLC0415

        issue = Issue.objects.filter(pk=baris.issue_id).first()
        if issue is None:
            return Response({"error": "Tugasnya sudah tidak ada."}, status=status.HTTP_404_NOT_FOUND)

        penerima_ids = list(issue.issue_assignee.values_list("assignee_id", flat=True))
        if not butuh_persetujuan(request.user, baris.project_id, penerima_ids):
            # Keadaan berubah sejak ditolak (mis. pembuatnya kini atasan, atau
            # penugasannya sudah dipindah): cukup munculkan lagi, tanpa antrean.
            issue.is_draft = False
            issue.save(update_fields=["is_draft", "updated_at"])
            return Response(_serial(baris, "pemohon", False))

        issue.is_draft = False
        issue.save(update_fields=["is_draft", "updated_at"])
        baru = Baris.objects.create(
            workspace_id=baris.workspace_id,
            project_id=baris.project_id,
            issue_id=baris.issue_id,
            pemohon=request.user,
            penerima=request.user,
        )
        return Response(_serial(baru, "pemohon", False))
