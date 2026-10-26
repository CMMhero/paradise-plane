# Kustomisasi Paradise Task Tracker: simpan status sebelum diajukan selesai.
# Tugas tetap berstatus selesai selagi menunggu persetujuan; kalau ditolak,
# dikembalikan ke status ini. Dibuat manual mengikuti gaya migrasi repo.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0147_ringkasan_harian_opt_in'),
    ]

    operations = [
        migrations.AddField(
            model_name='persetujuanpenugasan',
            name='state_sebelumnya',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='db.state',
            ),
        ),
    ]
