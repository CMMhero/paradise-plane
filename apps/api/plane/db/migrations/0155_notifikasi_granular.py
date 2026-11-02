from django.db import migrations, models

# Kolom baru lahir True: itu perilaku sebelum saklarnya ada (inbox selalu ditulis,
# email obrolan hanya diatur saklar instance, ringkasan memuat semua bagian).
# Baris yang masih ikut bawaan jabatan tidak tersentuh: kunci yang hilang dari
# potret `bawaan_email`-nya jatuh ke tabel God Mode hari ini.
_KOLOM = (
    "chat",
    "inbox_assigned",
    "inbox_mention",
    "inbox_comment",
    "inbox_approval",
    "inbox_deadline",
    "inbox_issue_completed",
    "inbox_state_change",
    "inbox_property_change",
    "inbox_chat",
    "digest_terlambat",
    "digest_hari_ini",
    "digest_depan",
    "digest_diberikan",
    "digest_tim",
)


class Migration(migrations.Migration):
    """Notifikasi granular: inbox per jenis kabar, email obrolan, dan bagian ringkasan harian."""

    dependencies = [("db", "0154_fitur_project_nyala")]

    operations = [
        migrations.AddField(
            model_name="usernotificationpreference",
            name=kolom,
            field=models.BooleanField(default=True),
        )
        for kolom in _KOLOM
    ]
