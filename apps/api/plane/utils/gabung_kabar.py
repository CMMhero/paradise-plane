# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kabar pembaruan beruntun dilebur jadi satu
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Lebur kabar pembaruan beruntun dari satu pelaku atas satu work item jadi satu kabar.

Masalahnya: menyunting work item (status, prioritas, label, assignee, module,
beberapa komentar beruntun) menghasilkan satu baris inbox, satu kartu obrolan,
dan satu baris email PER aktivitas. Penerima cukup tahu ringkasannya.

## Dua mode

* **Lebur penuh** (`ENABLE_EMAIL_BATCH` menyala, bawaan): semua kabar pembaruan
  dari pelaku yang sama atas work item yang sama untuk penerima yang sama, di
  dalam satu jendela, jadi SATU baris `Notification`. Kolom bernilai tunggal
  disimpan lama -> baru, kolom berdaftar (label, assignee, module, link,
  lampiran, relasi) disimpan sebagai tambah/hapus per butir, komentar dihitung.
* **Lebur sekolom** (saklar mati, perilaku sebelum 2026-11-17): hanya perubahan
  beruntun atas kolom bernilai tunggal YANG SAMA yang dilipat. Antrean email
  selalu memakai mode ini, karena email sudah dikumpulkan per penerima oleh
  `email_antrean` dan perakitnya membaca satu aktivitas per baris.

## Jendela

`EMAIL_BATCH_DELAY_MINUTES` (satu knob God Mode), dihitung dari kabar PERTAMA
(`created_at` baris tidak digeser). Pelaku yang terus menyunting tetap
menghasilkan kabar baru paling lambat sekali per jendela, bukan satu baris yang
tertahan tanpa akhir. Hanya baris yang belum dibaca, belum diarsipkan, dan
tidak sedang ditunda (snooze) yang menjadi tujuan lebur: yang sudah dilihat
orang tidak ditulis ulang.

## Yang TIDAK dilebur (tetap kabar tersendiri dan seketika)

* sebutan (`:mentioned`): ditujukan ke orang itu, bukan kabar umum;
* penugasan ke penerima sendiri (`assignees` dengan `new_identifier` = penerima)
  dan tugas baru (`field` "None"): orangnya harus tahu sekarang, dan kartu/email
  "tugas baru" punya jalurnya sendiri (`tugas_ke_dm_task`, `penugasan_email`);
* balasan atas komentar penerima (`JUDUL_BALASAN`): percakapan langsung;
* baris ber-`entity` (persetujuan, utas email) dan sender lain (tenggat, obrolan).

## Urutan, ganda, dan pembatalan

* Nilai LAMA kolom tunggal diambil dari aktivitas paling AWAL, nilai BARU dari
  yang paling AKHIR menurut `activity_time`, bukan urutan tiba. Tugas Celery
  yang selesai terbalik tidak membalik hasilnya.
* Id aktivitas dicatat: aktivitas yang sama yang datang dua kali (pesan dikirim
  ulang broker) tidak dihitung dua kali.
* A -> B -> A membatalkan HANYA kolom itu. Tambah lalu hapus label yang sama
  saling meniadakan; komentar yang dibuat lalu dihapus di jendela yang sama
  juga. Kalau semuanya batal, barisnya dihapus.

Fungsi `lipat`, `keadaan_dari`, dan `terapkan` murni (tanpa database) dan diuji
langsung; `gabungkan*` adalah lapisan database di atasnya.
"""

import hashlib
import logging
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timedelta

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from plane.utils.saklar_instance import EMAIL_BATCH_DELAY_MINUTES, setelan_angka

logger = logging.getLogger("plane.worker")

KOLOM_TUNGGAL = frozenset({"state", "priority", "target_date", "start_date", "name", "parent", "estimate_point"})
SENDER_PEMBARUAN = frozenset(
    {
        "in_app:issue_activities:created",
        "in_app:issue_activities:assigned",
        "in_app:issue_activities:subscribed",
    }
)
# Judul baris kabar balasan komentar (notification_task). Dipakai sebagai penanda.
JUDUL_BALASAN = "replied to your comment"
KOLOM_KOMENTAR = "comment"
# Kolom yang selalu kabar tersendiri. "None" = tugas baru (str(None) di muatan).
KOLOM_LANGSUNG = frozenset({"None", "approval", "deadline", "chat", "mention", "description"})
# Batas id aktivitas yang diingat per baris (penangkal hitung ganda).
BATAS_ID = 200


# ---------------------------------------------------------------- pembantu murni


def _aktivitas(baris) -> dict:
    return ((getattr(baris, "data", None) or {}).get("issue_activity")) or {}


def kolom_tunggal(baris) -> str | None:
    """Nama kolom kalau `baris` kabar perubahan kolom bernilai tunggal, selain itu None."""
    kolom = str(_aktivitas(baris).get("field") or "")
    return kolom if kolom in KOLOM_TUNGGAL else None


def boleh_dilebur(baris) -> bool:
    """True kalau `baris` kabar pembaruan biasa yang boleh dilebur dengan kabar lain.

    Tidak memeriksa `sender`: itu tugas pemanggil (`gabungkan_notifikasi`), karena
    baris email tidak punya sender.
    """
    if getattr(baris, "entity", "") or not getattr(baris, "entity_identifier", None):
        return False
    a = _aktivitas(baris)
    kolom = str(a.get("field") or "")
    if not kolom or kolom in KOLOM_LANGSUNG:
        return False
    if kolom == "assignees" and a.get("new_identifier") and str(a.get("new_identifier")) == str(baris.receiver_id):
        return False
    return (getattr(baris, "title", "") or "") != JUDUL_BALASAN


def _kunci(baris, semua: bool) -> tuple | None:
    """Kunci lebur. Lebur penuh: penerima + work item + pelaku; sekolom: + kolom."""
    if semua:
        if not boleh_dilebur(baris):
            return None
        return (str(baris.receiver_id), str(baris.entity_identifier), str(baris.triggered_by_id))
    kolom = kolom_tunggal(baris)
    # `entity` terisi = baris khusus (persetujuan, utas email): jangan disentuh.
    if kolom is None or not baris.entity_identifier or getattr(baris, "entity", ""):
        return None
    return (str(baris.receiver_id), str(baris.entity_identifier), str(baris.triggered_by_id), kolom)


def _waktu(a: dict) -> float | None:
    nilai = a.get("activity_time")
    if not nilai:
        return None
    try:
        return datetime.fromisoformat(str(nilai).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _lebih_baru(t_baru, t_lama) -> bool:
    """`t_baru` datang sesudah `t_lama`? Tanpa waktu, urutan tiba yang dipakai."""
    if t_baru is None or t_lama is None:
        return True
    return t_baru >= t_lama


def _lebih_awal(t_baru, t_lama) -> bool:
    return t_baru is not None and t_lama is not None and t_baru < t_lama


def _kosong(nilai) -> bool:
    return nilai is None or str(nilai) in ("", "None")


def _nilai(a: dict, sisi: str):
    """Pembanding satu sisi: identifier kalau ada, selain itu nilai teksnya."""
    ident = a.get(f"{sisi}_identifier")
    return str(ident) if not _kosong(ident) else str(a.get(f"{sisi}_value") or "")


def _butir(a: dict) -> tuple[str, str, str]:
    """(arah, kunci, label) untuk satu aktivitas kolom berdaftar. Arah: tambah|hapus|lain."""
    kolom = str(a.get("field") or "")
    verb = str(a.get("verb") or "")
    if kolom == KOLOM_KOMENTAR:
        kunci = str(a.get("issue_comment_id") or a.get("new_identifier") or a.get("id") or "")
        label = str(a.get("new_value") or "")
        arah = {"created": "tambah", "deleted": "hapus"}.get(verb, "lain")
        return arah, kunci, label
    lama, baru = a.get("old_value"), a.get("new_value")
    if not _kosong(baru) and _kosong(lama):
        return "tambah", _nilai(a, "new"), str(baru)
    if not _kosong(lama) and _kosong(baru):
        return "hapus", _nilai(a, "old"), str(lama)
    return "lain", "", str(baru or "")


def _keadaan_kosong() -> dict:
    return {"jumlah": 0, "ids": [], "urutan": [], "tunggal": {}, "daftar": {}, "terakhir": {}}


def lipat(keadaan: dict, aktivitas: dict, judul: str | None = None) -> dict:
    """Lipat satu `issue_activity` ke `keadaan`. Murni: mengembalikan salinan baru."""
    k = {
        "jumlah": keadaan.get("jumlah", 0),
        "ids": list(keadaan.get("ids") or []),
        "urutan": list(keadaan.get("urutan") or []),
        "tunggal": {f: dict(v) for f, v in (keadaan.get("tunggal") or {}).items()},
        "daftar": {
            f: {"tambah": dict(v.get("tambah") or {}), "hapus": dict(v.get("hapus") or {}), "lain": v.get("lain", 0)}
            for f, v in (keadaan.get("daftar") or {}).items()
        },
        "terakhir": {f: dict(v) for f, v in (keadaan.get("terakhir") or {}).items()},
    }
    ident = "" if _kosong(aktivitas.get("id")) else str(aktivitas.get("id"))
    if ident and ident in k["ids"]:
        return k  # aktivitas yang sama datang dua kali (dikirim ulang broker): abaikan
    if ident:
        k["ids"] = (k["ids"] + [ident])[-BATAS_ID:]
    k["jumlah"] += 1

    kolom = str(aktivitas.get("field") or "")
    if kolom not in k["urutan"]:
        k["urutan"].append(kolom)
    t = _waktu(aktivitas)

    if kolom in KOLOM_TUNGGAL:
        isi = k["tunggal"].get(kolom)
        if isi is None:
            k["tunggal"][kolom] = {
                "old_value": aktivitas.get("old_value"),
                "old_identifier": aktivitas.get("old_identifier"),
                "new_value": aktivitas.get("new_value"),
                "new_identifier": aktivitas.get("new_identifier"),
                "t_lama": t,
                "t_baru": t,
            }
        else:
            if _lebih_awal(t, isi.get("t_lama")):
                isi.update(
                    old_value=aktivitas.get("old_value"), old_identifier=aktivitas.get("old_identifier"), t_lama=t
                )
            if _lebih_baru(t, isi.get("t_baru")):
                isi.update(
                    new_value=aktivitas.get("new_value"), new_identifier=aktivitas.get("new_identifier"), t_baru=t
                )
    else:
        isi = k["daftar"].setdefault(kolom, {"tambah": {}, "hapus": {}, "lain": 0})
        arah, kunci, label = _butir(aktivitas)
        if arah == "tambah":
            if kunci in isi["hapus"]:
                del isi["hapus"][kunci]
            else:
                isi["tambah"][kunci] = label
        elif arah == "hapus":
            if kunci in isi["tambah"]:
                del isi["tambah"][kunci]
            else:
                isi["hapus"][kunci] = label
        elif kolom == KOLOM_KOMENTAR and kunci in isi["tambah"]:
            isi["tambah"][kunci] = label  # komentar baru yang disunting: teksnya saja
        else:
            isi["lain"] += 1

    lalu = k["terakhir"].get(kolom)
    if lalu is None or _lebih_baru(t, lalu.get("t")):
        k["terakhir"][kolom] = {"aktivitas": dict(aktivitas), "judul": judul, "t": t, "n": k["jumlah"]}
    return k


def keadaan_dari(baris) -> dict:
    """Keadaan lebur sebuah baris: yang tersimpan, atau dibangun dari aktivitas tunggalnya."""
    tersimpan = ((getattr(baris, "data", None) or {}).get("gabungan") or {}).get("keadaan")
    if tersimpan:
        return tersimpan
    return lipat(_keadaan_kosong(), _aktivitas(baris), getattr(baris, "title", None))


def _hidup(k: dict, kolom: str) -> bool:
    if kolom in k["tunggal"]:
        isi = k["tunggal"][kolom]
        return _nilai(isi, "old") != _nilai(isi, "new")
    isi = k["daftar"].get(kolom)
    return bool(isi and (isi["tambah"] or isi["hapus"] or isi["lain"]))


def kolom_hidup(k: dict) -> list:
    """Kolom yang masih berubah sesudah pembatalan, urut kemunculan pertama."""
    return [f for f in k.get("urutan") or [] if _hidup(k, f)]


def ringkasan(k: dict) -> dict:
    """Bagian `data["gabungan"]` yang dibaca web dan kartu obrolan."""
    hidup = kolom_hidup(k)
    perubahan = []
    for f in hidup:
        if f == KOLOM_KOMENTAR:
            continue
        if f in k["tunggal"]:
            isi = k["tunggal"][f]
            perubahan.append(
                {"field": f, "lama": str(isi.get("old_value") or ""), "baru": str(isi.get("new_value") or "")}
            )
        else:
            isi = k["daftar"][f]
            perubahan.append({"field": f, "tambah": list(isi["tambah"].values()), "hapus": list(isi["hapus"].values())})
    komentar = len(((k["daftar"].get(KOLOM_KOMENTAR) or {}).get("tambah")) or {})
    return {"jumlah": k["jumlah"], "komentar": komentar, "perubahan": perubahan, "keadaan": k}


def terapkan(baris, k: dict) -> bool:
    """Tulis keadaan `k` ke `baris` (di memori). False = semuanya batal, baris harus dibuang.

    `issue_activity` tetap diisi aktivitas TERAKHIR dari kolom yang masih hidup,
    dengan lama -> baru hasil lebur, supaya pembaca lama (web, email, kartu) yang
    hanya mengenal satu aktivitas tetap benar untuk kasus satu kolom.
    """
    hidup = kolom_hidup(k)
    if not hidup:
        return False
    utama = max(hidup, key=lambda f: (k["terakhir"][f].get("t") or 0, k["terakhir"][f].get("n") or 0))
    aktivitas = dict(k["terakhir"][utama]["aktivitas"])
    if utama in k["tunggal"]:
        isi = k["tunggal"][utama]
        for kunci in ("old_value", "old_identifier", "new_value", "new_identifier"):
            aktivitas[kunci] = isi.get(kunci)
    data = dict(getattr(baris, "data", None) or {})
    data["issue_activity"] = aktivitas
    if k["jumlah"] > 1:
        data["gabungan"] = ringkasan(k)
    baris.data = data
    if hasattr(baris, "title"):
        judul = [k["terakhir"][f].get("judul") for f in hidup if f != KOLOM_KOMENTAR]
        judul = [j for j in judul if j]
        baris.title = "; ".join(judul) if judul else k["terakhir"][utama].get("judul")
    return True


# ---------------------------------------------------------------- lapisan database


@dataclass
class HasilGabung:
    """`baru`: harus disimpan; `diperbarui`: baris tersimpan yang diubah di tempat;
    `dihapus`: baris tersimpan yang dibuang karena semua perubahannya batal."""

    baru: list = dc_field(default_factory=list)
    diperbarui: list = dc_field(default_factory=list)
    dihapus: list = dc_field(default_factory=list)


def kunci_gabungan(issue_id, actor_id) -> None:
    """Serialkan lebur untuk satu (work item, pelaku) sampai transaksi selesai.

    Dua tugas notifikasi untuk work item dan pelaku yang sama yang berjalan
    bersamaan akan sama-sama tidak menemukan baris lalu sama-sama membuat baris
    baru, atau menimpa lebur satu sama lain. Kunci advisory transaksi Postgres
    dilepas sendiri saat commit/rollback, juga saat worker mati (koneksinya
    putus). Wajib dipanggil di dalam `transaction.atomic()`.
    """
    if connection.vendor != "postgresql":
        return
    angka = int.from_bytes(
        hashlib.blake2b(f"gabung-kabar:{issue_id}:{actor_id}".encode(), digest_size=8).digest(), "big", signed=True
    )
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", [angka])


def gabungkan_rinci(baru: list, sudah_ada, *, semua: bool, jendela_menit: int | None = None) -> HasilGabung:
    """Lebur `baru` (objek belum tersimpan, urut waktu) dengan sesamanya dan dengan baris tersimpan.

    `sudah_ada(baris)`: queryset baris tersimpan yang boleh jadi tujuan lebur
    (sudah dibatasi belum dibaca / belum diproses oleh pemanggil).
    """
    menit = setelan_angka(EMAIL_BATCH_DELAY_MINUTES) if jendela_menit is None else jendela_menit
    batas = timezone.now() - timedelta(minutes=menit)
    hasil = HasilGabung()
    urut_baru: list = []
    # kunci -> [objek tujuan, keadaan, tersimpan?]
    tujuan: dict[tuple, list] = {}

    with transaction.atomic():
        for baris in baru:
            kunci = _kunci(baris, semua)
            if kunci is None:
                urut_baru.append(baris)
                continue
            aktivitas = _aktivitas(baris)
            judul = getattr(baris, "title", None)

            # 1. Kunci yang sudah punya tujuan di gelombang ini (baru atau tersimpan).
            if kunci in tujuan:
                tujuan[kunci][1] = lipat(tujuan[kunci][1], aktivitas, judul)
                continue

            # 2. Baris tersimpan di dalam jendela, dikunci baris supaya tidak ditimpa.
            kueri = sudah_ada(baris).filter(created_at__gte=batas)
            if not semua:
                kueri = kueri.filter(data__issue_activity__field=kolom_tunggal(baris))
            lama = next(
                (b for b in kueri.select_for_update().order_by("-created_at")[:10] if (_kunci(b, semua) == kunci)),
                None,
            )
            if lama is not None:
                tujuan[kunci] = [lama, lipat(keadaan_dari(lama), aktivitas, judul), True]
                continue

            # 3. Tidak ada: baris ini jadi tujuan baru.
            tujuan[kunci] = [baris, keadaan_dari(baris), False]
            urut_baru.append(baris)

        for objek, keadaan, tersimpan in tujuan.values():
            hidup = terapkan(objek, keadaan) if keadaan["jumlah"] > 1 or tersimpan else True
            if tersimpan:
                if hidup:
                    perbarui = ["data", "updated_at"] + (["title"] if hasattr(objek, "title") else [])
                    objek.save(update_fields=perbarui)
                    hasil.diperbarui.append(objek)
                else:
                    objek.delete()
                    hasil.dihapus.append(objek)
            elif not hidup:
                urut_baru.remove(objek)

    hasil.baru = urut_baru
    return hasil


def gabungkan(baru: list, model, sudah_ada, *, jendela_menit: int | None = None, semua: bool = False) -> list:
    """Bentuk lama: hanya daftar yang masih harus disimpan. `model` tidak dipakai lagi."""
    return gabungkan_rinci(baru, sudah_ada, semua=semua, jendela_menit=jendela_menit).baru


def lebur_penuh_aktif() -> bool:
    """Lebur penuh mengikuti saklar `ENABLE_EMAIL_BATCH` (satu saklar untuk kabar terkumpul)."""
    from plane.utils.saklar_instance import ENABLE_EMAIL_BATCH, saklar_aktif  # noqa: PLC0415

    try:
        return saklar_aktif(ENABLE_EMAIL_BATCH)
    except Exception:  # noqa: BLE001
        return True


def gabungkan_notifikasi_rinci(baru: list, *, semua: bool | None = None) -> HasilGabung:
    """`gabungkan_rinci` untuk `Notification` pembaruan work item yang belum dibaca."""
    from plane.db.models import Notification  # noqa: PLC0415

    semua = lebur_penuh_aktif() if semua is None else semua
    kandidat = [b for b in baru if b.sender in SENDER_PEMBARUAN and (b.entity_name or "") == "issue"]
    lain = [b for b in baru if b not in kandidat]
    sekarang = timezone.now()

    def sudah_ada(baris):
        return Notification.objects.filter(
            Q(snoozed_till__isnull=True) | Q(snoozed_till__lte=sekarang),
            receiver_id=baris.receiver_id,
            entity_identifier=baris.entity_identifier,
            entity_name="issue",
            triggered_by_id=baris.triggered_by_id,
            sender__in=SENDER_PEMBARUAN,
            read_at__isnull=True,
            archived_at__isnull=True,
        )

    hasil = gabungkan_rinci(kandidat, sudah_ada, semua=semua)
    # Urutan relatif tetap: yang dilebur kembali ke daftar sesudah yang lain.
    hasil.baru = lain + hasil.baru
    if hasil.diperbarui or hasil.dihapus or len(hasil.baru) < len(baru):
        contoh = baru[0] if baru else None
        logger.info(
            "gabung-kabar: mode=%s masuk=%d baru=%d dilebur=%d dihapus=%d issue=%s pelaku=%s",
            "penuh" if semua else "sekolom",
            len(baru),
            len(hasil.baru),
            len(hasil.diperbarui),
            len(hasil.dihapus),
            getattr(contoh, "entity_identifier", None),
            getattr(contoh, "triggered_by_id", None),
        )
    return hasil


def gabungkan_notifikasi(baru: list, *, semua: bool | None = None) -> list:
    """Bentuk lama `gabungkan_notifikasi_rinci`: hanya daftar yang masih harus disimpan."""
    return gabungkan_notifikasi_rinci(baru, semua=semua).baru


def gabungkan_email(baru: list) -> list:
    """Lebur sekolom untuk antrean email pembaruan work item yang belum diproses.

    Sengaja tidak lebur penuh: `email_antrean` sudah merakit SATU email per
    penerima per jendela dari semua barisnya, dan perakitnya (`create_payload`)
    membaca satu aktivitas per baris.
    """
    from plane.db.models import EmailNotificationLog  # noqa: PLC0415

    def sudah_ada(baris):
        return EmailNotificationLog.objects.filter(
            receiver_id=baris.receiver_id,
            entity_identifier=baris.entity_identifier,
            entity_name="issue",
            triggered_by_id=baris.triggered_by_id,
            processed_at__isnull=True,
        )

    return gabungkan_rinci(baru, sudah_ada, semua=False).baru
