# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: rujukan #kanal dan #PRJ-12 (KEP-91)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Rujukan ke kanal dan work item di pesan obrolan dan editor teks kaya.

Satu tempat untuk tiga pertanyaan:

1. Kanal mana yang boleh dirujuk seseorang (`kanal_terlihat`). Kanal publik
   terlihat semua anggota workspace, kanal privat hanya oleh anggotanya. DM dan
   ruang kabar pribadi ("Paradise") tidak pernah bisa dirujuk.
2. Work item mana yang boleh dirujuk (`tugas_terlihat`): hanya dari project yang
   orang itu anggota aktifnya.
3. Apa yang boleh DIBACA penonton (`samarkan`). Pengirim boleh merujuk kanal
   privat yang ia ikuti, tapi pesannya bisa dibaca orang yang bukan anggota
   kanal itu. Nama kanal privat sudah membocorkan bahwa ada obrolan tertutup
   soal sesuatu (alasan yang sama dengan daftar kanal di ChatRuangEndpoint),
   jadi bagi mereka namanya diganti `#private-channel`.

Penyamaran dilakukan saat DIBACA, bukan saat disimpan: keanggotaan kanal bisa
berubah, dan orang yang baru diundang berhak melihat nama yang tadinya
tersembunyi.
"""

import re
import uuid

from django.db.models import Q

from plane.db.models import AWALAN_KABAR, Issue, Langganan, ProjectMember, Ruang

# Berapa rujukan per jenis yang disimpan di satu pesan. Lebih dari ini bukan
# rujukan lagi, cuma daftar.
BATAS_RUJUKAN = 20

# Nama pengganti kanal privat yang tidak boleh dilihat penonton.
NAMA_PRIVAT = "private-channel"


def urai_uuid(mentah, batas=BATAS_RUJUKAN) -> list:
    """Daftar UUID sah dari masukan peramban, urutan dipertahankan, tanpa kembar.

    Nilai yang bukan UUID dibuang diam-diam: peramban lama atau tempelan rusak
    tidak boleh menggagalkan pengiriman pesan.
    """
    if not isinstance(mentah, (list, tuple)):
        return []
    hasil = []
    for nilai in mentah:
        if len(hasil) >= batas:
            break
        try:
            u = uuid.UUID(str(nilai))
        except (TypeError, ValueError, AttributeError):
            continue
        if u not in hasil:
            hasil.append(u)
    return hasil


def kanal_terlihat_q(user_id) -> Q:
    """Syarat kanal yang boleh dilihat/dirujuk `user_id`: publik, atau ia anggotanya."""
    return Q(tipe=Ruang.Tipe.KANAL) | Q(id__in=Langganan.objects.filter(user_id=user_id).values("ruang_id"))


def kanal_terlihat(user_id, workspace_id):
    """Kanal di workspace ini yang boleh dirujuk `user_id`, tanpa DM dan ruang kabar."""
    return (
        Ruang.objects.filter(workspace_id=workspace_id)
        .exclude(tipe=Ruang.Tipe.DM)
        .exclude(kunci_sistem__startswith=AWALAN_KABAR)
        .filter(kanal_terlihat_q(user_id))
    )


def tugas_terlihat(user_id, workspace_id):
    """Work item di workspace ini dari project yang `user_id` anggota aktifnya."""
    project_saya = ProjectMember.objects.filter(workspace_id=workspace_id, member_id=user_id, is_active=True).values(
        "project_id"
    )
    return Issue.issue_objects.filter(workspace_id=workspace_id, project_id__in=project_saya)


def nomor_tugas(issue) -> str:
    """`PRJ-12`. Membaca `project.identifier`, jadi panggil dengan select_related."""
    return f"{issue.project.identifier}-{issue.sequence_id}"


def saring_kanal(user, workspace_id, ids) -> list:
    """Kanal yang benar-benar boleh dirujuk pengirim, urut seperti permintaan."""
    calon = urai_uuid(ids)
    if not calon:
        return []
    peta = {r.id: r for r in kanal_terlihat(user.id, workspace_id).filter(id__in=calon)}
    return [
        {"id": str(u), "nama": peta[u].nama or "", "privat": peta[u].tipe == Ruang.Tipe.PRIVAT}
        for u in calon
        if u in peta
    ]


def saring_tugas(user, workspace_id, ids) -> list:
    """Work item yang benar-benar boleh dirujuk pengirim, urut seperti permintaan."""
    calon = urai_uuid(ids)
    if not calon:
        return []
    peta = {i.id: i for i in tugas_terlihat(user.id, workspace_id).filter(id__in=calon).select_related("project")}
    return [
        {"id": str(u), "nomor": nomor_tugas(peta[u]), "project_id": str(peta[u].project_id)} for u in calon if u in peta
    ]


def samarkan_teks(isi, nama_list) -> str:
    """Ganti `#<nama>` yang berdiri sendiri dengan `#private-channel`.

    Berdiri sendiri = tidak didahului dan tidak diikuti huruf, angka, atau garis
    bawah (Unicode). Nama terpanjang dicocokkan lebih dulu, supaya `#sales-jkt`
    tidak tersisa `-jkt` karena `#sales` menang duluan. Huruf besar/kecil tidak
    dibedakan, sama dengan aturan nama kembar kanal.
    """
    if not isi:
        return isi or ""
    nama = sorted({n for n in nama_list if n}, key=len, reverse=True)
    if not nama:
        return isi
    pola = re.compile(r"(?<!\w)#(?:" + "|".join(re.escape(n) for n in nama) + r")(?!\w)", re.IGNORECASE)
    return pola.sub("#" + NAMA_PRIVAT, isi)


def _entri_kanal(muatan) -> list:
    kanal = (muatan or {}).get("kanal") if isinstance(muatan, dict) else None
    return [k for k in kanal if isinstance(k, dict) and k.get("id")] if isinstance(kanal, list) else []


def ada_kanal_privat(muatan) -> bool:
    return any(k.get("privat") for k in _entri_kanal(muatan))


def kanal_privat_milik(penonton_ids, muatan_list) -> dict:
    """{str(user_id): {str(ruang_id)}} kanal privat yang dirujuk dan diikuti penonton.

    SATU kueri untuk banyak penonton dan banyak pesan, untuk pemanggil massal
    (kartu sebutan, email). Hasilnya diumpankan ke `samarkan(..., boleh=...)`.
    """
    ruang_ids = {k["id"] for m in muatan_list for k in _entri_kanal(m) if k.get("privat")}
    penonton = [p for p in penonton_ids if p]
    hasil = {str(p): set() for p in penonton}
    if not ruang_ids or not penonton:
        return hasil
    for user_id, ruang_id in Langganan.objects.filter(user_id__in=penonton, ruang_id__in=ruang_ids).values_list(
        "user_id", "ruang_id"
    ):
        hasil.setdefault(str(user_id), set()).add(str(ruang_id))
    return hasil


def samarkan(isi, muatan, penonton_id, boleh=None):
    """(isi, muatan) sebagaimana boleh dibaca `penonton_id`.

    Tiap entri `muatan["kanal"]` mendapat `boleh`. Kanal privat yang penonton
    tidak ikuti (atau penonton tak dikenal) diganti `private-channel` di isi
    maupun di muatan, tanpa id-nya ikut terbuka namanya. `muatan` asli tidak
    diubah. `boleh` = himpunan id ruang privat yang diikuti penonton, kalau
    pemanggil sudah menghitungnya; kalau kosong dan perlu, ditanya ke database
    (hanya saat memang ada entri privat).
    """
    entri = _entri_kanal(muatan)
    if not entri:
        return isi, (dict(muatan) if isinstance(muatan, dict) else muatan)

    privat = [k for k in entri if k.get("privat")]
    if privat and boleh is None:
        if penonton_id is None:
            boleh = set()
        else:
            boleh = {
                str(r)
                for r in Langganan.objects.filter(
                    user_id=penonton_id, ruang_id__in=[k["id"] for k in privat]
                ).values_list("ruang_id", flat=True)
            }
    boleh = {str(b) for b in (boleh or set())}

    tersembunyi, kanal_baru = [], []
    for k in entri:
        if k.get("privat") and str(k["id"]) not in boleh:
            tersembunyi.append(k.get("nama") or "")
            kanal_baru.append({"id": k["id"], "nama": NAMA_PRIVAT, "privat": True, "boleh": False})
        else:
            kanal_baru.append({**k, "boleh": True})

    # Nama yang juga dipakai kanal yang TERLIHAT tidak disamarkan di teks: teks
    # tidak bisa membedakan keduanya, dan menyembunyikan yang sah lebih buruk.
    terlihat = {(k.get("nama") or "").lower() for k in kanal_baru if k["boleh"]}
    tersembunyi = [n for n in tersembunyi if n and n.lower() not in terlihat]

    return samarkan_teks(isi, tersembunyi) if tersembunyi else isi, {**muatan, "kanal": kanal_baru}
