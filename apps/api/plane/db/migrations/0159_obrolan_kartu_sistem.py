# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kanal sistem + kartu obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kanal sistem (Announcements, Changelog) dan pesan kartu (3 Nov 2026).

* `Ruang.sistem` + `Ruang.kunci_sistem` (unik per workspace selama belum dihapus).
* `PesanLangsung.jenis` + `muatan`: kartu yang dirender peramban.
* `PesanLangsung.pengirim` boleh kosong: pesan dari sistem ("Paradise").
* Data: dua kanal sistem untuk setiap workspace, dan seluruh anggota aktif yang
  layak (bukan bot, bukan akun nonaktif atau terhapus, KEP-50) berlangganan.
  Langganan baru lahir sudah terbaca, supaya tidak menyala merah di hari deploy.

Urutan operasi ditulis tangan: AddField SEBELUM AddConstraint yang memakainya
(jebakan urutan AddIndex di 0136).
"""

from django.db import migrations, models
from django.db.models import deletion
from django.utils import timezone

KANAL = (
    ("pengumuman", "Announcements", "Company announcements from admins."),
    ("changelog", "Changelog", "What changed in each Paradise release."),
)


def _isi_kanal_sistem(apps, schema_editor):
    Workspace = apps.get_model("db", "Workspace")
    WorkspaceMember = apps.get_model("db", "WorkspaceMember")
    Ruang = apps.get_model("db", "Ruang")
    Langganan = apps.get_model("db", "Langganan")

    sekarang = timezone.now()
    for ws_id in Workspace.objects.filter(deleted_at__isnull=True).values_list("id", flat=True):
        ruang_ids = []
        for kunci, nama, topik in KANAL:
            ruang = Ruang.objects.filter(workspace_id=ws_id, kunci_sistem=kunci, deleted_at__isnull=True).first()
            if ruang is None:
                ruang = Ruang.objects.create(
                    workspace_id=ws_id, tipe="kanal", nama=nama, topik=topik, sistem=True, kunci_sistem=kunci
                )
            ruang_ids.append(ruang.id)

        orang = set(
            WorkspaceMember.objects.filter(
                workspace_id=ws_id,
                is_active=True,
                deleted_at__isnull=True,
                member__is_active=True,
                member__is_bot=False,
            )
            .exclude(member__email__endswith="@deleted.local")
            .values_list("member_id", flat=True)
        )
        sudah = set(
            Langganan.objects.filter(ruang_id__in=ruang_ids, deleted_at__isnull=True).values_list("ruang_id", "user_id")
        )
        Langganan.objects.bulk_create(
            [
                Langganan(ruang_id=rid, user_id=uid, dibaca_sampai=sekarang)
                for rid in ruang_ids
                for uid in orang
                if (rid, uid) not in sudah
            ],
            batch_size=500,
        )


def _buang_kanal_sistem(apps, schema_editor):
    Ruang = apps.get_model("db", "Ruang")
    PesanLangsung = apps.get_model("db", "PesanLangsung")
    # Pesan sistem tanpa pengirim tidak bisa bertahan saat kolomnya kembali NOT NULL.
    PesanLangsung.objects.filter(pengirim__isnull=True).delete()
    Ruang.objects.filter(sistem=True).delete()
    # Postgres menunda pemeriksaan kunci asing sampai akhir transaksi; tanpa ini
    # AlterField berikutnya gagal "pending trigger events" (jebakan 0136).
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class Migration(migrations.Migration):
    dependencies = [("db", "0158_ringkasan_sore")]

    operations = [
        migrations.AddField(
            model_name="ruang",
            name="sistem",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="ruang",
            name="kunci_sistem",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddConstraint(
            model_name="ruang",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), ("kunci_sistem__isnull", False)),
                fields=("workspace", "kunci_sistem"),
                name="ruang_ws_kunci_sistem_unik",
            ),
        ),
        migrations.AddField(
            model_name="pesanlangsung",
            name="jenis",
            field=models.CharField(
                choices=[
                    ("teks", "Teks"),
                    ("panggilan", "Log panggilan"),
                    ("changelog", "Catatan rilis"),
                    ("tugas", "Ditugaskan"),
                    ("project", "Ditambahkan ke project"),
                    ("persetujuan", "Persetujuan"),
                    ("mention", "Disebut"),
                    ("komentar", "Komentar"),
                    ("pembaruan", "Pembaruan work item"),
                ],
                default="teks",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="pesanlangsung",
            name="muatan",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="pesanlangsung",
            name="pengirim",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=deletion.CASCADE,
                related_name="pesan_terkirim",
                to="db.user",
            ),
        ),
        migrations.RunPython(_isi_kanal_sistem, _buang_kanal_sistem),
    ]
