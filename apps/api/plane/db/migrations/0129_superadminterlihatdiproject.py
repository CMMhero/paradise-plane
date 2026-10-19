# Kustomisasi Paradise Task Tracker: pengecualian penyembunyian Super Admin

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0128_loginactivity'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuperAdminTerlihatDiProject',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='superadmin_visibility', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='superadmin_visibility', to='db.project')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='superadmin_visibility', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Super Admin Terlihat di Project',
                'verbose_name_plural': 'Super Admin Terlihat di Project',
                'db_table': 'superadmin_visibility',
                'ordering': ('-created_at',),
                'unique_together': {('project', 'member', 'deleted_at')},
            },
        ),
    ]
