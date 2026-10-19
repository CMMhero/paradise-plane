# Kustomisasi Paradise Task Tracker: hierarki jabatan + pengawasan divisi
#
# Reversible: ya. `CreateModel` / `AddConstraint` / `AlterUniqueTogether` semuanya
# punya kebalikannya yang dihasilkan otomatis, jadi `migrate db 0138` mengembalikan
# skema persis seperti sebelumnya tanpa menyentuh tabel lain.
#
# Aman dinyalakan pada data nyata: kedua tabel LAHIR KOSONG, jadi tidak ada satu pun
# perilaku 88 user yang berubah. Perilaku baru hanya muncul kalau tabelnya diisi DAN
# `HIERARKI_GERBANG_TUGAS` disetel (lihat plane/utils/hierarki.py).
#
# CATATAN: migrasi ini dijalankan di stack uji dari worktree, BUKAN ke DB lokal yang
# dipakai bersama agen lain lewat bind-mount (jebakan RISK-06).

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0138_permintaanlintasdivisi'),
    ]

    operations = [
        migrations.CreateModel(
            name='JabatanOrganisasi',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('tingkat', models.PositiveSmallIntegerField(choices=[(10, 'Member'), (20, 'Supervisor'), (30, 'Manager'), (40, 'Direktur')])),
                ('sumber', models.CharField(default='manual', max_length=64)),
                ('catatan', models.TextField(blank=True, default='')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jabatan_organisasi', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jabatan_organisasi', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Jabatan Organisasi',
                'verbose_name_plural': 'Jabatan Organisasi',
                'db_table': 'jabatan_organisasi',
                'ordering': ('-tingkat', 'created_at'),
            },
        ),
        migrations.CreateModel(
            name='PengawasanDivisi',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('catatan', models.TextField(blank=True, default='')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pengawasan_divisi', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pengawasan_divisi', to='db.project')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pengawasan_divisi', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Pengawasan Divisi',
                'verbose_name_plural': 'Pengawasan Divisi',
                'db_table': 'pengawasan_divisi',
                'ordering': ('-created_at',),
                'indexes': [models.Index(fields=['workspace', 'member'], name='pengawasan_ws_member_idx')],
            },
        ),
        migrations.AddConstraint(
            model_name='pengawasandivisi',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('project', 'member'), name='pengawasan_divisi_unique_aktif'),
        ),
        migrations.AlterUniqueTogether(
            name='pengawasandivisi',
            unique_together={('project', 'member', 'deleted_at')},
        ),
        migrations.AddConstraint(
            model_name='jabatanorganisasi',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('workspace', 'member'), name='jabatan_organisasi_unique_aktif'),
        ),
        migrations.AlterUniqueTogether(
            name='jabatanorganisasi',
            unique_together={('workspace', 'member', 'deleted_at')},
        ),
    ]
