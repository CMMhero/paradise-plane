from django.db import migrations, models

# Supervisor ke atas, dibekukan di sini (migrasi tidak boleh mengimpor kode hidup).
_TINGKAT_SUPERVISOR = 20


def _maju(apps, schema_editor):
    """Baris yang sudah dibekukan (pilihan manusia) milik pimpinan: saklar baru mati.

    Kolom lahir True supaya staf yang pernah mengubah saklar tetap menerima kabar
    penugasan. Pimpinan yang membekukan pilihannya tidak boleh mendadak menerima
    email jenis baru yang bawaan pimpinannya mati. Baris yang masih ikut bawaan
    jabatan tidak tersentuh: kunci yang hilang dari potretnya jatuh ke tabel God Mode.
    """
    Pref = apps.get_model("db", "UserNotificationPreference")
    Jabatan = apps.get_model("db", "JabatanOrganisasi")
    pimpinan = Jabatan.objects.filter(tingkat__gte=_TINGKAT_SUPERVISOR, deleted_at__isnull=True).values("member_id")
    Pref.objects.filter(ikut_bawaan_jabatan=False, user_id__in=pimpinan).update(assigned=False)


class Migration(migrations.Migration):
    """Saklar email "tugas baru untuk Anda" (bgtasks/penugasan_email.py)."""

    dependencies = [("db", "0152_akun_terhapus")]

    operations = [
        migrations.AddField(
            model_name="usernotificationpreference",
            name="assigned",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(_maju, migrations.RunPython.noop),
    ]
