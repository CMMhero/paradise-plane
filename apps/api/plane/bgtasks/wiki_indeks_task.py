# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: mengindeks isi materi Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Membaca isi sebuah materi Wiki dan menyimpannya di `WikiMaterial.isi_teks`
supaya pencarian bisa menemukan dokumen lewat isinya.

Dijalankan sesudah unggah dan sesudah konversi PDF. Aman dipanggil berulang:
hasilnya selalu ditimpa dengan pembacaan terbaru. Satu materi yang gagal dibaca
tidak boleh menjatuhkan siapa pun, jadi galat hanya dicatat dan kolomnya
dibiarkan kosong (materi tetap bisa dicari lewat judulnya).
"""

from celery import shared_task
from django.utils import timezone

from plane.db.models import WikiMaterial
from plane.settings.storage import S3Storage
from plane.utils.exception_logger import log_exception
from plane.utils.wiki_isi import batas_baca, ekstrak_teks, jenis_sumber


def _ambil(penyimpanan, berkas, maks):
    """Paling banyak `maks` byte pertama dari penyimpanan, atau None bila gagal / terlalu besar."""
    objek = penyimpanan.s3_client.get_object(
        Bucket=penyimpanan.aws_storage_bucket_name,
        Key=berkas.asset.name,
        Range=f"bytes=0-{maks}",
    )
    data = objek["Body"].read(maks + 1)
    # PDF dan zip tidak bisa dibaca setengah; yang melebihi batas dilewati.
    return data[:maks] if len(data) <= maks else None


def indeks_satu(materi):
    """Baca dan simpan isi satu materi. True bila selesai (walau tanpa teks)."""
    atribut = materi.berkas.attributes or {}
    nama = atribut.get("name") or ""
    jenis = jenis_sumber(atribut.get("type") or "", nama)
    teks = ""
    if jenis is not None:
        sumber = materi.berkas
        if jenis == "pratinjau":
            # Word lama, PowerPoint, OpenDocument: hanya PDF hasil konversi yang bisa dibaca.
            pr = materi.pratinjau
            if pr is None or not pr.is_uploaded or pr.is_deleted:
                # Belum dikonversi. Jangan tandai selesai: konversi memanggil kita lagi.
                return False
            sumber, jenis = pr, "pdf"
        data = _ambil(S3Storage(), sumber, batas_baca(jenis))
        teks = ekstrak_teks(data, jenis, nama) if data else ""
    WikiMaterial.objects.filter(id=materi.id).update(isi_teks=teks, diindeks_pada=timezone.now())
    return True


@shared_task
def indeks_materi(materi_id):
    try:
        materi = WikiMaterial.objects.select_related("berkas", "pratinjau").get(pk=materi_id)
        if not materi.berkas.is_uploaded or materi.berkas.is_deleted:
            return
        indeks_satu(materi)
    except WikiMaterial.DoesNotExist:
        return
    except Exception as e:  # noqa: BLE001
        log_exception(e)
