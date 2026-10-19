# Kustomisasi Paradise Task Tracker: permintaan tugas lintas divisi
#
# Reversible: ya. `CreateModel` + `AddIndex` punya kebalikannya (DeleteModel /
# RemoveIndex) yang dihasilkan otomatis, jadi `migrate db 0137` mengembalikan
# skema persis seperti sebelumnya tanpa kehilangan tabel lain.
#
# CATATAN: migrasi ini BELUM dijalankan ke DB lokal (dipakai bersama agen lain
# lewat bind-mount, jebakan RISK-06). Bukti jalan diambil di stack uji.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0137_workspaceplan'),
    ]

    operations = [
        migrations.CreateModel(
            name='PermintaanLintasDivisi',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('catatan', models.TextField(blank=True, default='')),
                ('asal_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permintaan_lintas_divisi_asal', to='db.project')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('diminta_oleh', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permintaan_lintas_divisi_dibuat', to=settings.AUTH_USER_MODEL)),
                ('intake_issue', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='permintaan_lintas_divisi', to='db.intakeissue')),
                ('tujuan_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permintaan_lintas_divisi_tujuan', to='db.project')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permintaan_lintas_divisi', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Permintaan Lintas Divisi',
                'verbose_name_plural': 'Permintaan Lintas Divisi',
                'db_table': 'permintaan_lintas_divisi',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='permintaanlintasdivisi',
            index=models.Index(fields=['workspace', 'asal_project', 'created_at'], name='pld_ws_asal_idx'),
        ),
        migrations.AddIndex(
            model_name='permintaanlintasdivisi',
            index=models.Index(fields=['workspace', 'tujuan_project', 'created_at'], name='pld_ws_tujuan_idx'),
        ),
        migrations.AddIndex(
            model_name='permintaanlintasdivisi',
            index=models.Index(fields=['diminta_oleh', 'created_at'], name='pld_peminta_idx'),
        ),
    ]
