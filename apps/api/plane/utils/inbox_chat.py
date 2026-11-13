# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pesan obrolan di inbox
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pesan langsung (DM) yang belum dibaca juga tampil di inbox (keputusan user 2026-11-02).

Satu baris per percakapan, BUKAN per pesan: selama barisnya belum dibaca, pesan
berikutnya dari ruang yang sama hanya menaikkan hitungan dan mengganti cuplikan.
Sepuluh balasan cepat tidak boleh jadi sepuluh baris inbox.

Hanya DM. Pesan kanal tidak ditulis ke inbox: satu pesan di kanal 40 orang akan
jadi 40 baris, dan kanal sudah punya lencana sendiri.

Baris ini sengaja TIDAK dihitung di `UnreadNotificationEndpoint`: obrolan sudah
punya lencana, pop-up, dan bunyi sendiri (penjaga.tsx). Ikut dihitung berarti
setiap pesan berbunyi dua kali.

Membuka percakapan menandai barisnya terbaca (`tandai_chat_terbaca`). Saklar
`inbox_chat` mati = tidak ada baris baru; baris lama tetap.

Semua fungsi menelan galatnya sendiri: kabar inbox tidak boleh menggagalkan
pengiriman pesan.
"""

import logging

from django.utils import timezone

logger = logging.getLogger("plane.worker")

ENTITY_CHAT = "chat"
SENDER_CHAT = "in_app:chat:dm"
BATAS_CUPLIKAN = 160


def _cuplikan(isi) -> str:
    rapi = " ".join((isi or "").split())
    return rapi if len(rapi) <= BATAS_CUPLIKAN else rapi[: BATAS_CUPLIKAN - 1] + "…"


def catat_pesan_dm(pesan) -> None:
    """Tulis atau perbarui baris inbox penerima untuk satu pesan DM yang baru terkirim."""
    from plane.db.models import Notification
    from plane.utils.preferensi_email import boleh

    try:
        penerima_id = pesan.penerima_id
        if penerima_id is None or penerima_id == pesan.pengirim_id or not boleh(penerima_id, "inbox_chat"):
            return
        from plane.utils.rujukan_obrolan import samarkan  # noqa: PLC0415

        # KEP-91: #kanal-privat yang tidak diikuti penerima disamarkan.
        teks, _ = samarkan(pesan.isi, pesan.muatan, penerima_id)
        cuplikan = _cuplikan(teks) or "📎"
        terbuka = Notification.objects.filter(
            receiver_id=penerima_id,
            entity_name=ENTITY_CHAT,
            entity_identifier=pesan.ruang_id,
            read_at__isnull=True,
            archived_at__isnull=True,
        ).first()
        jumlah = (((terbuka.data or {}).get("chat") or {}).get("jumlah") or 0) + 1 if terbuka else 1
        data = {
            "chat": {
                "ruang_id": str(pesan.ruang_id),
                "pengirim_id": str(pesan.pengirim_id),
                "jumlah": jumlah,
            },
            # Kartu inbox membaca `issue_activity.field` untuk memilih cara merender.
            "issue_activity": {
                "id": None,
                "verb": "message",
                "field": ENTITY_CHAT,
                "actor": str(pesan.pengirim_id),
                "new_value": cuplikan,
                "old_value": "",
                "new_identifier": None,
                "old_identifier": None,
            },
        }
        if terbuka:
            # created_at digeser supaya percakapan yang hidup naik ke atas inbox.
            Notification.objects.filter(pk=terbuka.pk).update(
                data=data, triggered_by_id=pesan.pengirim_id, created_at=timezone.now(), snoozed_till=None
            )
        else:
            Notification.objects.create(
                workspace_id=pesan.workspace_id,
                project=None,
                sender=SENDER_CHAT,
                triggered_by_id=pesan.pengirim_id,
                receiver_id=penerima_id,
                entity_identifier=pesan.ruang_id,
                entity_name=ENTITY_CHAT,
                title="",
                data=data,
            )
        # Daftar Pemberitahuan penerima menyegarkan diri; menelan galatnya sendiri.
        from plane.utils.sinyal_data import siarkan_notifikasi  # noqa: PLC0415

        siarkan_notifikasi(pesan.workspace_id, [penerima_id])
    except Exception:  # noqa: BLE001
        logger.exception("Gagal menulis inbox obrolan untuk pesan %s", getattr(pesan, "id", None))


def tandai_chat_terbaca(user_id, ruang_id) -> None:
    """Percakapan dibuka = baris inboxnya terbaca."""
    from plane.db.models import Notification

    try:
        Notification.objects.filter(
            receiver_id=user_id, entity_name=ENTITY_CHAT, entity_identifier=ruang_id, read_at__isnull=True
        ).update(read_at=timezone.now())
    except Exception:  # noqa: BLE001
        logger.exception("Gagal menandai inbox obrolan terbaca untuk ruang %s", ruang_id)
