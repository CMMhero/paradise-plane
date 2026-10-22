# Kustomisasi Paradise Task Tracker: saklar email persetujuan per pengguna.
# Dibuat manual mengikuti gaya migrasi repo (tanpa makemigrations di CI).
# Default True: pengguna lama langsung mendapat email persetujuan; yang tidak
# mau mematikan dari Profil → Notifikasi.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0142_organisasi'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotificationpreference',
            name='approval',
            field=models.BooleanField(default=True),
        ),
    ]
