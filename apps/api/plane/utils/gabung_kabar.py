# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kabar pembaruan yang sama digabung, bukan ditumpuk
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Gabungkan kabar pembaruan beruntun atas kolom yang sama menjadi satu.

Masalahnya: menggeser kartu Kanban dari To Do ke In Progress ke Review ke Done
menghasilkan empat notifikasi di aplikasi, empat kartu di obrolan, dan empat baris
di email. Penerima hanya perlu tahu keadaan akhirnya.

Aturan (berlaku untuk notifikasi aplikasi DAN antrean email):

* Hanya kolom BERNILAI TUNGGAL (`KOLOM_TUNGGAL`): status, prioritas, tanggal, judul,
  induk, estimasi. Kolom berdaftar (assignee, label, module, link, lampiran) dan
  komentar tidak digabung: tiap barisnya adalah fakta yang berbeda, bukan nilai
  yang ditimpa.
* Kunci gabungan: penerima + work item + pelaku + kolom. Orang lain yang mengubah
  kolom yang sama tetap kabar tersendiri.
* Jendela waktu = `EMAIL_BATCH_DELAY_MINUTES` (satu knob di God Mode). Hanya baris
  yang belum dibaca (notifikasi) atau belum diproses (email) yang digabung: yang
  sudah dilihat atau dikirim tidak ditulis ulang.
* Hasil gabungan memakai nilai LAMA dari baris pertama dan nilai BARU dari baris
  terakhir. Kalau keduanya sama (A -> B -> A), tidak ada yang berubah: barisnya
  dibuang dan tidak ada kabar sama sekali.
"""

from datetime import timedelta

from django.utils import timezone

from plane.utils.saklar_instance import EMAIL_BATCH_DELAY_MINUTES, setelan_angka

KOLOM_TUNGGAL = frozenset({"state", "priority", "target_date", "start_date", "name", "parent", "estimate_point"})
SENDER_PEMBARUAN = frozenset(
    {
        "in_app:issue_activities:created",
        "in_app:issue_activities:assigned",
        "in_app:issue_activities:subscribed",
    }
)


def _aktivitas(baris) -> dict:
    return ((baris.data or {}).get("issue_activity")) or {}


def kolom_tunggal(baris) -> str | None:
    """Nama kolom kalau `baris` kabar perubahan kolom bernilai tunggal, selain itu None."""
    kolom = str(_aktivitas(baris).get("field") or "")
    return kolom if kolom in KOLOM_TUNGGAL else None


def _kunci(baris) -> tuple | None:
    kolom = kolom_tunggal(baris)
    # `entity` terisi = baris khusus (persetujuan, utas email): jangan disentuh.
    if kolom is None or not baris.entity_identifier or getattr(baris, "entity", ""):
        return None
    return (str(baris.receiver_id), str(baris.entity_identifier), str(baris.triggered_by_id), kolom)


def _lama(a: dict):
    return a.get("old_identifier") if a.get("old_identifier") is not None else a.get("old_value")


def _baru(a: dict):
    return a.get("new_identifier") if a.get("new_identifier") is not None else a.get("new_value")


def _sama(a: dict, b: dict) -> bool:
    return str(_lama(a)) == str(_baru(b))


def _lipat(lama, baru):
    """Muatan `baru` dengan nilai lama dari `lama`. Mengembalikan salinan data `baru`."""
    data = dict(baru.data or {})
    aktivitas = dict(data.get("issue_activity") or {})
    asal = _aktivitas(lama)
    aktivitas["old_value"] = asal.get("old_value")
    aktivitas["old_identifier"] = asal.get("old_identifier")
    data["issue_activity"] = aktivitas
    return data


def gabungkan(baru: list, model, sudah_ada, *, jendela_menit: int | None = None) -> list:
    """Lipat `baru` ke baris yang SUDAH ADA di database, kembalikan yang masih harus disimpan.

    * `baru`: objek `model` belum tersimpan, urut waktu.
    * `sudah_ada(baris)`: queryset baris tersimpan yang boleh digabung dengan `baris`
      (sudah dibatasi belum dibaca / belum diproses oleh pemanggil).
    * Baris yang digabung ke baris tersimpan diperbarui di tempat; yang berbalik
      ke nilai awal membuat baris tersimpan itu dihapus.

    Baris `baru` yang saling bertabrakan di dalam daftar yang sama juga dilipat.
    """
    menit = setelan_angka(EMAIL_BATCH_DELAY_MINUTES) if jendela_menit is None else jendela_menit
    batas = timezone.now() - timedelta(minutes=menit)
    disimpan = []
    di_daftar: dict[tuple, object] = {}

    for baris in baru:
        kunci = _kunci(baris)
        if kunci is None:
            disimpan.append(baris)
            continue

        # 1. Tabrakan dengan baris lain di daftar yang sama.
        sebelumnya = di_daftar.get(kunci)
        if sebelumnya is not None:
            if _sama(_aktivitas(sebelumnya), _aktivitas(baris)):
                disimpan.remove(sebelumnya)
                del di_daftar[kunci]
            else:
                sebelumnya.data = _lipat(sebelumnya, baris)
                if hasattr(baris, "title"):
                    sebelumnya.title = baris.title
            continue

        # 2. Tabrakan dengan baris yang sudah tersimpan.
        lama = (
            sudah_ada(baris)
            .filter(created_at__gte=batas, data__issue_activity__field=kolom_tunggal(baris))
            .order_by("-created_at")
            .first()
        )
        if lama is not None:
            if _sama(_aktivitas(lama), _aktivitas(baris)):
                lama.delete()
            else:
                lama.data = _lipat(lama, baris)
                perbarui = ["data", "updated_at"]
                if hasattr(baris, "title"):
                    lama.title = baris.title
                    perbarui.append("title")
                lama.save(update_fields=perbarui)
            continue

        disimpan.append(baris)
        di_daftar[kunci] = baris
    return disimpan


def gabungkan_notifikasi(baru: list) -> list:
    """`gabungkan` untuk `Notification` pembaruan work item yang belum dibaca."""
    from plane.db.models import Notification  # noqa: PLC0415

    kandidat = [b for b in baru if b.sender in SENDER_PEMBARUAN and (b.entity_name or "") == "issue"]
    lain = [b for b in baru if b not in kandidat]

    def sudah_ada(baris):
        return Notification.objects.filter(
            receiver_id=baris.receiver_id,
            entity_identifier=baris.entity_identifier,
            entity_name="issue",
            triggered_by_id=baris.triggered_by_id,
            sender__in=SENDER_PEMBARUAN,
            read_at__isnull=True,
            archived_at__isnull=True,
        )

    # Urutan relatif tetap: yang digabung kembali ke daftar sesudah yang lain.
    return lain + gabungkan(kandidat, Notification, sudah_ada)


def gabungkan_email(baru: list) -> list:
    """`gabungkan` untuk antrean email pembaruan work item yang belum diproses."""
    from plane.db.models import EmailNotificationLog  # noqa: PLC0415

    def sudah_ada(baris):
        return EmailNotificationLog.objects.filter(
            receiver_id=baris.receiver_id,
            entity_identifier=baris.entity_identifier,
            entity_name="issue",
            triggered_by_id=baris.triggered_by_id,
            processed_at__isnull=True,
        )

    return gabungkan(baru, EmailNotificationLog, sudah_ada)
