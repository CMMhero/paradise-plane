# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Memindahkan SATU workspace utuh dari satu database ke database lain.

KENAPA INI PERLU ADA SEBELUM ADA YANG MEMBUTUHKANNYA

Di topologi yang dipilih, perusahaan gratis hidup sebagai satu workspace di
kolam bersama, sedangkan perusahaan berbayar mendapat instance dan database
sendiri. Jadi "naik kelas" bukan mengubah satu kolom tingkatan, melainkan
MEMINDAHKAN DATA antar database.

Kalau jalur itu baru dipikirkan saat pelanggan pertama membayar, pemindahannya
jadi pekerjaan manual semalaman, dan itu terjadi persis di hari yang paling
tidak boleh ada masalah.

DAFTAR MODELNYA TIDAK DITULIS TANGAN, DAN ITU INTI BERKAS INI

Ada 112 model di instalasi ini. Eksporter yang daftarnya diketik manusia akan
tertinggal pada model ke-113, dan kegagalannya TIDAK BERGEJALA: ekspor tetap
sukses, impor tetap sukses, dan yang hilang baru ketahuan berbulan-bulan
kemudian oleh orang yang mencari datanya.

Jadi yang ditulis tangan di sini bukan daftar yang IKUT, melainkan daftar yang
sengaja DITINGGAL, masing-masing dengan alasannya. Sisanya diturunkan dari
skema. Model baru yang tidak masuk kategori mana pun akan membuat
`klasifikasi()` menaruhnya di `tidak_dikenal`, dan uji penjaga menggagalkan
build sampai ada manusia yang memutuskan. Komentar tidak bisa menggagalkan
build; uji bisa.

YANG TIDAK DIURUS BERKAS INI

Objek di penyimpanan (MinIO/S3) tidak ikut. Yang dihasilkan adalah MANIFES berisi
kunci objeknya, dan penyalinan dilakukan operator dengan alat penyimpanan biasa.
Menyalin ratusan megabyte lewat proses Django adalah cara paling lambat dan
paling mudah gagal di tengah untuk melakukan sesuatu yang `mc mirror` selesaikan
dengan benar termasuk melanjutkan yang terputus.
"""

import json

from django.apps import apps

# --- Model yang sengaja TIDAK ikut, beserta alasannya -------------------------
#
# Alasan wajib ditulis. Daftar pengecualian tanpa alasan akan berubah jadi
# tempat sampah begitu ada orang yang buru-buru.
DILEWATI = {
    # Keadaan autentikasi dan sesi. Terikat ke instance asal, dan memindahkannya
    # berarti memindahkan sesi hidup ke mesin lain.
    "db.Account": "kredensial penyedia OAuth, milik instance asal",
    "db.Session": "sesi hidup, tidak boleh berpindah mesin",
    "db.Device": "perangkat terdaftar, terikat sesi",
    "db.DeviceSession": "turunan Device",
    "db.SocialLoginConnection": "sambungan login sosial, milik instance asal",
    "db.LoginActivity": "jejak masuk, riwayat keamanan instance asal",
    # Catatan dan log. Besar, dan tidak ada artinya di instance baru.
    "db.EmailNotificationLog": "log pengiriman surel instance asal",
    "db.APIActivityLog": "log permintaan API instance asal",
    # Katalog dan keadaan global instance.
    "db.Integration": "katalog integrasi, sama di tiap instance",
    "db.KalenderGoogle": "token OAuth Google, terikat aplikasi OAuth instance asal",
    "db.AcaraKalender": "pemetaan acara ke kalender Google instance asal",
    # Milik lapisan lain, bukan milik workspace.
    "license.Instance": "identitas instance itu sendiri",
    "license.InstanceAdmin": "admin instance, bukan anggota workspace",
    "license.InstanceConfiguration": "konfigurasi instance",
    "license.ChangeLog": "catatan rilis instance",
    "control.Company": "bidang kendali tidak pernah ikut pindah ke penyewa",
    "control.Subscription": "bidang kendali",
    "control.TenantInstance": "bidang kendali",
    "control.UsageSnapshot": "bidang kendali",
    "control.Invoice": "bidang kendali, dan catatan keuangan tidak pernah ikut ke penyewa",
    "django_celery_beat.PeriodicTask": "keadaan penjadwal, milik instance",
    "django_celery_beat.PeriodicTasks": "keadaan penjadwal",
    "django_celery_beat.CrontabSchedule": "keadaan penjadwal",
    "django_celery_beat.IntervalSchedule": "keadaan penjadwal",
    "django_celery_beat.SolarSchedule": "keadaan penjadwal",
    "django_celery_beat.ClockedSchedule": "keadaan penjadwal",
    # Riwayat audit menunjuk objeknya lewat generic FK (content_type + object_pk),
    # jadi memindahkannya sebagian berarti memindahkan baris yang menunjuk ke
    # objek yang tidak ada di database tujuan. Dan riwayat audit memang catatan
    # kepatuhan milik instance, bukan milik workspace.
    #
    # KONSEKUENSINYA NYATA DAN SENGAJA DITERIMA: workspace yang pindah kehilangan
    # jejak auditnya. Kalau suatu saat ada pelanggan yang menuntut jejak itu ikut,
    # yang dibutuhkan bukan menambahkannya ke ekspor melainkan mengarsipkan
    # jejaknya di instance asal dan menyerahkannya terpisah.
    "auditlog.LogEntry": "riwayat audit generic-FK, milik instance asal",
}

# App bawaan Django yang tidak pernah relevan.
APP_DILEWATI = {"admin", "auth", "contenttypes", "sessions", "token_blacklist"}

# Model yang MEMANG milik workspace tapi tidak punya FK langsung ke sana. Nilai
# petanya adalah jalur lookup dari model itu ke workspace.
LEWAT_INDUK = {
    "db.Langganan": "ruang__workspace_id",
    "db.ReaksiPesan": "pesan__workspace_id",
}

# Diurus dengan tangan karena bukan "baris milik workspace" biasa.
KHUSUS = {
    "db.Workspace": "akar yang sedang dipindahkan",
    "db.User": "identitas global, hanya anggota workspace ini yang ikut",
    "db.Profile": "menempel satu-satu ke User",
}


def _label(model):
    return f"{model._meta.app_label}.{model.__name__}"


def _punya_fk_workspace(model):
    for f in model._meta.get_fields():
        if (getattr(f, "many_to_one", False) or getattr(f, "one_to_one", False)) and f.name == "workspace":
            return True
    return False


def klasifikasi():
    """Bagi SELURUH model instalasi ini ke dalam empat keranjang.

    `tidak_dikenal` harus selalu kosong. Kalau tidak, ada model yang tidak
    seorang pun pernah memutuskan nasibnya saat workspace dipindahkan, dan
    menebaknya di sini berarti menebak apakah data pelanggan ikut atau hilang.
    """
    hasil = {"langsung": [], "lewat_induk": [], "khusus": [], "dilewati": [], "tidak_dikenal": []}
    for model in apps.get_models():
        if model._meta.app_label in APP_DILEWATI:
            continue
        label = _label(model)
        if label in KHUSUS:
            hasil["khusus"].append(label)
        elif label in DILEWATI:
            hasil["dilewati"].append(label)
        elif label in LEWAT_INDUK:
            hasil["lewat_induk"].append(label)
        elif _punya_fk_workspace(model):
            hasil["langsung"].append(label)
        else:
            hasil["tidak_dikenal"].append(label)
    for k in hasil:
        hasil[k].sort()
    return hasil


def _model(label):
    app_label, nama = label.split(".")
    return apps.get_model(app_label, nama)


def kumpulkan(workspace):
    """Semua baris milik satu workspace, dikelompokkan per model.

    Urutannya disengaja: Workspace dulu, lalu User dan Profile, baru sisanya.
    Impor menjalankannya dengan pemeriksaan constraint ditunda, jadi urutan
    sebenarnya tidak wajib, tapi berkas ekspor yang urutannya masuk akal jauh
    lebih mudah dibaca manusia saat ada yang perlu diperiksa dengan mata.
    """
    from plane.db.models import Profile, User, WorkspaceMember

    kelas = klasifikasi()
    if kelas["tidak_dikenal"]:
        raise RuntimeError(
            "Ada model yang belum diputuskan nasibnya saat pemindahan workspace: "
            + ", ".join(kelas["tidak_dikenal"])
            + ". Tambahkan ke DILEWATI atau LEWAT_INDUK di plane/utils/workspace_transfer.py."
        )

    anggota_ids = list(
        WorkspaceMember.objects.filter(workspace=workspace).values_list("member_id", flat=True)
    )

    kelompok = [
        ("db.Workspace", type(workspace).objects.filter(pk=workspace.pk)),
        ("db.User", User.objects.filter(id__in=anggota_ids)),
        ("db.Profile", Profile.objects.filter(user_id__in=anggota_ids)),
    ]

    for label in kelas["langsung"]:
        kelompok.append((label, _model(label).objects.filter(workspace_id=workspace.id)))

    for label in kelas["lewat_induk"]:
        jalur = LEWAT_INDUK[label]
        kelompok.append((label, _model(label).objects.filter(**{jalur: workspace.id})))

    return kelompok


def manifes_aset(workspace):
    """Kunci objek penyimpanan yang harus ikut disalin operator.

    Barisnya ada di ekspor, ISINYA tidak. Manifes ini yang membuat perbedaan itu
    terlihat, bukan ditemukan belakangan sebagai berkas yang tidak bisa dibuka.
    """
    from plane.db.models import FileAsset

    return list(
        FileAsset.objects.filter(workspace_id=workspace.id, deleted_at__isnull=True)
        .exclude(asset="")
        .values_list("asset", flat=True)
    )


# --- Objek penyimpanan --------------------------------------------------------
#
# KENAPA TIAP SISI MEMAKAI PENYIMPANANNYA SENDIRI
#
# Cara yang tampak paling langsung adalah satu perintah yang menyambung ke DUA
# endpoint S3 sekaligus lalu menyalin antar keduanya. Itu menuntut kredensial
# penyimpanan asal DAN tujuan berada di satu tempat pada saat yang sama, dan
# tempat itu biasanya laptop operator.
#
# Yang dipakai di sini: ekspor mengunduh dari penyimpanan instance ASAL, impor
# mengunggah ke penyimpanan instance TUJUAN, dan keduanya memakai kredensial
# yang memang sudah ada di masing-masing instance. Nol konfigurasi baru, dan
# tidak ada kredensial yang pernah berpindah mesin.
#
# Perantaranya satu berkas tar. Berkas bisa di-scp, di-rsync, dilanjutkan saat
# putus, dan diperiksa isinya, semuanya oleh alat yang sudah dikenal orang.

MANIFES_DI_TAR = "_manifest.json"

# Level 1, bukan 9. Isi tar ini didominasi gambar dan PDF yang sudah terkompresi,
# jadi level tinggi menghabiskan CPU untuk penghematan yang nyaris nol.
GZIP_LEVEL = 1


def unduh_aset(kunci, tujuan, log=print):
    """Unduh objek dari penyimpanan instance INI ke satu berkas tar.

    Objek yang barisnya ada tapi berkasnya hilang TIDAK menggagalkan ekspor.
    Berkas yang sudah hilang di asal tidak akan menjadi ada karena ekspornya
    dibatalkan, dan membatalkan berarti pemindahannya tertahan oleh satu berkas
    rusak yang mungkin sudah lama tidak dipakai siapa pun. Yang hilang dicatat
    dan dilaporkan di akhir.

    Tipe konten disimpan di manifes DI DALAM tar, bukan ditebak ulang saat
    impor. Menebaknya dari ekstensi akan menyajikan PDF sebagai
    application/octet-stream, dan penampil Wiki merender PDF di dalam iframe
    peramban yang menolak menampilkannya kalau tipenya salah.
    """
    import tarfile
    from io import BytesIO

    from botocore.exceptions import ClientError

    from plane.settings.storage import S3Storage

    penyimpanan = S3Storage()
    tipe = {}
    hilang = []
    total = 0

    with tarfile.open(tujuan, "w:gz", compresslevel=GZIP_LEVEL) as tar:
        for k in kunci:
            try:
                obj = penyimpanan.s3_client.get_object(
                    Bucket=penyimpanan.aws_storage_bucket_name, Key=k
                )
            except ClientError:
                hilang.append(k)
                continue

            ukuran = int(obj["ContentLength"])
            info = tarfile.TarInfo(name=k)
            info.size = ukuran
            tar.addfile(info, obj["Body"])
            tipe[k] = obj.get("ContentType") or "application/octet-stream"
            total += ukuran

        muatan = json.dumps({"content_types": tipe}).encode("utf-8")
        info = tarfile.TarInfo(name=MANIFES_DI_TAR)
        info.size = len(muatan)
        tar.addfile(info, BytesIO(muatan))

    if hilang:
        log(f"  {len(hilang)} objek disebut baris tapi TIDAK ADA di penyimpanan:")
        for k in hilang[:5]:
            log(f"    {k}")
        if len(hilang) > 5:
            log(f"    ... dan {len(hilang) - 5} lagi")

    return {"disalin": len(tipe), "hilang": hilang, "bytes": total}


def unggah_aset(sumber, log=print):
    """Unggah isi tar ke penyimpanan instance INI.

    Kegagalan unggah MENGGAGALKAN, kebalikan dari kebijakan unduh. Bedanya
    disengaja: unduhan yang tidak lengkap menghasilkan paket yang kekurangannya
    tercatat dan terlihat, sedangkan unggahan yang tidak lengkap menghasilkan
    instance yang tampak beres padahal sebagian berkasnya tidak akan pernah
    terbuka. Yang kedua baru ketahuan oleh pemakainya.
    """
    import tarfile

    from plane.settings.storage import S3Storage

    penyimpanan = S3Storage()
    naik = 0
    gagal = []

    with tarfile.open(sumber, "r:gz") as tar:
        manifes = tar.extractfile(MANIFES_DI_TAR)
        tipe = json.loads(manifes.read().decode("utf-8"))["content_types"] if manifes else {}

        for anggota in tar.getmembers():
            if anggota.name == MANIFES_DI_TAR or not anggota.isfile():
                continue
            isi = tar.extractfile(anggota)
            if isi is None:
                gagal.append(anggota.name)
                continue
            berhasil = penyimpanan.upload_file(
                isi, anggota.name, content_type=tipe.get(anggota.name)
            )
            if berhasil:
                naik += 1
            else:
                gagal.append(anggota.name)

    if gagal:
        log(f"  {len(gagal)} objek GAGAL diunggah:")
        for k in gagal[:5]:
            log(f"    {k}")
        raise RuntimeError(
            f"{len(gagal)} objek gagal diunggah. Instance ini BELUM siap diserahkan: "
            "barisnya ada tapi berkasnya tidak akan bisa dibuka."
        )

    return {"diunggah": naik}
