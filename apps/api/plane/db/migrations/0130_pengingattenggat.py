# Kustomisasi Paradise Task Tracker: pengingat tenggat

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0129_superadminterlihatdiproject'),
    ]

    operations = [
        migrations.CreateModel(
            name='PengingatTenggat',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('titik', models.IntegerField()),
                ('tenggat', models.DateField()),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deadline_reminders', to='db.issue')),
                ('penerima', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deadline_reminders', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deadline_reminders', to='db.project')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deadline_reminders', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Pengingat Tenggat',
                'verbose_name_plural': 'Pengingat Tenggat',
                'db_table': 'deadline_reminders',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='pengingattenggat',
            index=models.Index(fields=['issue', 'penerima'], name='deadline_re_issue_i_8f3a21_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='pengingattenggat',
            unique_together={('issue', 'penerima', 'titik', 'tenggat', 'deleted_at')},
        ),
    ]
