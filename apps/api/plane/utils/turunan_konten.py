# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tautan & gambar dari deskripsi/komentar (KEP-88)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tautan dan gambar yang ditulis di deskripsi atau komentar ikut tampil di Links/Attachments.

Sengaja TIDAK disimpan sebagai baris IssueLink / FileAsset baru. Sumbernya tetap
teksnya: hapus tautan dari deskripsi = hilang dari Links, tanpa sinkronisasi yang
bisa tertinggal. Yang ditambahkan ke daftar adalah "turunan" berpenanda
`sumber` ("description" | "comment"); web menampilkannya hanya-baca, karena
menghapusnya dari daftar tidak akan menghapusnya dari teks.

Tautan yang URL-nya sama dengan link yang sudah ditambahkan manual tidak diulang.
"""

# Python imports
import re
import uuid
from typing import Any, Iterable, Optional

# Third party imports
from bs4 import BeautifulSoup, CData, Comment, NavigableString

# Module imports
from plane.db.models import FileAsset, Issue, IssueComment, IssueLink
from plane.utils.pratinjau_tautan import pratinjau_tersimpan

SUMBER_DESKRIPSI = "description"
SUMBER_KOMENTAR = "comment"
SUMBER_MANUAL = "link"
SUMBER_LAMPIRAN = "attachment"

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _sup(html: Optional[str]) -> Optional[BeautifulSoup]:
    if not html or not html.strip():
        return None
    return BeautifulSoup(html, "html.parser")


_URL_POLOS = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_TANPA_TAUTAN = {"a", "code", "pre", "script", "style"}
_PUNCT_AKHIR = ".,;:!?"


def _bersihkan_url(alamat: str) -> str:
    """Buang tanda baca penutup yang ikut tertangkap ("lihat https://x.id/a.", "(https://x.id)")."""
    alamat = alamat.rstrip(_PUNCT_AKHIR)
    while alamat.endswith(")") and alamat.count(")") > alamat.count("("):
        alamat = alamat[:-1].rstrip(_PUNCT_AKHIR)
    return alamat


def tautan_dari_html(html: Optional[str]) -> list[str]:
    """Alamat http(s) dari `<a href>` DAN URL polos di teks, urut kemunculan, tanpa duplikat.

    URL polos (belum diberi mark tautan oleh editor, mis. diketik di akhir baris tanpa
    spasi, ditempel sebagai teks, atau ditulis lewat API) ikut dihitung. Teks di dalam
    `<a>`, `<code>`, `<pre>` dilewati.
    """
    soup = _sup(html)
    if soup is None:
        return []
    hasil: list[str] = []

    def tambah(alamat: str) -> None:
        if alamat.lower().startswith(("http://", "https://")) and alamat not in hasil:
            hasil.append(alamat)

    for node in soup.descendants:
        if isinstance(node, NavigableString):
            if isinstance(node, (Comment, CData)):
                continue
            if any(p.name in _TANPA_TAUTAN for p in node.parents if p.name):
                continue
            for cocok in _URL_POLOS.finditer(str(node)):
                tambah(_bersihkan_url(cocok.group(0)))
        elif node.name == "a" and node.get("href"):
            tambah(node["href"].strip())
    return hasil


def aset_dari_html(html: Optional[str]) -> list[str]:
    """ID aset gambar dari `<image-component src>` (dan `<img src>` yang memuat ID aset)."""
    soup = _sup(html)
    if soup is None:
        return []
    hasil: list[str] = []
    for tag in soup.find_all(["image-component", "img"]):
        cocok = _UUID.search(tag.get("src") or "")
        if cocok and cocok.group(0).lower() not in hasil:
            hasil.append(cocok.group(0).lower())
    return hasil


def _komentar(issue_id) -> Iterable[IssueComment]:
    return (
        IssueComment.objects.filter(issue_id=issue_id)
        .only("id", "comment_html", "actor_id", "created_at", "updated_at")
        .order_by("created_at")
    )


def tautan_turunan(issue: Issue, url_manual: Iterable[str]) -> list[dict[str, Any]]:
    """Link turunan berbentuk sama dengan IssueLinkSerializer, plus `sumber` & `comment_id`."""
    sudah = set(url_manual)
    hasil: list[dict[str, Any]] = []

    def tambah(url: str, sumber: str, komentar: Optional[IssueComment]) -> None:
        if url in sudah:
            return
        sudah.add(url)
        kunci = f"{issue.id}|{sumber}|{komentar.id if komentar else ''}|{url}"
        kartu = pratinjau_tersimpan(url) or {}
        hasil.append(
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, kunci)),
                "url": url,
                "title": None,
                "metadata": {"title": kartu.get("title"), "favicon": kartu.get("favicon")},
                "issue": str(issue.id),
                "issue_id": str(issue.id),
                "project": str(issue.project_id),
                "workspace": str(issue.workspace_id),
                "created_by": str(komentar.actor_id) if komentar else None,
                "created_by_id": str(komentar.actor_id) if komentar else None,
                "created_at": (komentar.created_at if komentar else issue.updated_at),
                "updated_at": (komentar.updated_at if komentar else issue.updated_at),
                "sumber": sumber,
                "comment_id": str(komentar.id) if komentar else None,
            }
        )

    for url in tautan_dari_html(issue.description_html):
        tambah(url, SUMBER_DESKRIPSI, None)
    for komentar in _komentar(issue.id):
        for url in tautan_dari_html(komentar.comment_html):
            tambah(url, SUMBER_KOMENTAR, komentar)
    return hasil


def aset_turunan(issue: Issue) -> list[tuple[FileAsset, str]]:
    """Gambar deskripsi & komentar yang MASIH dirujuk teksnya, berpasangan dengan sumbernya.

    Aset yang sudah dibuang dari teks tidak ikut, walaupun barisnya belum terhapus.
    """
    di_deskripsi = aset_dari_html(issue.description_html)
    komentar = list(_komentar(issue.id))
    di_komentar = [aid for k in komentar for aid in aset_dari_html(k.comment_html)]
    if not di_deskripsi and not di_komentar:
        return []

    aset = FileAsset.objects.filter(
        id__in=di_deskripsi + di_komentar,
        workspace_id=issue.workspace_id,
        is_uploaded=True,
        entity_type__in=[
            FileAsset.EntityTypeContext.ISSUE_DESCRIPTION,
            FileAsset.EntityTypeContext.COMMENT_DESCRIPTION,
        ],
    ).select_related("workspace")
    id_komentar = {str(k.id) for k in komentar}
    hasil: list[tuple[FileAsset, str]] = []
    for a in aset:
        # Aset komentar harus milik komentar di work item INI, aset deskripsi milik
        # work item ini: ID yang ditempel dari work item lain tidak membuka berkasnya.
        if a.entity_type == FileAsset.EntityTypeContext.ISSUE_DESCRIPTION and str(a.issue_id) == str(issue.id):
            hasil.append((a, SUMBER_DESKRIPSI))
        elif a.entity_type == FileAsset.EntityTypeContext.COMMENT_DESCRIPTION and str(a.comment_id) in id_komentar:
            hasil.append((a, SUMBER_KOMENTAR))
    return hasil


def url_link_manual(links: Iterable[IssueLink]) -> list[str]:
    return [link.url for link in links]
