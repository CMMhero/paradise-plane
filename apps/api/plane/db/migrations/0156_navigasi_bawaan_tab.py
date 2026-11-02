"""Navigasi bawaan: project bertab, semua project tampil, semua menu tersemat.

Bawaan kolom berubah supaya baris baru lahir dengan navigasi bertab dan tanpa
batas jumlah project di sidebar. Baris lama ikut disamakan: saklar "Show limited
projects" sebelumnya tidak bisa dimatikan, jadi nilai 10 yang tersimpan bukan
pilihan siapa pun. Semua item sidebar juga disematkan; menu khusus admin
(Analytics, Views, Archives, ...) tetap disaring izin di web, jadi member biasa
tidak melihatnya.

Mundur hanya mengembalikan bawaan kolom; nilai per orang sebelum migrasi tidak
disimpan.
"""

from django.db import migrations, models

# Cermin NAV_KUNCI di plane/utils/bawaan_member.py.
_NAV_KUNCI = (
    "your_work",
    "stickies",
    "drafts",
    "quick_links",
    "views",
    "analytics",
    "dashboard_divisi",
    "initiatives",
    "chat",
    "wiki",
    "archives",
)


def _samakan(apps, schema_editor):
    WorkspaceUserProperties = apps.get_model("db", "WorkspaceUserProperties")
    WorkspaceUserPreference = apps.get_model("db", "WorkspaceUserPreference")
    WorkspaceUserProperties._base_manager.update(navigation_project_limit=0, navigation_control_preference="TABBED")
    WorkspaceUserPreference._base_manager.filter(key__in=_NAV_KUNCI).update(is_pinned=True)


class Migration(migrations.Migration):
    dependencies = [("db", "0155_notifikasi_granular")]

    operations = [
        migrations.AlterField(
            model_name="workspaceuserproperties",
            name="navigation_project_limit",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="workspaceuserproperties",
            name="navigation_control_preference",
            field=models.CharField(
                choices=[("ACCORDION", "Accordion"), ("TABBED", "Tabbed")], default="TABBED", max_length=25
            ),
        ),
        migrations.RunPython(_samakan, migrations.RunPython.noop),
    ]
