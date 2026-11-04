# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: satu utas email per work item
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Header supaya semua email tentang satu work item tertumpuk dalam satu percakapan.

Saklar God Mode `ENABLE_EMAIL_THREADING`. Tiap work item punya id akar tetap
`<issue-{issue_id}@{domain}>`:

- email PERTAMA ke seseorang tentang work item itu memakai id akar sebagai
  `Message-ID`, subjek `[PROJ-12] Judul`;
- email berikutnya memakai `Message-ID` unik, `In-Reply-To` dan `References` ke
  id akar, subjek `Re: [PROJ-12] Judul`.

Gmail menumpuk pesan yang subjeknya sama (tanpa `Re:`) dan saling merujuk; Outlook
memakai subjek yang dinormalkan. Karena itu subjeknya harus TETAP: penanda peran
penerima ("Perlu persetujuanmu", "Pekerjaanmu disetujui") pindah ke pratajuk dan
judul isi email, bukan ke subjek.

"Pertama" dicatat per penerima di `EmailNotificationLog` (`entity="email_thread"`,
`processed_at` terisi, `sent_at` kosong supaya tidak ikut disapu `cleanup_task`).
Kenapa wajib tahan lama: Gmail membuang diam-diam pesan kedua yang `Message-ID`-nya
sudah pernah diterima. Jadi kalau ragu (kunci gagal, database galat), anggap
BUKAN yang pertama: balasan ke akar yang belum pernah datang tetap terkirim, cuma
mungkin tidak tertumpuk. Penanda ditulis SEBELUM pengiriman dengan alasan yang sama.
"""

import logging
from email.utils import make_msgid, parseaddr
from urllib.parse import urlparse

from django.db import connection, transaction
from django.utils import timezone

from plane.utils.saklar_instance import ENABLE_EMAIL_THREADING, saklar_aktif

logger = logging.getLogger("plane.worker")

ENTITY_UTAS = "email_thread"
DOMAIN_CADANGAN = "paradise.local"


def domain_pesan(dari: str = "", base_url: str = "") -> str:
    """Domain untuk id pesan: domain alamat pengirim, lalu host aplikasi, lalu cadangan."""
    alamat = parseaddr(dari or "")[1]
    if "@" in alamat:
        return alamat.rsplit("@", 1)[1].strip().lower() or DOMAIN_CADANGAN
    host = urlparse(base_url or "").hostname
    return host or DOMAIN_CADANGAN


def id_akar(issue_id, domain: str) -> str:
    return f"<issue-{issue_id}@{domain}>"


def subjek_utas(kode: str, judul: str, balasan: bool) -> str:
    dasar = f"[{kode}] {judul}"
    return f"Re: {dasar}" if balasan else dasar


def header_utas(issue_id, domain: str, pertama: bool) -> dict:
    """Murni. Header email untuk satu work item, pertama atau balasan."""
    akar = id_akar(issue_id, domain)
    if pertama:
        return {"Message-ID": akar}
    return {"Message-ID": make_msgid(domain=domain), "In-Reply-To": akar, "References": akar}


def utas_bersama(issue, orang, kunci, dari: str = "") -> list[tuple[list, tuple[str, dict] | None]]:
    """[(kelompok, utas)] untuk SATU email bersama ke beberapa orang tentang `issue`.

    Penanda "pertama" tetap per orang, jadi orang yang sudah pernah menerima akar
    utas dipisah dari yang belum: mengirim ulang `Message-ID` akar ke orang yang
    sudah memilikinya membuat Gmail membuang pesannya diam-diam. `kunci(user)`
    = pembeda isi lain (bahasa). Kelompok balasan memakai satu `Message-ID` unik
    untuk semua anggotanya, itu benar: pesannya memang satu.
    """
    from plane.utils.email_merek import kelompokkan_penerima

    per_orang = {o.id: utas_untuk(issue, o.id, dari=dari) for o in orang}

    def _kunci(o):
        utas = per_orang[o.id]
        return (kunci(o), None if utas is None else "In-Reply-To" not in utas[1])

    hasil = []
    for kelompok in kelompokkan_penerima(orang, _kunci):
        hasil.append((kelompok, per_orang[kelompok[0].id]))
    return hasil


def klaim_akar(receiver_id, issue_id, domain: str) -> bool:
    """True kalau ini email utas PERTAMA ke `receiver_id` tentang `issue_id` (lalu dicatat)."""
    from plane.db.models import EmailNotificationLog

    try:
        with transaction.atomic():
            # Kunci transaksi Postgres per (penerima, work item): dua worker yang
            # bersamaan tidak boleh sama-sama mengira dirinya yang pertama.
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [f"email-utas:{receiver_id}:{issue_id}"])
            sudah = EmailNotificationLog.all_objects.filter(
                entity=ENTITY_UTAS, receiver_id=receiver_id, entity_identifier=issue_id
            ).exists()
            if sudah:
                return False
            EmailNotificationLog.objects.create(
                receiver_id=receiver_id,
                triggered_by_id=receiver_id,
                entity_identifier=issue_id,
                entity_name="issue",
                entity=ENTITY_UTAS,
                data={"message_id": id_akar(issue_id, domain)},
                processed_at=timezone.now(),
            )
            return True
    except Exception:  # noqa: BLE001
        logger.exception("Penanda utas email gagal ditulis, dikirim sebagai balasan")
        return False


def utas_untuk(issue, receiver_id, dari: str = "", base_url: str = "") -> tuple[str, dict] | None:
    """(subjek, header) untuk email tentang `issue`, atau None kalau saklarnya mati."""
    if not saklar_aktif(ENABLE_EMAIL_THREADING):
        return None
    if not dari:
        from plane.license.utils.instance_value import get_email_configuration

        dari = get_email_configuration()[6] or ""
    if not base_url:
        from plane.utils.email_merek import base_url as _base_url

        base_url = _base_url()
    domain = domain_pesan(dari, base_url)
    pertama = klaim_akar(receiver_id, issue.id, domain)
    kode = f"{issue.project.identifier}-{issue.sequence_id}"
    return subjek_utas(kode, issue.name, balasan=not pertama), header_utas(issue.id, domain, pertama)
