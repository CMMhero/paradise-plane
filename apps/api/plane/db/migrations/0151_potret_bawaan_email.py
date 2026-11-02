from django.db import migrations, models

# Tabel pabrik KEP-42 per 2026-10-30, dibekukan di sini (migrasi tidak boleh
# mengimpor kode hidup). Semua akun yang sudah ada lahir di bawah tabel ini,
# sebelum bawaan email bisa diatur dari God Mode.
_SAKLAR = (
    "property_change",
    "state_change",
    "comment",
    "mention",
    "issue_completed",
    "approval",
    "daily_digest",
    "deadline_reminder",
)
_PIMPINAN = {kunci: False for kunci in _SAKLAR} | {"daily_digest": True}
_STAF = {**_PIMPINAN, "issue_completed": True, "approval": True}


def _maju(apps, schema_editor):
    Pref = apps.get_model("db", "UserNotificationPreference")
    Pref.objects.filter(bawaan_email__isnull=True).update(bawaan_email={"staf": _STAF, "pimpinan": _PIMPINAN})


class Migration(migrations.Migration):
    """Potret tabel bawaan email per orang, supaya mengubah bawaan member baru di
    God Mode tidak ikut mengubah akun lama yang masih ikut bawaan jabatan.

    Lihat plane/utils/preferensi_email.py.
    """

    dependencies = [("db", "0150_email_bawaan_jabatan")]

    operations = [
        migrations.AddField(
            model_name="usernotificationpreference",
            name="bawaan_email",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.RunPython(_maju, migrations.RunPython.noop),
    ]
