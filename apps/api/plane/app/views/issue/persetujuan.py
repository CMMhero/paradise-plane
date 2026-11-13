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
from plane.db.models import TINGKAT_SUPERVISOR
from plane.utils.hierarki import (
    boleh_memutuskan,
    calon_penyetuju,
    gerbang_aktif,
    peta_tingkat,
    saring_penyetuju,
    tingkat_anggota,
)
from plane.utils.sinyal_data import siarkan_tugas
from plane.utils.saklar_instance import (
    APPROVAL_REJECT_REASON_REQUIRED,
    APPROVAL_REQUIRED_BELOW_LEVEL,
    ASSIGN_DOWN_ONLY,
    DUE_DATE_CHANGE_RULE,
    TASK_DELETE_RULE,
    saklar_aktif,
    setelan_angka,
)

# Batas baris yang SUDAH diputuskan dalam satu balasan GET. Baris menunggu tidak
# pernah dipotong (itu pekerjaan yang harus dilihat); riwayat keputusan
# (`peran=pemohon`, tanpa `peran`, `?tugas=`) diambil 200 terbaru saja. Tanpa batas,
# staf yang rajin mengajukan membuat daftarnya tumbuh selamanya.
BATAS_RIWAYAT = 200


def _aturan_tugas():
    """Aturan kerja God Mode (KEP-83) yang perlu dicerminkan tampilan.

    Klien memakainya untuk menyembunyikan tombol yang pasti ditolak server
    (`use-aturan-tugas.ts`); penegaknya tetap `task_access` dan `hierarki`.
    Nilai pilihan = konstanta di `plane/utils/saklar_instance.py`.
    """
    return {
        "hapus_tugas": setelan_angka(TASK_DELETE_RULE),
        "ganti_tenggat": setelan_angka(DUE_DATE_CHANGE_RULE),
        "persetujuan_di_bawah": setelan_angka(APPROVAL_REQUIRED_BELOW_LEVEL),
        "alasan_tolak_wajib": saklar_aktif(APPROVAL_REJECT_REASON_REQUIRED),
        "tugaskan_ke_bawah_saja": saklar_aktif(ASSIGN_DOWN_ONLY),
    }


def _q_daftar(user):
    """Baris milik saya (apa pun statusnya) ATAU yang masih menunggu keputusan."""
    return Q(pemohon=user) | Q(status=STATUS_PERSETUJUAN_MENUNGGU)


class _Wewenang:
    """Calon penyetuju + "boleh saya putuskan" satu project, dihitung SEKALI.

    BUG-11: dulu GET menghitung `calon_penyetuju` dua kali dan `tingkat_anggota`
    sekali per calon untuk SETIAP baris (~180 kueri per baris di data lokal, 6 baris
    = 1.085 kueri / 2,4 dtk). Semua baris satu balasan milik project yang sama, jadi
    jawabannya sama untuk semuanya. Aturannya tidak berubah: `boleh_memutuskan`
    tetap satu-satunya penentu, di sini ia cuma diberi daftar yang sudah jadi.
    """

    def __init__(self, user):
        self.user = user
        self._cache = {}
        self._peta = {}

    def _hitung(self, workspace_id, project_id):
        kunci = (str(workspace_id), str(project_id))
        if kunci not in self._cache:
            # KEP-93: jenjang yang berlaku DI project ini, jadi peta per project.
            if kunci not in self._peta:
                self._peta[kunci] = peta_tingkat(workspace_id, project_id)
            peta = self._peta[kunci]
            calon = calon_penyetuju(workspace_id, project_id, peta=peta)
            self._cache[kunci] = (
                # Tingkat dari peta yang sama dengan `tingkat_anggota(..., project_id)`.
                [{"id": str(uid), "tingkat": peta.get(uid)} for uid in calon],
                boleh_memutuskan(self.user, workspace_id, project_id, penyetuju=calon),
            )
        return self._cache[kunci]

    def _sah_untuk(self, baris):
        """Calon penyetuju yang sah untuk pemohon baris ini (`saring_penyetuju`).

        Pengajuan staf: daftar project apa adanya, tanpa kueri tambahan. Pengajuan
        atasan (APPROVAL_REQUIRED_BELOW_LEVEL dinaikkan, KEP-83): hanya yang lebih
        tinggi dari pemohon, dan "boleh" dihitung ulang dari daftar yang tersaring.
        """
        calon, boleh = self._hitung(baris.workspace_id, baris.project_id)
        peta = self._peta[(str(baris.workspace_id), str(baris.project_id))]
        tingkat_pemohon = peta.get(baris.pemohon_id)
        if tingkat_pemohon is None or tingkat_pemohon < TINGKAT_SUPERVISOR:
            return calon, boleh
        calon_ids = {c["id"] for c in calon}
        sah = saring_penyetuju([uid for uid in peta if str(uid) in calon_ids], peta, baris.pemohon_id)
        sah_str = {str(uid) for uid in sah}
        tersaring = [c for c in calon if c["id"] in sah_str]
        return tersaring, boleh_memutuskan(self.user, baris.workspace_id, baris.project_id, penyetuju=sah)

    def penyetuju(self, baris):
        return self._sah_untuk(baris)[0]

    def boleh(self, baris):
        return self._sah_untuk(baris)[1]


def _serial(baris, peran, boleh_memutuskan, penyetuju=None):
    """Daftar-putih. Sengaja BUKAN `fields = "__all__"`.

    Yang menyeberang cuma nomor & judul tugas, status keputusan, dan daftar calon
    penyetuju. Tidak ada assignee lain, label, atau isi deskripsi -- alasan yang sama
    dengan proyeksi lintas divisi (`.herdr/crossdiv-desain.md` §3 poin 2).

    `penyetuju` = daftar `{id, tingkat}` yang sudah dihitung (`_Wewenang`). None =
    hitung di sini, cukup untuk balasan satu baris (POST).
    """
    if penyetuju is None:
        penyetuju = [
            {"id": str(uid), "tingkat": tingkat_anggota(uid, baris.workspace_id, baris.project_id)}
            for uid in calon_penyetuju(baris.workspace_id, baris.project_id)
        ]
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
            # Status tugas SAAT INI. Di balasan POST keputusan ini status SESUDAH
            # setujui (Done) / tolak (In Progress), supaya papan memindahkan kartu
            # tanpa muat ulang (KEP-55).
            "state_id": str(baris.issue.state_id) if baris.issue_id and baris.issue.state_id else None,
        },
        "pemohon": {
            "id": str(baris.pemohon_id),
            "email": baris.pemohon.email if baris.pemohon_id else None,
            "nama": baris.pemohon.display_name if baris.pemohon_id else None,
        },
        "status": baris.status,
        "alasan": baris.alasan,
        "diputuskan_oleh": str(baris.diputuskan_oleh_id) if baris.diputuskan_oleh_id else None,
        "diputuskan_oleh_nama": baris.diputuskan_oleh.display_name if baris.diputuskan_oleh_id else None,
        "diputuskan_pada": baris.diputuskan_pada,
        "boleh_saya_putuskan": boleh_memutuskan,
        # Dihitung ULANG saat dibaca, BUKAN disimpan: begitu God Mode mengisi jenjang
        # orangnya, label "belum ada penyetuju" hilang sendiri tanpa ada yang perlu
        # membersihkan data lama.
        "penyetuju_di_divisi": penyetuju,
        "created_at": baris.created_at,
    }


def _pindahkan_tugas(aktor, issue, tujuan):
    """Ganti status tugas dan catat aktivitasnya atas nama `aktor`."""
    import json  # noqa: PLC0415

    from django.core.serializers.json import DjangoJSONEncoder  # noqa: PLC0415

    from plane.bgtasks.issue_activities_task import issue_activity  # noqa: PLC0415

    lama = issue.state_id
    issue.state = tujuan
    issue.save(update_fields=["state", "completed_at", "updated_at"])
    issue_activity.delay(
        type="issue.activity.updated",
        requested_data=json.dumps({"state_id": str(tujuan.id)}, cls=DjangoJSONEncoder),
        current_instance=json.dumps({"state_id": str(lama)}, cls=DjangoJSONEncoder),
        actor_id=str(aktor.id),
        issue_id=str(issue.id),
        project_id=str(issue.project_id),
        epoch=int(timezone.now().timestamp()),
        notification=True,
    )


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
            _di_bawah_direktur,
            gerbang_aktif,
            tingkat_anggota,
        )
        from plane.db.superadmin import is_super_admin  # noqa: PLC0415
        from plane.db.models import TINGKAT_DIREKTUR, TINGKAT_SUPERVISOR  # noqa: PLC0415

        project = Project.objects.filter(pk=project_id).first()
        if project is None:
            return Response({"error": "Project tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        saya = request.user.id
        from plane.utils.hierarki import adalah_admin_penuh  # noqa: PLC0415

        if (
            not gerbang_aktif()
            or is_super_admin(request.user)
            or adalah_admin_penuh(request.user, project.workspace_id)
        ):
            anggota = list(
                ProjectMember.objects.filter(project_id=project_id, is_active=True).values_list(
                    "member_id", flat=True
                )
            )
            return Response(
                {
                    "mode": "semua",
                    "tingkat_saya": tingkat_anggota(saya, project.workspace_id, project.id),
                    "user_ids": [str(u) for u in anggota],
                    # Klien memakai dua kunci ini untuk mencerminkan `galat_ubah_tugas`:
                    # gerbang mati = tidak ada kunci edit; Super Admin dibaca klien sendiri.
                    "gerbang_aktif": gerbang_aktif(),
                    "aturan": _aturan_tugas(),
                    "bawahan_ids": [],
                }
            )

        tingkat = tingkat_anggota(saya, project.workspace_id, project.id)
        if tingkat is not None and tingkat >= TINGKAT_DIREKTUR:
            anggota = list(
                ProjectMember.objects.filter(project_id=project_id, is_active=True).values_list(
                    "member_id", flat=True
                )
            )
            return Response(
                {
                    "mode": "semua",
                    "tingkat_saya": tingkat,
                    "user_ids": [str(u) for u in anggota],
                    "gerbang_aktif": True,
                    "aturan": _aturan_tugas(),
                    # Hak UBAH direktur tetap "assignee-nya bawahan saya" (`galat_ubah_tugas`),
                    # lebih sempit daripada hak menugaskan "semua anggota".
                    "bawahan_ids": [str(u) for u in _bawahan_ids(saya, project.workspace_id, project_id)],
                }
            )
        if tingkat is not None and tingkat >= TINGKAT_SUPERVISOR:
            bawahan = _bawahan_ids(saya, project.workspace_id, project_id)
            # `_bawahan_ids` sudah hanya memuat anggota project ini, dan baris
            # `boleh &= anggota` di bawah menyaring sekali lagi. Pemeriksaan
            # keanggotaan per bawahan yang dulu ada di sini (satu kueri per
            # orang) jadi berlebih dan dibuang.
            boleh = {saya} | bawahan
            # Batasi ke anggota project ini (bawahan di divisi lain tak relevan).
            anggota = set(
                ProjectMember.objects.filter(project_id=project_id, is_active=True).values_list(
                    "member_id", flat=True
                )
            )
            # KEP-83: ASSIGN_DOWN_ONLY dimatikan = `galat_penugasan` tidak lagi
            # memeriksa jenjang penerima di divisi yang saya awasi, jadi seluruh
            # anggotanya boleh dipilih. Hak UBAH (`bawahan_ids`) tetap per jenjang.
            if not saklar_aktif(ASSIGN_DOWN_ONLY):
                from plane.utils.hierarki import divisi_diawasi  # noqa: PLC0415

                if str(project_id) in {str(p) for p in divisi_diawasi(saya, project.workspace_id)}:
                    boleh |= anggota
            boleh &= anggota
            # Sekretaris (KEP-101) tidak pernah boleh menugaskan direktur, walau saklar
            # ASSIGN_DOWN_ONLY mati: samakan daftar dengan `galat_penugasan`.
            if _di_bawah_direktur(tingkat):
                from plane.utils.hierarki import peta_tingkat  # noqa: PLC0415

                peta = peta_tingkat(project.workspace_id, project_id)
                boleh = {u for u in boleh if u == saya or peta.get(u, 0) < TINGKAT_DIREKTUR}
            users = {u.id: u for u in User.objects.filter(id__in=boleh)}
            return Response(
                {
                    "mode": "bawahan",
                    "tingkat_saya": tingkat,
                    "gerbang_aktif": True,
                    "aturan": _aturan_tugas(),
                    # Tanpa saringan anggota project: sama persis dengan yang dibaca `galat_ubah_tugas`.
                    "bawahan_ids": [str(u) for u in bawahan],
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
        from plane.utils.hierarki import rekan_staf_ids  # noqa: PLC0415

        boleh = {saya} | rekan_staf_ids(saya, project.workspace_id, project.id)
        users = {u.id: u for u in User.objects.filter(id__in=boleh)}
        return Response(
            {
                # "diri-sendiri" dipertahankan saat tak ada rekan: klien lama tetap benar.
                "mode": "rekan" if len(boleh) > 1 else "diri-sendiri",
                "tingkat_saya": tingkat,
                "gerbang_aktif": True,
                "aturan": _aturan_tugas(),
                # Rekan boleh DIAJAK, bukan disunting tugasnya: staf hanya mengubah tugas yang melibatkan dirinya.
                "bawahan_ids": [],
                "users": [
                    {"id": str(uid), "nama": users[uid].display_name, "email": users[uid].email}
                    for uid in sorted(boleh, key=lambda u: (u != saya, str(u)))
                    if uid in users
                ],
            }
        )


class PersetujuanPenugasanEndpoint(BaseAPIView):
    """`GET` daftar · `POST` putuskan (setujui/tolak)."""

    permission_classes = [ProjectEntityPermission]

    @staticmethod
    def _boleh_putuskan(user, baris, wewenang):
        """Predikat TUNGGAL "user ini boleh memutuskan baris ini".

        Dipakai tombol di daftar, penyaring antrean, dan (lewat `wewenang.boleh`)
        pemeriksaan 403 di POST, jadi antrean tidak pernah menampilkan baris yang
        akan ditolak server.
        """
        return (
            baris.pemohon_id != user.id
            and baris.status == STATUS_PERSETUJUAN_MENUNGGU
            and wewenang.boleh(baris)
        )

    def _saring_antrean(self, user, semua, wewenang, hanya_putusan=False):
        """Buang baris orang lain yang tidak boleh saya putuskan; satu baris terbaru per tugas.

        * Milik saya (pemohon) selalu tampil, apa pun statusnya.
        * Milik orang lain hanya tampil kalau menunggu DAN saya penyetujunya yang sah.
        * Per tugas hanya baris TERBARU yang tampil: tugas yang ditolak lalu diajukan
          ulang punya baris `ditolak` lama dan baris `menunggu` baru, dan yang lama
          cuma riwayat (riwayat lengkap tetap ada lewat `?tugas=`).
        `hanya_putusan` (`peran=penyetuju`, tab "perlu keputusan saya"): hanya baris
        yang boleh saya putuskan, jadi pengajuan saya sendiri tidak ikut.
        `semua` sudah terurut terbaru dulu; `wewenang` men-cache per project, jadi
        tidak ada kueri per baris.
        """
        terlihat = set()
        hasil = []
        for baris in semua:
            kunci = baris.issue_id or baris.id
            if kunci in terlihat:
                continue
            terlihat.add(kunci)
            boleh = self._boleh_putuskan(user, baris, wewenang)
            if boleh or (not hanya_putusan and baris.pemohon_id == user.id):
                hasil.append(baris)
        return hasil

    def get(self, request, slug, project_id):
        sudut = request.query_params.get("peran")
        if sudut not in (None, "pemohon", "penyetuju"):
            return Response({"error": "peran harus 'pemohon' atau 'penyetuju'."}, status=status.HTTP_400_BAD_REQUEST)

        project = Project.objects.filter(pk=project_id).first()
        if project is None:
            return Response({"error": "Project tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        dasar = (
            PersetujuanPenugasan.objects.filter(project_id=project_id)
            .select_related("issue", "issue__project", "pemohon", "diputuskan_oleh")
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
        elif not tugas:
            # Dengan `?tugas=` tanpa `peran`: riwayat LENGKAP satu tugas untuk
            # detail work item (KEP-55). Semua anggota project boleh melihat tugas
            # apa pun (KEP-38), jadi log keputusannya juga.
            dasar = dasar.filter(_q_daftar(request.user))

        # Terbaru dulu. Menunggu selalu utuh; riwayat keputusan dipotong
        # `BATAS_RIWAYAT` (indeks `persetujuan_proyek_status_idx` menutup keduanya).
        dasar = dasar.order_by("-created_at")
        semua = list(dasar.filter(status=STATUS_PERSETUJUAN_MENUNGGU))
        if sudut != "penyetuju":
            semua += list(dasar.exclude(status=STATUS_PERSETUJUAN_MENUNGGU)[:BATAS_RIWAYAT])
            semua.sort(key=lambda b: b.created_at, reverse=True)

        wewenang = _Wewenang(request.user)
        if not tugas:
            semua = self._saring_antrean(request.user, semua, wewenang, hanya_putusan=sudut == "penyetuju")
        hasil = []
        for baris in semua:
            # Atasan yang sah saja; Super Admin hanya kalau divisi tanpa atasan sama
            # sekali (lihat `boleh_memutuskan`). Dihitung sekali per project.
            boleh = self._boleh_putuskan(request.user, baris, wewenang)
            hasil.append(
                _serial(
                    baris,
                    "pemohon" if baris.pemohon_id == request.user.id else "penyetuju",
                    boleh,
                    penyetuju=wewenang.penyetuju(baris),
                )
            )

        return Response(
            {
                "gerbang_aktif": gerbang_aktif(),
                "aturan": _aturan_tugas(),
                "tingkat_saya": tingkat_anggota(request.user.id, project.workspace_id, project.id),
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
            .select_related("issue", "issue__project", "pemohon", "diputuskan_oleh")
            .first()
        )
        if baris is None:
            return Response({"error": "Permintaan persetujuan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if baris.status != STATUS_PERSETUJUAN_MENUNGGU:
            return Response({"error": f"Permintaan ini sudah {baris.status}."}, status=status.HTTP_400_BAD_REQUEST)

        # Diperiksa ULANG di sini, bukan dipercaya dari daftar: kewenangan bisa berubah
        # antara menampilkan daftar dan menekan tombol. Super Admin lolos sebagai
        # jalan keluar (B1), cermin pengecualian yang sama di kunci persetujuan.
        wewenang = _Wewenang(request.user)
        if not wewenang.boleh(baris):
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
        if aksi == "tolak" and not alasan and saklar_aktif(APPROVAL_REJECT_REASON_REQUIRED):
            # Penolakan tanpa alasan memaksa orang menebak, dan tebakan atas alasan orang
            # lain adalah cara termurah kehilangan kepercayaan. KEP-83: wajibnya diatur
            # di God Mode (bawaan menyala = perilaku lama).
            return Response({"error": "Alasan penolakan wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        baris.status = STATUS_PERSETUJUAN_DISETUJUI if aksi == "setujui" else STATUS_PERSETUJUAN_DITOLAK
        baris.diputuskan_oleh = request.user
        baris.diputuskan_pada = timezone.now()
        baris.alasan = alasan
        baris.save(update_fields=["status", "diputuskan_oleh", "diputuskan_pada", "alasan", "updated_at"])
        from plane.utils.notifikasi_persetujuan import beritahu_diputuskan  # noqa: PLC0415

        beritahu_diputuskan(baris, aksi)
        # Kartu permintaan di obrolan para atasan kehilangan tombolnya.
        from plane.utils.kartu_obrolan import tandai_persetujuan_diputuskan  # noqa: PLC0415

        tandai_persetujuan_diputuskan(baris.id, baris.status)
        from plane.utils.hierarki import (  # noqa: PLC0415
            AKTIVITAS_DISETUJUI,
            AKTIVITAS_DITOLAK,
            catat_aktivitas_persetujuan,
        )

        if baris.issue_id:
            catat_aktivitas_persetujuan(
                baris, AKTIVITAS_DISETUJUI if aksi == "setujui" else AKTIVITAS_DITOLAK, request.user, alasan
            )

        if aksi == "setujui" and baris.issue_id:
            self._selesaikan_tugas(request, baris)

        # Ditolak = tugas kembali ke In Progress (KEP-55). Staf mengerjakannya lagi
        # lalu mengajukan ulang dengan menggeser ke selesai lagi (atau `ajukan-ulang`).
        if aksi == "tolak" and baris.issue_id:
            self._kembalikan_tugas(request, baris)
        # `baris.issue` dimuat SEBELUM status dipindah (objek lain yang disimpan),
        # jadi dibaca ulang: `tugas.state_id` di balasan wajib status sesudahnya.
        if baris.issue_id:
            baris.issue.refresh_from_db(fields=["state"])
        # Antrean dan chip persetujuan di layar orang lain ikut menyegarkan diri.
        siarkan_tugas(baris.project_id, baris.issue_id, bidang=["approval"], oleh_id=request.user.id)
        return Response(_serial(baris, "penyetuju", False, penyetuju=wewenang.penyetuju(baris)))

    def _selesaikan_tugas(self, request, baris):
        """Pindahkan tugas ke status selesai setelah atasan menyetujui.

        Sejak KEP-55 tugas TETAP di status semula selama menunggu, jadi jalur
        biasanya memindahkan tugas ke status `completed` pertama di project (urut
        sequence). Waktu selesainya (`completed_at`, dan Due date otomatis yang
        dihitung darinya) mengikuti APPROVAL_FINISH_TIME (KEP-84): bawaan = saat
        pengajuan ini dibuat (`baris.created_at`; ajukan ulang = baris baru, jadi
        waktu pengajuan TERAKHIR), atau saat disetujui.
        """
        from plane.db.models import Issue, State  # noqa: PLC0415
        from plane.utils.saklar_instance import (  # noqa: PLC0415
            APPROVAL_FINISH_TIME,
            SELESAI_SAAT_DIAJUKAN,
            setelan_angka,
        )

        issue = Issue.objects.filter(pk=baris.issue_id).select_related("state", "project").first()
        if issue is None:
            return
        # Data lama (sebelum KEP-55): tugas sudah berstatus selesai sejak diajukan.
        # Statusnya tak berpindah, jadi tanggal selesai otomatis (KEP-41) diisi di
        # sini dari `completed_at` yang sudah ada. Tidak diubah oleh KEP-84.
        if issue.state is not None and issue.state.group == "completed":
            issue.isi_tanggal_selesai(actor_id=request.user.id)
            return
        selesai = State.objects.filter(project_id=baris.project_id, group="completed").order_by("sequence").first()
        if selesai is None:
            return
        if setelan_angka(APPROVAL_FINISH_TIME) == SELESAI_SAAT_DIAJUKAN:
            issue._completed_at_override = baris.created_at
        _pindahkan_tugas(request.user, issue, selesai)

    def _kembalikan_tugas(self, request, baris):
        """Tolak: kembalikan tugas ke In Progress supaya staf mengerjakannya lagi.

        KEP-55 (keputusan user 2 Nov 2026, "if rejected return to in progress"):
        tujuannya status `started` pertama project, apa pun status asalnya. Kalau
        project tidak punya status `started`, jatuh ke `state_sebelumnya`, lalu
        status bawaan. Tugas yang sudah di `started` atau dibatalkan dibiarkan.
        """
        from plane.db.models import Issue, State  # noqa: PLC0415

        issue = Issue.objects.filter(pk=baris.issue_id).select_related("state").first()
        if issue is None or (issue.state is not None and issue.state.group in ("started", "cancelled")):
            return
        dasar = State.objects.filter(project_id=baris.project_id)
        tujuan = (
            dasar.filter(group="started").order_by("sequence").first()
            or dasar.filter(pk=baris.state_sebelumnya_id).exclude(group="completed").first()
            or dasar.exclude(group__in=["completed", "cancelled"]).filter(default=True).first()
        )
        if tujuan is None or tujuan.id == issue.state_id:
            return
        _pindahkan_tugas(request.user, issue, tujuan)

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
            .select_related("issue", "issue__project", "pemohon", "diputuskan_oleh")
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

        from plane.db.models import Issue  # noqa: PLC0415
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
        # Diajukan ulang = pengajuan baru. Statusnya TIDAK dipindah (KEP-55):
        # tugas baru masuk selesai saat atasan menyetujui. `catat_persetujuan`
        # idempoten, menulis log, dan memberi tahu atasan.
        from plane.utils.hierarki import catat_persetujuan  # noqa: PLC0415

        baru = catat_persetujuan(issue, actor=request.user, state_sebelumnya_id=issue.state_id)
        siarkan_tugas(baris.project_id, issue.id, bidang=["approval"], oleh_id=request.user.id)
        # None hanya kalau gerbang hierarki dimatikan di tengah jalan.
        return Response(_serial(baru or baris, "pemohon", False))
