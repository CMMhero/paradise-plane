# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pratinjau isi berkas Materi Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pratinjau isi berkas Wiki langsung di aplikasi, tanpa konversi ke PDF.

Modul ini murni: menerima bytes, mengembalikan struktur JSON. Tidak ada akses
jaringan atau penyimpanan di sini, jadi semuanya bisa diuji tanpa MinIO.

Yang dibaca:

- teks polos (txt, log, json, xml, yaml, sql, ...) dan Markdown;
- CSV/TSV dan Excel (xlsx) menjadi tabel per lembar;
- Word (docx) menjadi blok terstruktur (judul, paragraf, daftar, tabel).

Selalu JSON terstruktur, TIDAK PERNAH HTML. Isi berkas adalah unggahan orang, dan
klien merender tiap blok dengan elemen React biasa, jadi tidak ada jalur untuk
menyisipkan skrip. Semua pembacaan dibatasi (ukuran, baris, kolom, lembar,
blok) supaya satu berkas besar tidak menahan worker.
"""

import csv
import io
import posixpath
import zipfile
from datetime import date, datetime, time
from itertools import islice

from lxml import etree

# ---------------------------------------------------------------- batas baca
TEKS_MAKS_BYTE = 2 * 1024 * 1024
CSV_MAKS_BYTE = 10 * 1024 * 1024
BERKAS_ZIP_MAKS_BYTE = 15 * 1024 * 1024
ZIP_TERURAI_MAKS_BYTE = 300 * 1024 * 1024
ZIP_MAKS_ENTRI = 10000
XML_UTAMA_MAKS_BYTE = 50 * 1024 * 1024

BARIS_MAKS = 2000
KOLOM_MAKS = 60
LEMBAR_MAKS = 20
SEL_MAKS_KARAKTER = 1000
BLOK_MAKS = 5000

# ----------------------------------------------------- jenis menurut tipe/nama
# Tipe yang HARUS dikonversi dulu: tidak ada peramban yang bisa membukanya.
PERLU_KONVERSI = {
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/rtf",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
}

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

MIME_TEKS = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "text/csv",
    "text/tab-separated-values",
    "text/css",
    "text/javascript",
    "text/xml",
    "application/xml",
    "application/json",
    "application/x-sql",
}

# Tipe yang sering dilaporkan salah oleh peramban/sistem: berkas teks tanpa tanda
# tangan biner jatuh ke "" atau octet-stream, dan Windows melaporkan .csv sebagai
# tipe Excel. Untuk itu ekstensi yang menentukan.
_MIME_GENERIK = {"", "application/octet-stream", "application/vnd.ms-excel", "text/plain"}

_EKSTENSI_KE_JENIS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".csv": "csv",
    ".tsv": "csv",
    ".txt": "text",
    ".text": "text",
    ".log": "text",
    ".json": "text",
    ".xml": "text",
    ".yml": "text",
    ".yaml": "text",
    ".ini": "text",
    ".cfg": "text",
    ".conf": "text",
    ".toml": "text",
    ".env": "text",
    ".sql": "text",
    ".css": "text",
    ".js": "text",
    ".ts": "text",
    ".py": "text",
    ".sh": "text",
    ".html": "text",
}

# Dipakai saat unggah, bila klien tidak bisa menyebut tipe (berkas teks).
_EKSTENSI_KE_MIME = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".text": "text/plain",
    ".log": "text/plain",
    ".json": "application/json",
    ".xml": "text/xml",
    ".sql": "application/x-sql",
    ".css": "text/css",
}


def _ekstensi(nama):
    return posixpath.splitext((nama or "").lower())[1]


def tebak_mime(nama):
    """Tipe berkas dari ekstensinya. Dipakai hanya kalau klien tidak menyebutnya."""
    return _EKSTENSI_KE_MIME.get(_ekstensi(nama), "application/octet-stream")


def jenis_pratinjau(mime, nama=""):
    """Bagaimana sebuah berkas ditampilkan.

    Nilai: pdf, image, video, audio (peramban sendiri), text, markdown, csv,
    xlsx, docx (dibaca server), konversi (lewat Gotenberg), none.
    """
    mime = (mime or "").split(";")[0].strip().lower()
    ekstensi = _ekstensi(nama)

    if mime == "video/x-matroska":
        return "none"
    if mime == "application/pdf":
        return "pdf"
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"

    if mime == MIME_XLSX or (mime in _MIME_GENERIK and ekstensi in (".xlsx", ".xlsm")):
        return "xlsx"
    if mime == MIME_DOCX or (mime in _MIME_GENERIK and ekstensi == ".docx"):
        return "docx"

    # Ekstensi menang atas tipe yang generik atau teks: .md sering datang sebagai
    # text/plain, dan .csv sebagai tipe Excel.
    if mime in _MIME_GENERIK or mime in MIME_TEKS:
        dari_nama = _EKSTENSI_KE_JENIS.get(ekstensi)
        if dari_nama:
            return dari_nama
    if mime in ("text/markdown", "text/x-markdown"):
        return "markdown"
    if mime in ("text/csv", "text/tab-separated-values"):
        return "csv"
    if mime in MIME_TEKS:
        return "text"

    if mime in PERLU_KONVERSI:
        return "konversi"
    return "none"


# ------------------------------------------------------------------- teks
def dekode_teks(data, terpotong=False):
    """bytes -> str, atau None kalau isinya jelas bukan teks.

    `terpotong`: bytes dibaca sebagian, jadi karakter multibita di ujungnya boleh
    putus tanpa menggagalkan sisanya.
    """
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    # NUL di awal = biner (utf-16 tanpa BOM juga jatuh di sini, dan itu wajar).
    if b"\x00" in data[:4096]:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        if terpotong and e.start >= len(data) - 3:
            return data[: e.start].decode("utf-8-sig", errors="replace")
    # Berkas lama Windows (Excel "CSV", Notepad) hampir selalu cp1252.
    return data.decode("cp1252", errors="replace")


def baca_teks(data, terpotong=False):
    """Hasil untuk jenis text dan markdown, atau None kalau bukan teks."""
    teks = dekode_teks(data, terpotong)
    if teks is None:
        return None
    return {"text": teks, "truncated": terpotong}


# -------------------------------------------------------------------- tabel
def _potong_sel(nilai):
    teks = str(nilai)
    return teks if len(teks) <= SEL_MAKS_KARAKTER else teks[:SEL_MAKS_KARAKTER] + "…"


def _sel_ke_teks(nilai):
    if nilai is None:
        return ""
    if isinstance(nilai, bool):
        return "TRUE" if nilai else "FALSE"
    if isinstance(nilai, datetime):
        return nilai.date().isoformat() if nilai.time() == time(0, 0) else nilai.isoformat(sep=" ")
    if isinstance(nilai, date):
        return nilai.isoformat()
    if isinstance(nilai, time):
        return nilai.isoformat()
    if isinstance(nilai, float):
        return str(int(nilai)) if nilai.is_integer() and abs(nilai) < 1e15 else format(nilai, ".15g")
    return _potong_sel(nilai)


def _rapikan_baris(baris):
    """Buang baris kosong di ujung dan kolom kosong di ujung, supaya lembar yang
    dimensinya digelembungkan format sel tidak tampil sebagai tabel raksasa."""
    while baris and not any(baris[-1]):
        baris.pop()
    lebar = 0
    for b in baris:
        for i in range(len(b) - 1, -1, -1):
            if b[i]:
                lebar = max(lebar, i + 1)
                break
    return [b[:lebar] + [""] * (lebar - len(b[:lebar])) for b in baris]


def _lembar(nama, baris_mentah, terpotong_baris):
    baris = _rapikan_baris([[_sel_ke_teks(c) for c in b] for b in baris_mentah])
    terpotong_kolom = any(len(b) > KOLOM_MAKS for b in baris)
    if terpotong_kolom:
        baris = [b[:KOLOM_MAKS] for b in baris]
    return {"name": nama, "rows": baris, "truncated": terpotong_baris or terpotong_kolom}


def baca_csv(data, nama="", terpotong=False):
    """CSV/TSV menjadi satu lembar. None kalau bukan teks."""
    teks = dekode_teks(data, terpotong)
    if teks is None:
        return None
    if _ekstensi(nama) == ".tsv":
        pemisah = "\t"
    else:
        try:
            pemisah = csv.Sniffer().sniff(teks[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            pemisah = ","
    try:
        pembaca = csv.reader(io.StringIO(teks, newline=""), delimiter=pemisah)
        baris = list(islice(pembaca, BARIS_MAKS + 1))
    except csv.Error:
        # Kolom raksasa atau kutip tak tertutup: tampilkan apa adanya sebagai teks.
        return None
    kebanyakan = len(baris) > BARIS_MAKS
    lembar = _lembar("CSV", baris[:BARIS_MAKS], kebanyakan or terpotong)
    return {"sheets": [lembar]}


def _zip_aman(zf):
    """Tolak bom zip: terlalu banyak entri atau terlalu besar setelah diurai."""
    info = zf.infolist()
    if len(info) > ZIP_MAKS_ENTRI:
        return False
    return sum(i.file_size for i in info) <= ZIP_TERURAI_MAKS_BYTE


def baca_xlsx(data):
    """Excel (xlsx) menjadi daftar lembar. None kalau berkas rusak atau tak aman."""
    from openpyxl import load_workbook

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            if not _zip_aman(zf):
                return None
        buku = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 - zip rusak, kata sandi, format salah: semuanya "tak terbaca"
        return None

    lembar_hasil, terpotong_lembar = [], False
    try:
        for ws in buku.worksheets:
            if ws.sheet_state != "visible":
                continue
            if len(lembar_hasil) >= LEMBAR_MAKS:
                terpotong_lembar = True
                break
            mentah = list(islice(ws.iter_rows(max_col=KOLOM_MAKS + 1, values_only=True), BARIS_MAKS + 1))
            kebanyakan = len(mentah) > BARIS_MAKS
            lembar_hasil.append(_lembar(ws.title, [list(b) for b in mentah[:BARIS_MAKS]], kebanyakan))
    except Exception:  # noqa: BLE001
        return None
    finally:
        buku.close()
    if not lembar_hasil:
        return None
    return {"sheets": lembar_hasil, "sheets_truncated": terpotong_lembar}


# --------------------------------------------------------------------- docx
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_TAUTAN_AMAN = ("http://", "https://", "mailto:")


def _w(tag):
    return f"{{{_W}}}{tag}"


def _parser_xml():
    # Tanpa entitas dan tanpa jaringan: berkas ini unggahan orang.
    return etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)


def _baca_xml(zf, jalur):
    try:
        info = zf.getinfo(jalur)
    except KeyError:
        return None
    if info.file_size > XML_UTAMA_MAKS_BYTE:
        raise ValueError("part too large")
    return etree.fromstring(zf.read(jalur), parser=_parser_xml())


def _relasi_tautan(zf):
    akar = None
    try:
        akar = _baca_xml(zf, "word/_rels/document.xml.rels")
    except Exception:  # noqa: BLE001 - tautan itu tambahan, bukan syarat
        return {}
    if akar is None:
        return {}
    hasil = {}
    for rel in akar.iter(f"{{{_REL}}}Relationship"):
        target = rel.get("Target") or ""
        if rel.get("TargetMode") == "External" and target.lower().startswith(_TAUTAN_AMAN):
            hasil[rel.get("Id")] = target
    return hasil


def _hidup(el, tag):
    """Properti run seperti <w:b/> aktif kecuali w:val menyatakan mati."""
    node = el.find(_w(tag)) if el is not None else None
    if node is None:
        return False
    return node.get(_w("val"), "true").lower() not in ("0", "false", "off", "none")


def _teks_run(run):
    potongan = []
    for anak in run:
        if anak.tag == _w("t"):
            potongan.append(anak.text or "")
        elif anak.tag == _w("tab"):
            potongan.append("\t")
        elif anak.tag in (_w("br"), _w("cr")):
            potongan.append("\n")
    return "".join(potongan)


def _runs_paragraf(p, tautan):
    runs = []

    def tambah(run, href=None):
        teks = _teks_run(run)
        if not teks:
            return
        rpr = run.find(_w("rPr"))
        item = {"text": teks}
        if _hidup(rpr, "b"):
            item["bold"] = True
        if _hidup(rpr, "i"):
            item["italic"] = True
        u = rpr.find(_w("u")) if rpr is not None else None
        if u is not None and u.get(_w("val"), "single") != "none":
            item["underline"] = True
        if _hidup(rpr, "strike"):
            item["strike"] = True
        if href:
            item["href"] = href
        runs.append(item)

    for anak in p:
        if anak.tag == _w("r"):
            tambah(anak)
        elif anak.tag == _w("hyperlink"):
            href = tautan.get(anak.get(f"{{{_R}}}id"))
            for run in anak.iter(_w("r")):
                tambah(run, href)
    return runs


def _jenis_paragraf(p):
    """(jenis, tingkat) dari gaya paragraf dan penomoran."""
    ppr = p.find(_w("pPr"))
    gaya = ""
    if ppr is not None:
        ps = ppr.find(_w("pStyle"))
        gaya = (ps.get(_w("val")) if ps is not None else "") or ""
        if ppr.find(_w("numPr")) is not None:
            ilvl = ppr.find(_w("numPr")).find(_w("ilvl"))
            try:
                tingkat = int(ilvl.get(_w("val"))) if ilvl is not None else 0
            except (TypeError, ValueError):
                tingkat = 0
            return "list_item", min(max(tingkat, 0), 5)
    nama = gaya.lower().replace(" ", "")
    if nama == "title":
        return "heading", 1
    if nama == "subtitle":
        return "heading", 2
    if nama.startswith("heading") and nama[7:].isdigit():
        return "heading", min(max(int(nama[7:]), 1), 6)
    if nama.startswith("listparagraph") or nama.startswith("list"):
        return "list_item", 0
    return "paragraph", 0


def _teks_sel(tc):
    baris = []
    for p in tc.iter(_w("p")):
        baris.append("".join(_teks_run(r) for r in p.iter(_w("r"))))
    return _potong_sel("\n".join(baris).strip())


def _tabel(tbl):
    baris = []
    for tr in tbl.findall(_w("tr")):
        baris.append([_teks_sel(tc) for tc in tr.findall(_w("tc"))])
    return {"type": "table", "rows": baris[:BARIS_MAKS], "truncated": len(baris) > BARIS_MAKS}


def baca_docx(data):
    """Word (docx) menjadi blok terstruktur. Gambar, kotak teks, dan tata letak
    TIDAK ikut: ini tampilan sederhana, bukan pengganti PDF hasil konversi.

    None kalau berkas rusak atau tak aman.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            if not _zip_aman(zf):
                return None
            akar = _baca_xml(zf, "word/document.xml")
            tautan = _relasi_tautan(zf)
    except Exception:  # noqa: BLE001
        return None
    body = akar.find(_w("body")) if akar is not None else None
    if body is None:
        return None

    blok, terpotong = [], False

    def telusuri(induk):
        nonlocal terpotong
        for el in induk:
            if len(blok) >= BLOK_MAKS:
                terpotong = True
                return
            if el.tag == _w("p"):
                runs = _runs_paragraf(el, tautan)
                if not runs:
                    continue
                jenis, tingkat = _jenis_paragraf(el)
                item = {"type": jenis, "runs": runs}
                if jenis == "heading":
                    item["level"] = tingkat
                elif jenis == "list_item":
                    item["level"] = tingkat
                blok.append(item)
            elif el.tag == _w("tbl"):
                blok.append(_tabel(el))
            elif el.tag == _w("sdt"):
                isi = el.find(_w("sdtContent"))
                if isi is not None:
                    telusuri(isi)

    telusuri(body)
    return {"blocks": blok, "truncated": terpotong}
