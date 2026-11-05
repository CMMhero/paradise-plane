# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Wiki mandiri, pindah data (KEP-94)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Memindah Wiki dari project ber-identifier WIKI ke tabel wiki_folder /
# wiki_material, lalu memensiunkan project itu. Tidak ada berkas yang hilang:
#
# - Tiap halaman project WIKI jadi satu WikiFolder ber-id SAMA (tautan
#   /wiki/<id> tetap hidup). Folder teratas yang namanya = nama Divisi jadi
#   folder divisi itu; folder teratas lain jadi General (KEP-51: folder teratas
#   non-divisi = General). Keterangan halaman ikut; isi halaman yang lebih dari
#   sekadar satu kalimat disimpan hanya-baca di `isi_lama_html`.
# - Tiap FileAsset WIKI_MATERIAL jadi satu WikiMaterial ber-id SAMA dengan
#   berkasnya. Berkas lain yang menempel di halaman Wiki (sisipan editor dari
#   masa sebelum 21 Agt) ikut dijadikan materi, supaya tidak ikut terhapus
#   bersama project. Objek MinIO tidak disentuh: kuncinya tidak memuat id project.
# - Berkas dilepas dari project dan page (project=NULL, page=NULL), jadi saat
#   project WIKI dihapus permanen oleh tugas harian, berkasnya tidak ikut.
# - Tiap Divisi dan Departemen yang belum punya folder dibuatkan.
# - Project WIKI, keanggotaannya, halaman lamanya, dan baris ACL lamanya
#   di-soft-delete dengan SATU cap waktu yang sama. Mundur memakai cap itu untuk
#   memulihkan tepat baris yang dipensiunkan di sini, tidak lebih.

import datetime

from django.db import migrations
from django.utils import timezone

WIKI = "WIKI"
MATERI = "WIKI_MATERIAL"
PRATINJAU = "WIKI_MATERIAL_PREVIEW"
# Berkas halaman yang bukan isi Wiki dan tidak dipindah.
BUKAN_MATERI = {PRATINJAU, "PROJECT_COVER"}
# Isi halaman yang lebih dari sekadar keterangan pendek.
TANDA_ISI = ("<img", "<image-component", "<a ", "<table", "<ul", "<ol", "<h1", "<h2", "<h3", "<pre", "<blockquote")
KUNCI_ASAL = "_wiki_entity_type_asal"


def _isi_kaya(html, teks):
    html = html or ""
    return len(teks or "") > 300 or any(t in html for t in TANDA_ISI)


def _sebagai_waktu(tanggal):
    if tanggal is None or isinstance(tanggal, datetime.datetime):
        return tanggal
    return timezone.make_aware(datetime.datetime.combine(tanggal, datetime.time()))


def _pastikan_folder_unit(apps, workspace_id, kini):
    Divisi = apps.get_model("db", "Divisi")
    Departemen = apps.get_model("db", "Departemen")
    WikiFolder = apps.get_model("db", "WikiFolder")

    folder_divisi = {
        f.divisi_id: f
        for f in WikiFolder.objects.filter(workspace_id=workspace_id, divisi__isnull=False, deleted_at__isnull=True)
    }
    for divisi in Divisi.objects.filter(workspace_id=workspace_id, deleted_at__isnull=True):
        if divisi.id not in folder_divisi:
            folder_divisi[divisi.id] = WikiFolder.objects.create(
                workspace_id=workspace_id, nama=divisi.nama, divisi_id=divisi.id, created_at=kini
            )

    sudah = set(
        WikiFolder.objects.filter(
            workspace_id=workspace_id, departemen__isnull=False, deleted_at__isnull=True
        ).values_list("departemen_id", flat=True)
    )
    for dep in Departemen.objects.filter(workspace_id=workspace_id, deleted_at__isnull=True):
        if dep.id in sudah:
            continue
        induk = folder_divisi.get(dep.divisi_id)
        WikiFolder.objects.create(
            workspace_id=workspace_id,
            nama=dep.nama,
            departemen_id=dep.id,
            parent_id=induk.id if induk else None,
            created_at=kini,
        )


def _pindah_satu(apps, wiki, kini):
    Page = apps.get_model("db", "Page")
    ProjectPage = apps.get_model("db", "ProjectPage")
    FileAsset = apps.get_model("db", "FileAsset")
    Divisi = apps.get_model("db", "Divisi")
    WikiFolder = apps.get_model("db", "WikiFolder")
    WikiMaterial = apps.get_model("db", "WikiMaterial")

    ws = wiki.workspace_id
    page_ids = set(
        ProjectPage.objects.filter(project_id=wiki.id, deleted_at__isnull=True).values_list("page_id", flat=True)
    )
    # Manager historis migrasi = Manager biasa (tanpa saring soft-delete), jadi
    # halaman yang sudah di tempat sampah ikut dan tetap di tempat sampah.
    halaman = list(Page.objects.filter(id__in=page_ids))

    divisi_per_nama = {}
    for d in Divisi.objects.filter(workspace_id=ws, deleted_at__isnull=True).order_by("created_at"):
        divisi_per_nama.setdefault(d.nama.strip().casefold(), d.id)
    divisi_terpakai = set()

    folders = []
    for p in sorted(halaman, key=lambda h: (h.parent_id is not None, h.created_at)):
        teratas = p.parent_id is None or p.parent_id not in page_ids
        aktif = p.deleted_at is None and p.archived_at is None
        divisi_id = None
        if teratas and aktif:
            calon = divisi_per_nama.get((p.name or "").strip().casefold())
            if calon and calon not in divisi_terpakai:
                divisi_id = calon
                divisi_terpakai.add(calon)
        teks = (p.description_stripped or "").strip()
        kaya = _isi_kaya(p.description_html, teks)
        folders.append(
            WikiFolder(
                id=p.id,
                workspace_id=ws,
                parent_id=None if teratas else p.parent_id,
                nama=(p.name or "").strip() or "Untitled",
                keterangan="" if kaya else teks,
                isi_lama_html=p.description_html if kaya else "",
                logo_props=p.logo_props or {},
                urutan=p.sort_order or 65535,
                divisi_id=divisi_id,
                umum=teratas and divisi_id is None,
                archived_at=_sebagai_waktu(p.archived_at),
                created_by_id=p.owned_by_id or p.created_by_id,
                updated_by_id=p.updated_by_id,
                deleted_at=p.deleted_at,
            )
        )
    WikiFolder.objects.bulk_create(folders)
    # bulk_create tidak menghormati created_at dari objek (auto_now_add), jadi disetel ulang.
    for p in halaman:
        WikiFolder.objects.filter(id=p.id).update(created_at=p.created_at)

    # Materi: semua berkas yang menempel di halaman Wiki, kecuali turunan & sampul.
    berkas = FileAsset.objects.filter(page_id__in=page_ids).exclude(entity_type__in=BUKAN_MATERI)
    berkas_materi = FileAsset.objects.filter(project_id=wiki.id, entity_type=MATERI)
    tanpa_folder = None
    materi = []
    for a in (berkas | berkas_materi).distinct():
        if a.entity_type != MATERI and not a.is_uploaded:
            continue
        folder_id = a.page_id if a.page_id in page_ids else None
        if folder_id is None:
            if tanpa_folder is None:
                tanpa_folder = WikiFolder.objects.create(workspace_id=ws, nama="Unsorted materials", created_at=kini)
            folder_id = tanpa_folder.id
        atribut = dict(a.attributes or {})
        if a.entity_type != MATERI:
            atribut[KUNCI_ASAL] = a.entity_type
        atribut["_wiki_page_asal"] = str(a.page_id) if a.page_id else None
        judul = (atribut.get("title") or atribut.get("name") or "")[:255]
        materi.append(
            WikiMaterial(
                id=a.id,
                workspace_id=ws,
                folder_id=folder_id,
                berkas_id=a.id,
                judul=judul,
                created_by_id=a.created_by_id,
                updated_by_id=a.updated_by_id,
                deleted_at=a.deleted_at or (kini if a.is_deleted else None),
            )
        )
        FileAsset.objects.filter(id=a.id).update(
            entity_type=MATERI,
            attributes=atribut,
            project_id=None,
            page_id=None,
            entity_identifier=str(folder_id),
        )
    WikiMaterial.objects.bulk_create(materi)
    for a in materi:
        asal = FileAsset.objects.filter(id=a.berkas_id).values_list("created_at", flat=True).first()
        if asal:
            WikiMaterial.objects.filter(id=a.id).update(created_at=asal)

    # Pratinjau PDF: lepas dari project, tautkan ke materinya (yang terbaru).
    ids_materi = {str(m.id) for m in materi}
    for prev in FileAsset.objects.filter(entity_type=PRATINJAU, entity_identifier__in=ids_materi).order_by(
        "created_at"
    ):
        FileAsset.objects.filter(id=prev.id).update(project_id=None, page_id=None)
        WikiMaterial.objects.filter(id=prev.entity_identifier).update(pratinjau_id=prev.id)

    return page_ids


def _pensiunkan(apps, wiki, page_ids, kini):
    Project = apps.get_model("db", "Project")
    ProjectMember = apps.get_model("db", "ProjectMember")
    ProjectPage = apps.get_model("db", "ProjectPage")
    Page = apps.get_model("db", "Page")
    WikiFolderAccess = apps.get_model("db", "WikiFolderAccess")
    WikiGovernedProject = apps.get_model("db", "WikiGovernedProject")

    ProjectMember.objects.filter(project_id=wiki.id, deleted_at__isnull=True).update(deleted_at=kini)
    ProjectPage.objects.filter(project_id=wiki.id, deleted_at__isnull=True).update(deleted_at=kini)
    Page.objects.filter(id__in=page_ids, deleted_at__isnull=True).update(deleted_at=kini)
    WikiFolderAccess.objects.filter(project_id=wiki.id, deleted_at__isnull=True).update(deleted_at=kini)
    WikiGovernedProject.objects.filter(project_id=wiki.id, deleted_at__isnull=True).update(deleted_at=kini)
    Project.objects.filter(id=wiki.id).update(deleted_at=kini)


def maju(apps, schema_editor):
    Project = apps.get_model("db", "Project")
    Workspace = apps.get_model("db", "Workspace")
    kini = timezone.now()

    sudah_ada_wiki = set()
    for wiki in Project.objects.filter(identifier=WIKI, deleted_at__isnull=True):
        page_ids = _pindah_satu(apps, wiki, kini)
        _pensiunkan(apps, wiki, page_ids, kini)
        sudah_ada_wiki.add(wiki.workspace_id)

    # Folder divisi/departemen untuk SEMUA workspace yang punya struktur organisasi,
    # termasuk yang belum pernah punya project WIKI.
    for ws_id in Workspace.objects.filter(deleted_at__isnull=True).values_list("id", flat=True):
        _pastikan_folder_unit(apps, ws_id, kini)


def mundur(apps, schema_editor):
    Project = apps.get_model("db", "Project")
    ProjectMember = apps.get_model("db", "ProjectMember")
    ProjectPage = apps.get_model("db", "ProjectPage")
    Page = apps.get_model("db", "Page")
    FileAsset = apps.get_model("db", "FileAsset")
    WikiFolderAccess = apps.get_model("db", "WikiFolderAccess")
    WikiGovernedProject = apps.get_model("db", "WikiGovernedProject")
    WikiMaterial = apps.get_model("db", "WikiMaterial")
    WikiFolder = apps.get_model("db", "WikiFolder")

    for wiki in Project.objects.filter(identifier=WIKI, deleted_at__isnull=False):
        cap = wiki.deleted_at
        for model, kolom in (
            (ProjectMember, "project_id"),
            (ProjectPage, "project_id"),
            (WikiFolderAccess, "project_id"),
            (WikiGovernedProject, "project_id"),
        ):
            model.objects.filter(**{kolom: wiki.id}, deleted_at=cap).update(deleted_at=None)
        page_ids = list(ProjectPage.objects.filter(project_id=wiki.id).values_list("page_id", flat=True))
        Page.objects.filter(id__in=page_ids, deleted_at=cap).update(deleted_at=None)

        for m in WikiMaterial.objects.filter(workspace_id=wiki.workspace_id).select_related("berkas"):
            atribut = dict(m.berkas.attributes or {})
            asal = atribut.pop(KUNCI_ASAL, MATERI)
            page_asal = atribut.pop("_wiki_page_asal", None) or (
                str(m.folder_id) if m.folder_id in set(page_ids) else None
            )
            FileAsset.objects.filter(id=m.berkas_id).update(
                entity_type=asal,
                attributes=atribut,
                project_id=wiki.id,
                page_id=page_asal,
                entity_identifier=None,
            )
            if m.pratinjau_id:
                FileAsset.objects.filter(id=m.pratinjau_id).update(project_id=wiki.id, page_id=page_asal)
        Project.objects.filter(id=wiki.id).update(deleted_at=None)

    WikiMaterial.objects.all().delete()
    WikiFolder.objects.filter(parent__isnull=False).delete()
    WikiFolder.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("db", "0170_wiki_mandiri")]

    operations = [migrations.RunPython(maju, mundur)]
