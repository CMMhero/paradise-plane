from django.db import migrations, models

# Nilai bawaan yang pernah dipakai, (property_change, state_change, comment, mention,
# issue_completed, approval, daily_digest). Baris yang PERSIS salah satunya = belum
# pernah disentuh orangnya, jadi boleh ikut bawaan jabatan. Sisanya pilihan manusia.
_BAWAAN_LAMA = {
    (True, True, True, True, True, True, False),  # bawaan asli Plane
    (False, False, False, False, True, True, False),  # 0149 / signal pembuatan user
}
_KOLOM = ("property_change", "state_change", "comment", "mention", "issue_completed", "approval", "daily_digest")


def _maju(apps, schema_editor):
    Pref = apps.get_model("db", "UserNotificationPreference")
    for pref in Pref.objects.all().only("id", "user_id", *_KOLOM):
        if tuple(getattr(pref, k) for k in _KOLOM) in _BAWAAN_LAMA:
            continue  # kolom baru sudah ikut_bawaan_jabatan=True
        # Pilihan manusia dibiarkan. Pengingat per tugas dulu dikirim ke semua orang;
        # yang belum menyalakan ringkasan harian tetap mendapatkannya supaya tidak
        # ada yang kehilangan kabar tenggat, yang sudah menyalakan tidak dobel.
        Pref.objects.filter(pk=pref.pk).update(
            ikut_bawaan_jabatan=False,
            deadline_reminder=not pref.daily_digest,
        )


class Migration(migrations.Migration):
    """Email bawaan menurut jabatan + saklar pengingat tenggat per orang.

    Lihat plane/utils/preferensi_email.py. Baris yang sudah diubah orangnya tetap
    memakai pilihannya.
    """

    dependencies = [("db", "0149_notifikasi_bawaan_senyap")]

    operations = [
        migrations.AddField(
            model_name="usernotificationpreference",
            name="deadline_reminder",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="usernotificationpreference",
            name="ikut_bawaan_jabatan",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(_maju, migrations.RunPython.noop),
    ]
