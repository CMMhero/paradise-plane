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

Editor menyimpan sebutan sebagai `<mention-component entity_identifier=...>`
tanpa isi. Tanpa penggantian di sini, `get_text()` biasa membuang namanya dan
kalimat "Pagi mas @Budi" terbaca "Pagi mas".
"""

from bs4 import BeautifulSoup, NavigableString

# Tag yang menutup satu baris. Isinya diberi baris baru di ujung supaya dua
# paragraf tidak menempel jadi satu kalimat.
TAG_BLOK = ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "tr")


def teks_sebutan(mention) -> str:
    """Teks pengganti satu `mention-component`.

    KEP-91: editor bisa menyebut orang, @all, #kanal, dan #work item. Nama kanal
    privat tidak pernah ditulis: email dan kartu bisa dibaca orang yang bukan
    anggotanya.
    """
    from plane.db.models import Issue, Ruang, User  # noqa: PLC0415
    from plane.utils.rujukan_obrolan import NAMA_PRIVAT, urai_uuid  # noqa: PLC0415

    jenis = mention.get("entity_name") or "user_mention"
    sah = urai_uuid([mention.get("entity_identifier")], 1)
    ident = sah[0] if sah else None

    if jenis == "everyone_mention":
        return "@all"
    if jenis == "channel_mention":
        ruang = Ruang.objects.filter(pk=ident).only("nama", "tipe").first() if ident else None
        if ruang is not None and ruang.tipe == Ruang.Tipe.KANAL and ruang.nama:
            return f"#{ruang.nama}"
        return f"#{NAMA_PRIVAT}"
    if jenis == "issue_mention":
        issue = Issue.objects.filter(pk=ident).select_related("project").first() if ident else None
        return f"{issue.project.identifier}-{issue.sequence_id}" if issue is not None else "#work-item"
    user = User.objects.filter(pk=ident).only("display_name").first() if ident else None
    return f"@{user.display_name}" if user is not None else "@unknown"


def _sup(html) -> BeautifulSoup:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for mention in soup.find_all("mention-component"):
        mention.replace_with(teks_sebutan(mention))
    return soup


def ganti_sebutan(html) -> str:
    """HTML yang sama, dengan tiap `mention-component` jadi teks sebutannya."""
    return str(_sup(html))


def teks_polos(html) -> str:
    """Teks tanpa tag: satu baris per paragraf, spasi dirapikan, baris kosong dibuang."""
    soup = _sup(html)
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for blok in soup.find_all(TAG_BLOK):
        blok.append(NavigableString("\n"))
    baris = (" ".join(b.split()) for b in soup.get_text().splitlines())
    return "\n".join(b for b in baris if b)
