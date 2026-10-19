# Kustomisasi Paradise Task Tracker: pesan langsung antar-karyawan

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0132_buang_akun_email'),
    ]

    operations = [
        migrations.CreateModel(
            name='PesanLangsung',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('isi', models.TextField()),
                ('dibaca_pada', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('pengirim', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pesan_terkirim', to=settings.AUTH_USER_MODEL)),
                ('penerima', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pesan_diterima', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pesan_langsung', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Pesan Langsung',
                'verbose_name_plural': 'Pesan Langsung',
                'db_table': 'direct_messages',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='pesanlangsung',
            index=models.Index(fields=['workspace', 'pengirim', 'penerima'], name='dm_ws_pengirim_penerima_idx'),
        ),
        migrations.AddIndex(
            model_name='pesanlangsung',
            index=models.Index(fields=['penerima', 'dibaca_pada'], name='dm_penerima_dibaca_idx'),
        ),
    ]
