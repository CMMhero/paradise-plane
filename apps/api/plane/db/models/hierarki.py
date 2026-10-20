# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: hierarki peran/jabatan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Jenjang organisasi dan "divisi yang dia bawahi".

Rancangan lengkap + pertanyaan yang belum dijawab: `.herdr/hierarki-desain.md`.

## Kenapa dua tabel baru, bukan kolom di model yang sudah ada

`ProjectMember.role` (20/15/5) **sudah punya arti lain** yang terpakai di 699 baris:
KEP-10 menetapkannya sebagai "admin divisi", dan `ProjectEntityPermission` membacanya
untuk memutuskan izin. Menimpanya dengan arti "Supervisor" akan mengubah izin 31 divisi
tanpa satu baris pun diubah — kelas kegagalan yang [[Jebakan & Pelajaran]] sebut paling
mahal. Bukti bahwa kolom itu juga sudah tercampur: 5 akun NON-Super Admin memegang
`role = 20` di ~27–31 divisi masing-masing (lihat BUG usulan di laporan).

`WorkspaceMember.company_role` (satu-satunya kolom "peran di perusahaan" bawaan
upstream) **kosong seluruhnya: 0 dari 96 baris**. Ia juga teks bebas, jadi tidak bisa
dibandingkan. Ia **tidak** dipakai di sini, hanya dilaporkan.

## Kenapa "belum diisi" tidak disamakan dengan "member"

Baris HANYA dibuat untuk orang yang jenjangnya memang sudah ditetapkan. Orang tanpa
baris berarti jenjangnya belum diisi — bukan berarti dia staf. Kalau keduanya
disamakan, 88 orang tiba-tiba "turun jadi staf" tanpa ada yang memutuskan, dan tidak
ada lagi cara membedakan mana yang datanya kurang.

## Kenapa `PengawasanDivisi` tabel pengecualian

Sama alasannya dengan `SuperAdminTerlihatDiProject`: yang perlu ditandai hanya belasan
baris. Kalau tabelnya kosong, perilakunya jatuh ke rumus jenjang (direktur = semua
divisi, manager/supervisor = divisi tempat ia memang anggota) — jadi sistem tetap masuk
akal sebelum ada yang mengisi. Begitu tabelnya diisi, data nyata yang menang.
"""

# Django imports
from django.db import models
from django.db.models import Q

# Module imports
from .base import BaseModel

# Tangga jenjang. Sengaja TIDAK memakai `ROLE` project (20/15/5) supaya dua sumbu itu
# tidak pernah tertukar: angka 20 muncul di dua tempat dengan arti berbeda, dan
# pemanggilnya wajib menyebut nama konstantanya, tidak boleh angka.
TINGKAT_MEMBER = 10
TINGKAT_SUPERVISOR = 20
TINGKAT_MANAGER = 30
TINGKAT_DIREKTUR = 40

TINGKAT_CHOICES = (
    (TINGKAT_MEMBER, "Member"),
    (TINGKAT_SUPERVISOR, "Supervisor"),
    (TINGKAT_MANAGER, "Manager"),
    (TINGKAT_DIREKTUR, "Direktur"),
)

TINGKAT_NAMA = dict(TINGKAT_CHOICES)

# Asal data. Dibedakan supaya tebakan (mis. dari konvensi nama email) bisa dicabut
# seluruhnya tanpa menyentuh data yang berasal dari berkas resmi.
SUMBER_ORG_DIRECTORY = "xlsx-org-directory"
SUMBER_KONVENSI_EMAIL = "email-konvensi"
SUMBER_MANUAL = "manual"


class JabatanOrganisasi(BaseModel):
    """Jenjang satu orang di satu workspace. Satu orang satu baris.

    Jabatan adalah atribut ORANG, bukan atribut keanggotaan project: ia tidak ikut
    berubah saat orangnya pindah divisi. Karena itu tabelnya di level workspace,
    bukan per project — kalau per project, satu jabatan akan punya 31 kebenaran dan
    pindah divisi berarti mengubah dua tempat (drift yang KEP-04 tolak).

    TIDAK ADA baris = jenjang belum diisi. Itu BUKAN "member".
    """

    workspace = models.ForeignKey("db.Workspace", related_name="jabatan_organisasi", on_delete=models.CASCADE)
    member = models.ForeignKey("db.User", related_name="jabatan_organisasi", on_delete=models.CASCADE)
    tingkat = models.PositiveSmallIntegerField(choices=TINGKAT_CHOICES)
    # Dari mana angka ini datang. Bukan hiasan: ia yang membuat tebakan bisa dicabut
    # tanpa menyentuh data resmi, dan ia yang menjawab "kenapa jenjang orang ini begini".
    sumber = models.CharField(max_length=64, default=SUMBER_MANUAL)
    catatan = models.TextField(blank=True, default="")
    # Penempatan (KEP-29), satu sumber kebenaran jangkauan:
    #   staf/supervisor -> `departemen` · manager -> `divisi` (ditetapkan eksplisit,
    #   TIDAK ditebak dari keanggotaan departemen) · direktur -> keduanya kosong.
    departemen = models.ForeignKey(
        "db.Departemen", related_name="penempatan", null=True, blank=True, on_delete=models.SET_NULL
    )
    divisi = models.ForeignKey(
        "db.Divisi", related_name="penempatan_manager", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        # unique_together menyertakan deleted_at mengikuti pola model kustom kita
        # (WikiGovernedProject, WikiFolderAccess, SuperAdminTerlihatDiProject).
        unique_together = ["workspace", "member", "deleted_at"]
        # ...tapi unique_together SAJA tidak cukup: di Postgres, NULL tidak sama dengan
        # NULL, jadi dua baris ber-deleted_at NULL tetap bisa masuk dan orangnya akan
        # punya DUA jenjang sekaligus. Resolusinya lalu bergantung urutan baris — gagal
        # senyap. Constraint parsial di bawah yang benar-benar menutupnya.
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "member"],
                condition=Q(deleted_at__isnull=True),
                name="jabatan_organisasi_unique_aktif",
            )
        ]
        verbose_name = "Jabatan Organisasi"
        verbose_name_plural = "Jabatan Organisasi"
        db_table = "jabatan_organisasi"
        ordering = ("-tingkat", "created_at")

    def __str__(self):
        return f"{self.member_id} = {TINGKAT_NAMA.get(self.tingkat, self.tingkat)}"


class PengawasanDivisi(BaseModel):
    """Baris eksplisit: "orang ini mengawasi divisi (project) ini".

    Dipakai untuk menjawab "divisi yang dia bawahi". Kosong = jatuh ke rumus jenjang,
    sehingga sebelum ada yang mengisi pun sistem tidak buntu:

        direktur  -> semua divisi
        manager   -> divisi tempat ia memang anggota
        supervisor-> divisi tempat ia memang anggota

    Yang mengisinya BELUM DIPUTUSKAN (lihat Pertanyaan #4 di rancangan). Karena itu
    tabel ini sengaja tidak punya endpoint tulis di irisan pertama: mengisinya adalah
    keputusan tata kelola, bukan rincian teknis.
    """

    workspace = models.ForeignKey("db.Workspace", related_name="pengawasan_divisi", on_delete=models.CASCADE)
    project = models.ForeignKey("db.Project", related_name="pengawasan_divisi", on_delete=models.CASCADE)
    member = models.ForeignKey("db.User", related_name="pengawasan_divisi", on_delete=models.CASCADE)
    catatan = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ["project", "member", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "member"],
                condition=Q(deleted_at__isnull=True),
                name="pengawasan_divisi_unique_aktif",
            )
        ]
        verbose_name = "Pengawasan Divisi"
        verbose_name_plural = "Pengawasan Divisi"
        db_table = "pengawasan_divisi"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["workspace", "member"], name="pengawasan_ws_member_idx"),
        ]

    def __str__(self):
        return f"{self.member_id} mengawasi {self.project_id}"
