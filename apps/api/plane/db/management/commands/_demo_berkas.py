# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi data demo, berkas sungguhan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Berkas demo yang benar-benar ada di MinIO, bukan baris FileAsset kosong.

Berkas berawalan `_` supaya Django tidak membacanya sebagai command.

Lampiran tanpa objek di storage tampak hidup di daftar tapi gagal saat diklik,
dan itu lebih buruk daripada tidak ada lampiran sama sekali. Karena itu tiap
berkas dibuat utuh (PDF, PNG, CSV, TXT yang valid) lalu diunggah lewat
`S3Storage.upload_file`, storage yang sama dengan unggahan dari peramban.

Pillow tidak terpasang di image API, jadi PNG dan PDF ditulis tangan. Keduanya
sengaja sederhana: satu grafik batang, satu halaman teks.
"""

# Python imports
import io
import struct
import uuid
import zlib

# Module imports
from plane.db.models import FileAsset
from plane.settings.storage import S3Storage

SUMBER_BERKAS = "seed-demo"


def unggah(ws, pemilik, nama, data, tipe, entity_type, **fk):
    """Unggah `data` ke MinIO lalu catat FileAsset-nya. Kunci objek sama dengan unggahan web."""
    kunci = f"{ws.id}/{uuid.uuid4().hex}-{nama}"
    if not S3Storage().upload_file(io.BytesIO(data), kunci, content_type=tipe):
        raise RuntimeError(f"Gagal mengunggah {nama} ke storage. Cek MinIO.")
    aset = FileAsset(
        attributes={"name": nama, "type": tipe, "size": len(data)},
        asset=kunci,
        size=len(data),
        workspace=ws,
        entity_type=entity_type,
        is_uploaded=True,
        external_source=SUMBER_BERKAS,
        **fk,
    )
    aset.save(created_by_id=pemilik.id)
    return aset


def hapus_berkas_demo(qs):
    """Buang objek MinIO milik FileAsset demo sebelum barisnya terhapus (kaskade tidak menyentuh storage)."""
    kunci = [str(k) for k in qs.filter(external_source=SUMBER_BERKAS).values_list("asset", flat=True) if k]
    if kunci:
        S3Storage().delete_files(kunci)
    return len(kunci)


# ------------------------------------------------------------- generator


def pdf(judul, baris):
    """PDF satu halaman berisi judul + baris teks (Helvetica, tanpa dependensi)."""

    def aman(teks):
        return teks.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", "replace")

    isi = b"BT /F1 18 Tf 56 780 Td (" + aman(judul) + b") Tj ET\n"
    y = 748
    for teks in baris:
        isi += b"BT /F1 11 Tf 56 " + str(y).encode() + b" Td (" + aman(teks) + b") Tj ET\n"
        y -= 18
    objek = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(isi)).encode() + b" >>\nstream\n" + isi + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    keluar = b"%PDF-1.4\n"
    posisi = []
    for i, o in enumerate(objek, start=1):
        posisi.append(len(keluar))
        keluar += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(keluar)
    keluar += f"xref\n0 {len(objek) + 1}\n0000000000 65535 f \n".encode()
    keluar += b"".join(f"{p:010d} 00000 n \n".encode() for p in posisi)
    keluar += f"trailer\n<< /Size {len(objek) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return keluar


def png_grafik(nilai, warna=(208, 2, 27), lebar=360, tinggi=200):
    """PNG grafik batang sederhana dari daftar angka 0..100."""
    latar, garis = (250, 250, 250), (220, 220, 220)
    n = max(len(nilai), 1)
    slot = lebar // n
    baris = []
    for y in range(tinggi):
        piksel = bytearray()
        for x in range(lebar):
            i = min(x // slot, n - 1)
            tinggi_batang = int(nilai[i] / 100 * (tinggi - 20))
            dalam_batang = slot * 0.2 < x % slot < slot * 0.8 and y >= tinggi - 10 - tinggi_batang and y < tinggi - 10
            if dalam_batang:
                piksel += bytes(warna)
            elif y == tinggi - 10 or y % 40 == 0:
                piksel += bytes(garis)
            else:
                piksel += bytes(latar)
        baris.append(b"\x00" + bytes(piksel))

    def potong(jenis, data):
        isi = jenis + data
        return struct.pack(">I", len(data)) + isi + struct.pack(">I", zlib.crc32(isi) & 0xFFFFFFFF)

    kepala = struct.pack(">IIBBBBB", lebar, tinggi, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + potong(b"IHDR", kepala)
        + potong(b"IDAT", zlib.compress(b"".join(baris), 9))
        + potong(b"IEND", b"")
    )


def csv(kepala, baris):
    teks = [",".join(kepala)] + [",".join(str(s) for s in b) for b in baris]
    return ("\n".join(teks) + "\n").encode("utf-8")


def txt(teks):
    return teks.encode("utf-8")
