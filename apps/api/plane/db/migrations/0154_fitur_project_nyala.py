"""KEP-53: semua fitur project menyala, termasuk project yang sudah ada.

Bawaan kolom berubah supaya project baru (termasuk yang dibuat otomatis dari
departemen) lahir dengan semua fitur menyala, lalu project lama ikut dinyalakan.
Project yang diarsip atau terhapus ikut, supaya memulihkannya tidak membawa
setelan lama yang sekarang tak lagi bisa diatur per project dengan wajar.

Cycles dan work item types dicabut, jadi `cycle_view` dan `is_issue_type_enabled`
tidak disentuh. Mundur hanya mengembalikan bawaan kolom: nilai per project
sebelum migrasi tidak disimpan, dan tak ada yang membutuhkannya kembali.
"""

from django.db import migrations, models

_FLAG = ("module_view", "issue_views_view", "page_view", "intake_view", "is_time_tracking_enabled")


def _nyalakan(apps, schema_editor):
    Project = apps.get_model("db", "Project")
    # `_base_manager` melewati manager bawaan yang menyaring project terhapus.
    Project._base_manager.update(**dict.fromkeys(_FLAG, True))


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0153_email_penugasan"),
    ]

    operations = [
        migrations.AlterField(model_name="project", name="module_view", field=models.BooleanField(default=True)),
        migrations.AlterField(model_name="project", name="issue_views_view", field=models.BooleanField(default=True)),
        migrations.AlterField(model_name="project", name="intake_view", field=models.BooleanField(default=True)),
        migrations.AlterField(
            model_name="project", name="is_time_tracking_enabled", field=models.BooleanField(default=True)
        ),
        migrations.RunPython(_nyalakan, migrations.RunPython.noop),
    ]
