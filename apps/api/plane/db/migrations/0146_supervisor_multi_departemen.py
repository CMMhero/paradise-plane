# Kustomisasi Paradise Task Tracker: supervisor multi-departemen sebagai baris jabatan.
# Dibuat manual mengikuti gaya migrasi repo (tanpa makemigrations di CI).
#
# Keputusan user 2026-10-23: "supervisor tambahan" DIHAPUS sebagai konsep. Sebagai
# gantinya supervisor boleh DITEMPATKAN di lebih dari satu departemen -- Fran
# Olnsen spv IT-AI sekaligus spv IT-SAP, dua baris `JabatanOrganisasi`, bukan
# satu baris utama + satu baris tambahan. Efeknya sama di jangkauan (union semua
# departemennya), tapi datanya jujur: tidak ada lagi "utama" vs "tambahan".
#
# Sekaligus: SATU departemen tepat SATU project, ditegakkan di database
# (`departemen_project_unique_departemen_aktif`). Sebelumnya hanya validasi di
# satu endpoint (PATCH departemen menolak >1), sementara 4 jalur create lain
# bisa menumpuk dua project di satu departemen tanpa error.
#
# Urutan operasi penting: salin baris tambahan -> baris jabatan DULU (butuh kedua
# tabel), baru hapus model SupervisorDepartemen. Rollback menghapus baris salinan
# (penanda sumber="migrasi-0146").

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def salin_tambahan_ke_jabatan(apps, schema_editor):
    SupervisorDepartemen = apps.get_model("db", "SupervisorDepartemen")
    JabatanOrganisasi = apps.get_model("db", "JabatanOrganisasi")
    for tambahan in SupervisorDepartemen.objects.filter(deleted_at__isnull=True):
        ws_id, uid, dep_id = (
            tambahan.workspace_id,
            tambahan.member_id,
            tambahan.departemen_id,
        )
        sudah = JabatanOrganisasi.objects.filter(
            workspace_id=ws_id, member_id=uid, departemen_id=dep_id, deleted_at__isnull=True
        ).first()
        if sudah is not None:
            continue
        baris = JabatanOrganisasi.objects.filter(
            workspace_id=ws_id, member_id=uid, deleted_at__isnull=True
        ).first()
        tingkat = baris.tingkat if baris is not None else 20
        JabatanOrganisasi.objects.create(
            workspace_id=ws_id,
            member_id=uid,
            tingkat=tingkat,
            departemen_id=dep_id,
            divisi_id=None,
            sumber="migrasi-0146",
            catatan="Penempatan multi-departemen, pindahan SupervisorDepartemen 2026-10-23",
        )


def buang_salinan(apps, schema_editor):
    JabatanOrganisasi = apps.get_model("db", "JabatanOrganisasi")
    JabatanOrganisasi.objects.filter(sumber="migrasi-0146").delete()


def bersihkan_pemetaan_arsip(apps, schema_editor):
    DepartemenProject = apps.get_model("db", "DepartemenProject")
    Project = apps.get_model("db", "Project")
    mati = Project.objects.filter(deleted_at__isnull=False) | Project.objects.filter(
        archived_at__isnull=False
    )
    DepartemenProject.objects.filter(
        deleted_at__isnull=True, project__in=mati
    ).update(deleted_at=django.utils.timezone.now())


def biarkan_apa_adanya(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0145_supervisor_departemen'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='jabatanorganisasi',
            unique_together={('workspace', 'member', 'departemen', 'divisi', 'deleted_at')},
        ),
        migrations.RemoveConstraint(
            model_name='jabatanorganisasi',
            name='jabatan_organisasi_unique_aktif',
        ),
        migrations.AddConstraint(
            model_name='jabatanorganisasi',
            constraint=models.UniqueConstraint(
                fields=['workspace', 'member', 'departemen'],
                condition=models.Q(deleted_at__isnull=True),
                name='jabatan_organisasi_unique_dept_aktif',
            ),
        ),
        migrations.AddConstraint(
            model_name='jabatanorganisasi',
            constraint=models.UniqueConstraint(
                fields=['workspace', 'member', 'divisi'],
                condition=models.Q(deleted_at__isnull=True),
                name='jabatan_organisasi_unique_divisi_aktif',
            ),
        ),
        migrations.AddConstraint(
            model_name='jabatanorganisasi',
            constraint=models.UniqueConstraint(
                fields=['workspace', 'member'],
                condition=models.Q(deleted_at__isnull=True)
                & models.Q(departemen__isnull=True)
                & models.Q(divisi__isnull=True),
                name='jabatan_organisasi_unique_tanpa_tempat_aktif',
            ),
        ),
        migrations.RunPython(salin_tambahan_ke_jabatan, buang_salinan),
        migrations.DeleteModel(
            name='SupervisorDepartemen',
        ),
        # Payung arsip E1 pemetaannya masih aktif -> bersihkan dulu, kalau tidak
        # constraint 1:1 di bawah gagal (departemen terhitung memegang dua project).
        migrations.RunPython(bersihkan_pemetaan_arsip, biarkan_apa_adanya),
        migrations.AddConstraint(
            model_name='departemenproject',
            constraint=models.UniqueConstraint(
                fields=['departemen'],
                condition=models.Q(deleted_at__isnull=True),
                name='departemen_project_unique_departemen_aktif',
            ),
        ),
    ]
