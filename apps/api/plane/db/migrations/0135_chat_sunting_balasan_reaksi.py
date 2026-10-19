# Kustomisasi Paradise Task Tracker: sunting, balas, dan reaksi pesan

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0134_pesanlangsung_dinotifikasi_pada'),
    ]

    operations = [
        migrations.AddField(
            model_name='pesanlangsung',
            name='disunting_pada',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pesanlangsung',
            name='balasan_ke',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='balasan', to='db.pesanlangsung'),
        ),
        migrations.CreateModel(
            name='ReaksiPesan',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('emoji', models.CharField(max_length=32)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('pesan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reaksi', to='db.pesanlangsung')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reaksi_pesan', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Reaksi Pesan',
                'verbose_name_plural': 'Reaksi Pesan',
                'db_table': 'direct_message_reactions',
                'ordering': ('created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='reaksipesan',
            index=models.Index(fields=['pesan'], name='dm_reaksi_pesan_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='reaksipesan',
            unique_together={('pesan', 'user', 'emoji', 'deleted_at')},
        ),
    ]
