# Kustomisasi Paradise Task Tracker: saklar ringkasan tugas harian per pengguna.
# Dibuat manual mengikuti gaya migrasi repo (tanpa makemigrations di CI).
# Default False (opt-in): tidak ada yang menerima email ini sebelum menyalakannya
# sendiri dari Profil -> Notifikasi.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0146_supervisor_multi_departemen'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotificationpreference',
            name='daily_digest',
            field=models.BooleanField(default=False),
        ),
    ]
