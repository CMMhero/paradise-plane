"""Menu KPI (`kinerja`) lahir tersemat tepat di bawah Dashboard Divisi.

Baris preferensi dibuat malas saat sidebar dimuat, dan kunci baru jatuh ke ujung
urutan. Di sini barisnya dibuat untuk semua orang yang sudah punya baris
Dashboard Divisi, dengan urutan tepat sesudahnya, supaya KPI muncul di tempat
yang sama untuk akun lama dan akun baru.

Mundur menghapus baris `kinerja`.
"""

from django.db import migrations


def _tambah(apps, schema_editor):
    WorkspaceUserPreference = apps.get_model("db", "WorkspaceUserPreference")
    aktif = WorkspaceUserPreference._base_manager.filter(deleted_at__isnull=True)
    sudah = set(aktif.filter(key="kinerja").values_list("workspace_id", "user_id"))
    baru = [
        WorkspaceUserPreference(
            workspace_id=workspace_id, user_id=user_id, key="kinerja", is_pinned=True, sort_order=urutan + 1
        )
        for workspace_id, user_id, urutan in aktif.filter(key="dashboard_divisi").values_list(
            "workspace_id", "user_id", "sort_order"
        )
        if (workspace_id, user_id) not in sudah
    ]
    WorkspaceUserPreference._base_manager.bulk_create(baru, batch_size=500, ignore_conflicts=True)


def _hapus(apps, schema_editor):
    apps.get_model("db", "WorkspaceUserPreference")._base_manager.filter(key="kinerja").delete()


class Migration(migrations.Migration):
    dependencies = [("db", "0176_project_network_privat")]

    operations = [migrations.RunPython(_tambah, _hapus)]
