# Kustomisasi Paradise Task Tracker: persetujuan penugasan
#
# Reversible: ya (`CreateModel` + `AddConstraint` punya kebalikannya).
# Tabelnya LAHIR KOSONG, jadi tidak ada perilaku 88 user yang berubah; baris hanya lahir
# kalau katup `HIERARKI_GERBANG_TUGAS` dinyalakan DAN yang menugaskan seorang member
# (lihat plane/utils/hierarki.py).
#
# CATATAN: dijalankan di stack uji dari worktree, BUKAN ke DB lokal yang dipakai bersama
# agen lain lewat bind-mount (jebakan RISK-06).

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0139_hierarki'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersetujuanPenugasan',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('status', models.CharField(choices=[('menunggu', 'Menunggu'), ('disetujui', 'Disetujui'), ('ditolak', 'Ditolak')], default='menunggu', max_length=20)),
                ('diputuskan_pada', models.DateTimeField(blank=True, null=True)),
                ('alasan', models.TextField(blank=True, default='')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('diputuskan_oleh', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='persetujuan_penugasan_diputuskan', to=settings.AUTH_USER_MODEL)),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='persetujuan_penugasan', to='db.issue')),
                ('pemohon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='persetujuan_penugasan_diminta', to=settings.AUTH_USER_MODEL)),
                ('penerima', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='persetujuan_penugasan_diterima', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='persetujuan_penugasan', to='db.project')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='persetujuan_penugasan', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Persetujuan Penugasan',
                'verbose_name_plural': 'Persetujuan Penugasan',
                'db_table': 'persetujuan_penugasan',
                'ordering': ('-created_at',),
                'indexes': [models.Index(fields=['project', 'status', 'created_at'], name='persetujuan_proyek_status_idx'), models.Index(fields=['pemohon', 'status'], name='persetujuan_pemohon_idx')],
            },
        ),
        migrations.AddConstraint(
            model_name='persetujuanpenugasan',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True), ('status', 'menunggu')), fields=('issue',), name='persetujuan_satu_menunggu_per_tugas'),
        ),
    ]
