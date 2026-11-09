# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Wiki mandiri (KEP-94)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Wiki sebagai fitur sendiri, bukan project.

Sampai KEP-94 Wiki adalah project ber-identifier WIKI: folder = Page, materi =
FileAsset ber-FK page, dan hak unggah dihitung dari keanggotaan project
departemen. Akibatnya tiap orang harus jadi anggota project WIKI, project itu
muncul di daftar penugasan anggota, dan judul folder hidup di binary Yjs.

Sekarang:

- `WikiFolder` = satu simpul pohon. Folder unit (`divisi` atau `departemen`
  terisi) dibuat dan dinamai otomatis dari struktur organisasi; folder lain
  (topik, General) dibuat admin.
- `WikiMaterial` = satu berkas di satu folder. Berkasnya tetap `FileAsset`
  (kunci MinIO tidak memuat id project, jadi tidak ada objek yang dipindah),
  hanya tidak lagi menunjuk project atau page.
- Hak dibaca dari penempatan organisasi (`plane.db.penempatan`), bukan dari
  keanggotaan project. Lihat `plane.utils.wiki_mandiri`.
"""

from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Lookup, Q

from .base import BaseModel


@models.CharField.register_lookup
@models.TextField.register_lookup
class KataMirip(Lookup):
    """`kolom__kata_mirip="kata"`: ada kata di kolom yang mirip dengan `kata`
    (pg_trgm `<%`), jadi salah ketik satu-dua huruf tetap ketemu. Tidak
    memasang `django.contrib.postgres` ke INSTALLED_APPS demi satu operator.
    Ambangnya `pg_trgm.word_similarity_threshold`, diatur per permintaan oleh
    pemanggil (`plane.utils.wiki_cari`)."""

    lookup_name = "kata_mirip"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return f"{rhs} <%% {lhs}", [*rhs_params, *lhs_params]


class WikiFolder(BaseModel):
    workspace = models.ForeignKey("db.Workspace", related_name="wiki_folder", on_delete=models.CASCADE)
    parent = models.ForeignKey("self", related_name="anak", null=True, blank=True, on_delete=models.CASCADE)
    nama = models.CharField(max_length=255)
    # Keterangan singkat di bawah judul (dulu description halaman topik).
    keterangan = models.TextField(blank=True, default="")
    # Isi halaman lama yang dibawa migrasi 0170, hanya-baca. Kosong untuk folder baru.
    isi_lama_html = models.TextField(blank=True, default="")
    logo_props = models.JSONField(default=dict, blank=True)
    urutan = models.FloatField(default=65535)
    # Pemilik unit. Folder divisi dan folder departemen dibuat oleh
    # `pastikan_folder_unit`; namanya mengikuti unit dan tidak diubah tangan.
    divisi = models.ForeignKey(
        "db.Divisi", related_name="wiki_folder", null=True, blank=True, on_delete=models.SET_NULL
    )
    departemen = models.ForeignKey(
        "db.Departemen", related_name="wiki_folder", null=True, blank=True, on_delete=models.SET_NULL
    )
    # Folder General: semua anggota workspace boleh mengunggah di dalamnya.
    umum = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "wiki_folder"
        verbose_name = "Wiki folder"
        verbose_name_plural = "Wiki folders"
        ordering = ("urutan", "nama")
        constraints = [
            models.UniqueConstraint(
                fields=["divisi"],
                condition=Q(deleted_at__isnull=True, divisi__isnull=False),
                name="wiki_folder_satu_per_divisi",
            ),
            models.UniqueConstraint(
                fields=["departemen"],
                condition=Q(deleted_at__isnull=True, departemen__isnull=False),
                name="wiki_folder_satu_per_departemen",
            ),
            models.CheckConstraint(
                condition=~Q(divisi__isnull=False, departemen__isnull=False),
                name="wiki_folder_satu_jenis_unit",
            ),
        ]
        indexes = [models.Index(fields=["workspace", "parent"], name="wiki_folder_ws_parent_idx")]

    def __str__(self):
        return self.nama

    @property
    def unit(self):
        return self.divisi_id is not None or self.departemen_id is not None


class WikiMaterial(BaseModel):
    workspace = models.ForeignKey("db.Workspace", related_name="wiki_materi", on_delete=models.CASCADE)
    folder = models.ForeignKey(WikiFolder, related_name="materi", on_delete=models.CASCADE)
    # Id materi = id berkasnya (dibuat begitu oleh endpoint unggah dan migrasi),
    # jadi tautan lama /wiki/materi/<asset_id> tetap hidup.
    berkas = models.OneToOneField("db.FileAsset", related_name="wiki_materi", on_delete=models.CASCADE)
    # Judul tampilan, terpisah dari nama berkas asli yang dipakai saat diunduh.
    judul = models.CharField(max_length=255, blank=True, default="")
    pratinjau = models.ForeignKey("db.FileAsset", related_name="+", null=True, blank=True, on_delete=models.SET_NULL)
    # Teks isi berkas untuk pencarian (PDF, Word, Excel, teks, CSV). Diisi tugas
    # latar `indeks_materi` sesudah unggah; kosong = belum atau tidak bisa dibaca.
    # Dipotong di `plane.utils.wiki_isi.TEKS_INDEKS_MAKS`.
    isi_teks = models.TextField(blank=True, default="")
    diindeks_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "wiki_material"
        verbose_name = "Wiki material"
        verbose_name_plural = "Wiki materials"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["workspace", "folder"], name="wiki_material_ws_folder_idx"),
            # Pencarian mirip (pg_trgm) pada judul dan isi. Operator `<%` memakainya.
            GinIndex(fields=["judul"], opclasses=["gin_trgm_ops"], name="wiki_material_judul_trgm"),
            GinIndex(fields=["isi_teks"], opclasses=["gin_trgm_ops"], name="wiki_material_isi_trgm"),
        ]

    def __str__(self):
        return self.judul or str(self.berkas_id)
