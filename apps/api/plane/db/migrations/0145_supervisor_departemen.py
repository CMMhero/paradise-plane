# Kustomisasi Paradise Task Tracker: supervisor boleh memegang beberapa departemen.
# Dibuat manual mengikuti gaya migrasi repo (tanpa makemigrations di CI).
#
# KEP-32: satu supervisor boleh mengawasi beberapa departemen (mis. Fran Olnsen
# membawahi IT-SAP sekaligus IT-AI). Penempatan utama tetap di
# `JabatanOrganisasi.departemen`; tabel ini menambah jangkauan, bukan memindahkan.
# Cerminan pola `AksesHierarki`/`PengawasanDivisi`: tabel pemetaan, bukan kolom di
# model upstream, supaya upstream sync tidak membayar konflik di tiap rilis.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0144_zona_waktu_jakarta'),
    ]

    operations = [
        migrations.CreateModel(
            name='SupervisorDepartemen',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('departemen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='supervisor_tambahan', to='db.departemen')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='supervisor_departemen', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='supervisor_departemen', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Supervisor Departemen',
                'verbose_name_plural': 'Supervisor Departemen',
                'db_table': 'organisasi_supervisor_departemen',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddConstraint(
            model_name='supervisordepartemen',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('member', 'departemen'), name='supervisor_dep_unique_aktif'),
        ),
        migrations.AlterUniqueTogether(
            name='supervisordepartemen',
            unique_together={('member', 'departemen', 'deleted_at')},
        ),
        migrations.AddIndex(
            model_name='supervisordepartemen',
            index=models.Index(fields=['workspace', 'member'], name='supdep_ws_member_idx'),
        ),
    ]
