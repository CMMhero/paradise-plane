"""Log persetujuan untuk pengajuan yang lahir sebelum KEP-55.

Sejak KEP-55 tiap pengajuan dan keputusan menulis `IssueActivity` dengan
`field="approval"` (`catat_aktivitas_persetujuan`). Baris `persetujuan_penugasan`
yang lebih tua tidak punya log itu, jadi riwayat aktivitas tugasnya kosong.
Migrasi ini menuliskannya, dengan waktu yang sama dengan barisnya: "requested"
pada `created_at` (oleh pemohon), keputusan pada `diputuskan_pada` (oleh
pemutus), alasan tolak di `new_value`.

Idempoten: tiap log menyimpan id baris persetujuannya di `new_identifier`, dan
pasangan (baris, verb) yang sudah ada dilewati. Mundur menghapus log yang
ditulis di sini saja (`comment` berawalan "approval backfill").
"""

from django.db import migrations

_KOMENTAR = "approval backfill"


def _tulis(apps, schema_editor):
    Persetujuan = apps.get_model("db", "PersetujuanPenugasan")
    IssueActivity = apps.get_model("db", "IssueActivity")

    sudah = set(
        IssueActivity.objects.filter(field="approval", new_identifier__isnull=False).values_list(
            "new_identifier", "verb"
        )
    )
    for baris in Persetujuan.objects.filter(deleted_at__isnull=True, issue__isnull=False).iterator():
        rencana = [("requested", baris.pemohon_id, baris.created_at, None)]
        if baris.status in ("disetujui", "ditolak") and baris.diputuskan_pada:
            verb = "approved" if baris.status == "disetujui" else "rejected"
            rencana.append((verb, baris.diputuskan_oleh_id, baris.diputuskan_pada, baris.alasan or None))
        for verb, aktor_id, waktu, alasan in rencana:
            if (baris.id, verb) in sudah:
                continue
            log = IssueActivity.objects.create(
                workspace_id=baris.workspace_id,
                project_id=baris.project_id,
                issue_id=baris.issue_id,
                actor_id=aktor_id,
                created_by_id=aktor_id,
                verb=verb,
                field="approval",
                new_value=alasan,
                new_identifier=baris.id,
                comment=f"{_KOMENTAR} {verb}",
                epoch=waktu.timestamp(),
            )
            # `created_at` diisi auto_now_add saat insert, jadi dimundurkan sesudahnya.
            IssueActivity.objects.filter(pk=log.pk).update(created_at=waktu, updated_at=waktu)


def _hapus(apps, schema_editor):
    IssueActivity = apps.get_model("db", "IssueActivity")
    IssueActivity.objects.filter(field="approval", comment__startswith=_KOMENTAR).delete()


class Migration(migrations.Migration):
    dependencies = [("db", "0156_navigasi_bawaan_tab")]

    operations = [migrations.RunPython(_tulis, _hapus)]
