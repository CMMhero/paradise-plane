# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: HTML editor jadi teks untuk email dan kartu
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""HTML editor (komentar, deskripsi) jadi sesuatu yang bisa dibaca di luar editor.

Dua bentuk keluaran:

* `ganti_sebutan`: tetap HTML, hanya `<mention-component>` yang diganti teksnya.
  Untuk email pembaruan, yang memang merender HTML komentar.
* `teks_polos`: teks tanpa tag. Untuk kartu obrolan dan email pengumuman.
  Paragraf jadi baris baru, entitas didekode, sebutan jadi `@Nama`.
* `teks_dokumen`: teks yang dibaca utuh di luar aplikasi (unduhan Excel). Poin
  daftar, centang, alamat tautan, dan jejak gambar atau berkas dipertahankan.

Editor menyimpan sebutan sebagai `<mention-component entity_identifier=...>`
tanpa isi. Tanpa penggantian di sini, `get_text()` biasa membuang namanya dan
kalimat "Pagi mas @Budi" terbaca "Pagi mas".
"""

import re
from collections.abc import Callable
from uuid import UUID

from bs4 import BeautifulSoup, NavigableString, Tag

# Tag yang menutup satu baris. Isinya diberi baris baru di ujung supaya dua
# paragraf tidak menempel jadi satu kalimat.
TAG_BLOK = ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "tr")

_ID_SEBUTAN = re.compile(r"""entity_identifier=["']([0-9a-fA-F]{8}-?(?:[0-9a-fA-F]{4}-?){3}[0-9a-fA-F]{12})["']""")


def _urai_sebutan(mention) -> tuple[str, UUID | None]:
    """(jenis, id) satu `mention-component`. Id yang bukan UUID jadi None."""
    from plane.utils.rujukan_obrolan import urai_uuid  # noqa: PLC0415

    sah = urai_uuid([mention.get("entity_identifier")], 1)
    return mention.get("entity_name") or "user_mention", sah[0] if sah else None


def _tulis_sebutan(jenis, objek) -> str:
    """Teks satu sebutan. `objek` = kanal, work item, atau orang yang disebut, atau None.

    KEP-91: editor bisa menyebut orang, @all, #kanal, dan #work item. Nama kanal
    privat tidak pernah ditulis: email dan kartu bisa dibaca orang yang bukan
    anggotanya.
    """
    from plane.db.models import Ruang  # noqa: PLC0415
    from plane.utils.rujukan_obrolan import NAMA_PRIVAT  # noqa: PLC0415

    if jenis == "everyone_mention":
        return "@all"
    if jenis == "channel_mention":
        if objek is not None and objek.tipe == Ruang.Tipe.KANAL and objek.nama:
            return f"#{objek.nama}"
        return f"#{NAMA_PRIVAT}"
    if jenis == "issue_mention":
        return f"{objek.project.identifier}-{objek.sequence_id}" if objek is not None else "#work-item"
    return f"@{objek.display_name}" if objek is not None else "@unknown"


def teks_sebutan(mention) -> str:
    """Teks pengganti satu `mention-component`."""
    from plane.db.models import Issue, Ruang, User  # noqa: PLC0415

    jenis, ident = _urai_sebutan(mention)
    sumber = {
        "everyone_mention": None,
        "channel_mention": Ruang.objects.only("nama", "tipe"),
        "issue_mention": Issue.objects.select_related("project"),
    }.get(jenis, User.objects.only("display_name"))
    objek = sumber.filter(pk=ident).first() if sumber is not None and ident else None
    return _tulis_sebutan(jenis, objek)


def sebutan_massal(daftar_html, saring_tugas) -> Callable[[Tag], str]:
    """Pengganti `teks_sebutan` untuk banyak dokumen, dengan jumlah kueri tetap.

    `saring_tugas` menerima queryset work item dan mengembalikan bagian yang
    boleh dilihat pembacanya: sisanya ditulis tanpa kode.
    """
    from plane.db.models import Issue, Ruang, User  # noqa: PLC0415

    ids = {UUID(ident) for html in daftar_html if html for ident in _ID_SEBUTAN.findall(html)}
    objek = {
        "channel_mention": Ruang.objects.only("nama", "tipe").in_bulk(ids),
        "issue_mention": saring_tugas(Issue.objects.filter(pk__in=ids)).select_related("project").in_bulk(),
        "user_mention": User.objects.only("display_name").in_bulk(ids),
    }

    def tulis(mention):
        jenis, ident = _urai_sebutan(mention)
        return _tulis_sebutan(jenis, objek.get(jenis, objek["user_mention"]).get(ident))

    return tulis


def _sup(html) -> BeautifulSoup:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for mention in soup.find_all("mention-component"):
        mention.replace_with(teks_sebutan(mention))
    return soup


def ganti_sebutan(html) -> str:
    """HTML yang sama, dengan tiap `mention-component` jadi teks sebutannya."""
    return str(_sup(html))


def _jadi_baris(soup: BeautifulSoup) -> str:
    """Satu baris per paragraf, spasi dirapikan, baris kosong dibuang."""
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for blok in soup.find_all(TAG_BLOK):
        blok.append(NavigableString("\n"))
    baris = (" ".join(b.split()) for b in soup.get_text().splitlines())
    return "\n".join(b for b in baris if b)


def teks_polos(html) -> str:
    """Teks tanpa tag: satu baris per paragraf, spasi dirapikan, baris kosong dibuang."""
    return _jadi_baris(_sup(html))


def teks_dokumen(html, sebutan: Callable[[Tag], str], gambar: str, berkas: str) -> str:
    """Isi editor sebagai teks yang tetap bisa dipahami tanpa aplikasinya.

    `gambar` dan `berkas` adalah kata untuk label pengganti, dalam bahasa pembaca.
    """
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for mention in soup.find_all("mention-component"):
        mention.replace_with(sebutan(mention))
    for tag in soup.find_all(["image-component", "img"]):
        tag.replace_with(f"\n[{gambar}]\n")
    for tag in soup.find_all("file-component"):
        nama = tag.get("name")
        tag.replace_with(f"\n[{berkas}: {nama}]\n" if nama else f"\n[{berkas}]\n")
    for tautan in soup.find_all("a", href=True):
        alamat = tautan["href"]
        if alamat.startswith(("http://", "https://")) and alamat.rstrip("/") not in tautan.get_text():
            tautan.append(f" ({alamat})")
    # Satu baris tabel = satu baris teks, jadi paragraf di dalam sel diratakan.
    for sel in soup.find_all(["td", "th"]):
        isi = " ".join(sel.get_text(" ").split())
        sel.string = f"{isi} | " if sel.find_next_sibling(["td", "th"]) else isi
    for butir in soup.find_all("li"):
        if butir.get("data-type") == "taskItem":
            butir.insert(0, "[x] " if butir.get("data-checked") == "true" else "[ ] ")
        else:
            butir.insert(0, "- ")
    return _jadi_baris(soup)
