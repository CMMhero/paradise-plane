# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: impor link portal one.paradiseperkasa.com (KEP-82)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Impor 23 link dari portal lama one.paradiseperkasa.com jadi quick link global.

Diambil 4 Nov 2026 dari halaman "Kelola Website" portal itu. Semuanya Public untuk
semua orang di setiap workspace (permintaan user: quick link global); admin bisa
mempersempit sasaran per link dari modal Quick links.

Ikon: logo situs sendiri (favicon) yang dipakai. Emoji per kategori portal hanya
cadangan (metadata.logo_cadangan) untuk situs yang tak punya favicon atau tak
terjangkau, jadi tidak pernah menimpa logo situs. Ikon pilihan admin tetap paling atas.

"HRIS - Haermes" disimpan portal dengan URL terpotong (`...returnUrl=%2...`), jadi
diarahkan ke halaman login-nya saja (`https://ids.cloudapp.id/account/login`).

Idempoten: baris dengan URL dan judul yang sama di workspace itu tidak dibuat dua kali,
jadi aman dijalankan di produksi yang sudah punya sebagian link ini. Judul & favicon
situs diisi sendiri di latar belakang saat daftar quick link pertama kali dibuka.
"""

from django.db import migrations

# (judul, url, kategori portal). Kategori dipakai untuk memilih ikon cadangan.
LINKS = [
    ("SAP Production", "https://my441843.s4hana.cloud.sap/ui#Shell-home", "SAP"),
    # Portal menyimpan URL terpotong (`...returnUrl=%2...`); pakai halaman login tanpa returnUrl.
    ("HRIS - Haermes", "https://ids.cloudapp.id/account/login", "HRIS"),
    ("HRIS", "https://hris.paradiseperkasa.com/login", "HRIS"),
    ("Website Pack", "https://pack.paradiseperkasa.com/", "Logistic"),
    ("Tenant Test", "https://my437388.s4hana.cloud.sap/", "SAP"),
    ("Tenant Development PT. Paradise Perkasa", "https://my436656.s4hana.cloud.sap/", "SAP"),
    ("Server UAT", "https://my437388.s4hana.cloud.sap/", "SAP"),
    ("Server Testing", "https://my437388.s4hana.cloud.sap/", "SAP"),
    ("SAP Starter", "https://my436383.s4hana.cloud.sap/ui#Shell-home", "SAP"),
    (
        "SAP Grow Process Flow - Google Drive",
        "https://drive.google.com/drive/folders/1F8LWRqq5xiJSBuOFEoL7ERZmmmf0Ft6d",
        "SAP",
    ),
    (
        "SAP Grow - Google Drive - Master Data",
        "https://drive.google.com/drive/folders/1xMMQjqJd4VMcRsgCGl_jyQLDhe61trfg",
        "SAP",
    ),
    ("SAP BAP PT. Paradise Perkasa", "https://basparadise.ap11cf.applicationstudio.cloud.sap/", "SAP"),
    ("Help SAP CALM", "https://help.sap.com/docs/CloudALM", "SAP"),
    ("Customizing (client 100)", "https://my436639.s4hana.cloud.sap/", "SAP"),
    ("CALM", "https://pt-paradise-perkasa-cloudalm.jp10.alm.cloud.sap/launchpad#Shell-home", "SAP"),
    ("Inspection", "https://inspect.paradiseperkasa.com/", "QAQC"),
    ("PPC", "https://productionorder.paradiseperkasa.com/dashboard", "PPC"),
    ("Plant Maintenance", "https://pm.paradiseperkasa.com/", "Maintenance"),
    ("Web Commitment", "https://forklift.paradiseperkasa.com/", "Logistic"),
    ("Web Meeting", "https://meetings.paradiseperkasa.com/", "Public"),
    ("Ticket - Helpdesk", "https://ticket.paradiseperkasa.com/", "IT"),
    ("SAP Tutorial", "https://tutorial-sap.paradiseperkasa.com/", "IT"),
    ("Digitalize Dashboard", "http://machinehub.local/dashboard", "IT"),
]

# Emoji cadangan per kategori, format kode desimal yang sama dengan pemilih ikon project.
EMOJI_KATEGORI = {
    "SAP": "128202",  # chart
    "HRIS": "128101",  # people
    "Logistic": "128666",  # truck
    "QAQC": "128269",  # magnifier
    "PPC": "127981",  # factory
    "Maintenance": "128295",  # wrench
    "Public": "127760",  # globe
    "IT": "128187",  # laptop
}
EMOJI_DRIVE = "128193"  # folder
EMOJI_BANTUAN = "128216"  # book


def _emoji(judul: str, url: str, kategori: str) -> str:
    if "drive.google.com" in url:
        return EMOJI_DRIVE
    if "help." in url or "tutorial" in url:
        return EMOJI_BANTUAN
    return EMOJI_KATEGORI.get(kategori, "128279")  # link


def impor(apps, schema_editor):
    Workspace = apps.get_model("db", "Workspace")
    QuickLinkBersama = apps.get_model("db", "QuickLinkBersama")

    for workspace in Workspace.objects.filter(deleted_at__isnull=True):
        ada = set(
            QuickLinkBersama.objects.filter(workspace=workspace, deleted_at__isnull=True).values_list("url", "title")
        )
        sort_order = 65535.0
        for judul, url, kategori in LINKS:
            sort_order += 1000
            if (url, judul) in ada:
                continue
            QuickLinkBersama.objects.create(
                workspace=workspace,
                url=url,
                title=judul,
                cakupan="semua",
                metadata={"logo_cadangan": {"in_use": "emoji", "emoji": {"value": _emoji(judul, url, kategori)}}},
                sort_order=sort_order,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0165_jadwal_terlaksana"),
    ]

    operations = [
        migrations.RunPython(impor, migrations.RunPython.noop),
    ]
