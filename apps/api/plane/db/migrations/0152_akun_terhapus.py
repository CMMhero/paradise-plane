import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def _ganti_nama_lama(apps, schema_editor):
    """Akun yang digosok sebelum migrasi ini bernama "Akun dihapus".

    Diseragamkan ke placeholder baru supaya semua akun terhapus tampil sama.
    Akun lama ini tidak punya potret identitas, jadi tetap tak bisa dipulihkan.
    """
    User = apps.get_model("db", "User")
    User.objects.filter(email__endswith="@deleted.local").update(
        display_name="Deleted account", first_name="Deleted", last_name="account"
    )


class Migration(migrations.Migration):
    dependencies = [("db", "0151_potret_bawaan_email")]

    operations = [
        migrations.CreateModel(
            name="AkunTerhapus",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.CharField(max_length=255)),
                ("username", models.CharField(max_length=128)),
                ("display_name", models.CharField(blank=True, max_length=255)),
                ("first_name", models.CharField(blank=True, max_length=255)),
                ("last_name", models.CharField(blank=True, max_length=255)),
                ("was_super_admin", models.BooleanField(default=False)),
                ("workspace_member_ids", models.JSONField(default=list)),
                ("dihapus_pada", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    "dihapus_oleh",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="akun_terhapus",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Akun Terhapus",
                "verbose_name_plural": "Akun Terhapus",
                "db_table": "akun_terhapus",
                "ordering": ("-dihapus_pada",),
            },
        ),
        migrations.RunPython(_ganti_nama_lama, migrations.RunPython.noop),
    ]
