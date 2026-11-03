# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi email pembaruan work item
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Merakit konteks `emails/notifications/issue-updates.html`. Murni kecuali foto profil.

Templat upstream punya cabang per kolom (state, priority, labels, ...) dalam
bahasa Inggris saja. Di sini semua kolom jadi baris "label: lama -> baru" yang
labelnya diterjemahkan, jadi templatnya tunggal dan kolom baru tidak butuh HTML baru.
"""

import re

from plane.utils.email_merek import avatar_untuk, render_email, tanggal
from plane.utils.email_teks import KOLOM, PRIORITAS, teks

# Nilainya HTML panjang, cukup disebut berubah.
KOLOM_TANPA_NILAI = {"description", "description_html"}
KOLOM_TANGGAL = {"target_date", "start_date"}
BATAS_NILAI = 3


def _rapikan(kolom, nilai, bahasa):
    daftar = [str(v) for v in (nilai or []) if v not in (None, "", "None")]
    if kolom in ("state", "priority", "name", "target_date", "start_date", "parent", "estimate_point"):
        daftar = daftar[-1:]
    if kolom == "priority":
        daftar = [PRIORITAS[bahasa].get(v, v) for v in daftar]
    if kolom in KOLOM_TANGGAL:
        daftar = [tanggal(v, bahasa, pendek=True) for v in daftar]
    lebih = len(daftar) - BATAS_NILAI
    hasil = ", ".join(daftar[:BATAS_NILAI])
    return f"{hasil} +{lebih}" if lebih > 0 else hasil


def baris_perubahan(changes, bahasa="id") -> list:
    """[{label, lama, baru}] dari {kolom: {old_value: [...], new_value: [...]}}."""
    label = KOLOM.get(bahasa, KOLOM["id"])
    kosong = teks("pembaruan", bahasa)["kosong"]
    hasil = []
    for kolom, nilai in (changes or {}).items():
        if not isinstance(nilai, dict):
            continue
        nama = label.get(kolom, kolom.replace("_", " "))
        if kolom in KOLOM_TANPA_NILAI:
            hasil.append({"label": nama, "lama": "", "baru": teks("pembaruan", bahasa)["diubah"]})
            continue
        lama = _rapikan(kolom, nilai.get("old_value"), bahasa)
        baru = _rapikan(kolom, nilai.get("new_value"), bahasa)
        if not lama and not baru:
            continue
        hasil.append({"label": nama, "lama": lama, "baru": baru or kosong})
    return hasil


_P_BUKA = re.compile(r"<p\b[^>]*>", re.I)
_P_ANTARA = re.compile(r"</p>\s*<p>", re.I)


def _rapikan_komentar(html) -> str:
    """Paragraf komentar tanpa margin bawaan klien; antar paragraf 8px.

    Outlook klasik memberi <p> tanpa gaya jarak dan sorotan latar dari gaya
    sekitarnya, Gmail memberi 1em. Komentar tampil di dalam komponen catatan
    yang paddingnya sudah mengatur ruang, jadi margin bawaan harus nol.
    """
    rapi = _P_ANTARA.sub("</p><p>", _P_BUKA.sub("<p>", str(html).strip()))
    potong = rapi.split("</p><p>")
    if len(potong) > 1:
        rapi = '</p><p style="margin:8px 0 0;">'.join(potong)
    return rapi.replace("<p>", '<p style="margin:0;">', 1)


def konteks_pembaruan(issue, aktor, bahasa="id", gambar=None) -> dict:
    """Konteks templat. `aktor` = [{user, waktu, changes, komentar: [html]}].

    `gambar` = daftar Gambar pesan; foto profil para aktor ditambahkan ke sana.
    """
    s = teks("pembaruan", bahasa)
    blok = []
    for a in aktor:
        av, _ = avatar_untuk(a.get("user"), nama=a.get("nama", ""), gambar=gambar)
        baris = baris_perubahan(a.get("changes"), bahasa)
        komentar = [_rapikan_komentar(k) for k in a.get("komentar") or [] if k]
        if baris or komentar:
            blok.append({"avatar": av, "waktu": a.get("waktu", ""), "baris": baris, "komentar": komentar})
    nama = blok[0]["avatar"]["nama"] if blok else ""
    jumlah = len(blok)
    judul_email = (
        teks("pembaruan", bahasa, aktor=nama)["judul_satu"]
        if jumlah <= 1
        else teks("pembaruan", bahasa, n=jumlah)["judul_banyak"]
    )
    return {"t": s, "issue": issue, "issue_url": issue.get("issue_url", ""), "perubahan": blok, "judul_email": judul_email}


def susun_email_pembaruan(issue, aktor, base_api, bahasa="id", email_penerima=""):
    """(subjek, html, teks, gambar) untuk satu work item. `issue` = model Issue."""
    slug = issue.project.workspace.slug
    kode = f"{issue.project.identifier}-{issue.sequence_id}"
    url = f"{base_api}/{slug}/projects/{issue.project.id}/issues/{issue.id}"
    gambar = []
    k = konteks_pembaruan({"issue_identifier": kode, "name": issue.name, "issue_url": url}, aktor, bahasa, gambar)
    html, polos = render_email(
        "emails/notifications/issue-updates.html",
        {
            **k,
            "judul": f"{kode} {issue.name}",
            "pratajuk": k["judul_email"],
            "alasan": k["t"]["alasan"],
            "url_preferensi": f"{base_api}/{slug}/settings/account/notifications/",
            "email_penerima": email_penerima,
        },
        bahasa,
    )
    return f"{kode} {issue.name}", html, polos, gambar
