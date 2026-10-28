from django.db import migrations, models


def _alter(name):
    return migrations.AlterField(
        model_name="usernotificationpreference",
        name=name,
        field=models.BooleanField(default=False),
    )


class Migration(migrations.Migration):
    """Email notifikasi mati secara bawaan, kecuali disetujui & selesai.

    Hanya mengubah bawaan baris BARU; preferensi yang sudah ada tidak disentuh.
    """

    dependencies = [("db", "0148_persetujuan_state_sebelumnya")]

    operations = [_alter(n) for n in ("property_change", "state_change", "comment", "mention")]
