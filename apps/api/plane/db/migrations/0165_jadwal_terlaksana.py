# Paradise KEP-83: penanda jadwal kantor (plane/bgtasks/jadwal_kantor.py).
#
# Hanya CreateModel. `makemigrations` juga mengusulkan AlterField user_timezone
# (daftar zona pytz di mesin pembuat berbeda); itu bukan bagian perubahan ini.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0164_quick_link_bersama"),
    ]

    operations = [
        migrations.CreateModel(
            name="JadwalTerlaksana",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slot", models.CharField(max_length=64)),
                ("tanggal", models.DateField()),
                ("diklaim_at", models.DateTimeField(auto_now_add=True)),
                ("selesai_at", models.DateTimeField(blank=True, null=True)),
                ("hasil", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "Jadwal Terlaksana",
                "verbose_name_plural": "Jadwal Terlaksana",
                "db_table": "office_schedule_runs",
                "ordering": ("-tanggal", "slot"),
            },
        ),
        migrations.AddConstraint(
            model_name="jadwalterlaksana",
            constraint=models.UniqueConstraint(fields=("slot", "tanggal"), name="jadwal_terlaksana_slot_tanggal_unik"),
        ),
    ]
