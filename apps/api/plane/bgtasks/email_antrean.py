# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email kabar kerja dikumpulkan per penerima
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu email per penerima per jendela, bukan satu email per kejadian.

Saklar God Mode `ENABLE_EMAIL_BATCH` + angka `EMAIL_BATCH_DELAY_MINUTES`. Antreannya
tetap `EmailNotificationLog` milik upstream (ditulis `notification_task` untuk
pembaruan/komentar/penyebutan dan `notifikasi_persetujuan` untuk persetujuan), dan
penyapunya tetap `stack_email_notification` tiap 5 menit. Yang berubah hanya cara
menyapu:

1. Penerima JATUH TEMPO kalau kabar tertua yang belum diproses sudah berumur
   >= jeda. Jendelanya per orang dan dihitung dari kabar pertama, jadi orang yang
   terus menerima kabar tetap dikirimi paling lambat jeda + 5 menit sesudah kabar
   pertamanya, bukan ditunda tanpa akhir.
2. Semua baris penerima itu DIKLAIM dalam satu transaksi (`select_for_update`
   skip_locked, lalu `processed_at` diisi). Penyapuan kedua, atau worker kedua
   yang berjalan bersamaan, tidak melihat baris yang sama: tidak ada email ganda.
3. Satu email dirakit dari baris-baris itu, urut `created_at`. Pengajuan
   persetujuan yang menunggu keputusan penerima tampil paling atas, terpisah.
4. Terkirim: `sent_at` diisi. Gagal karena SMTP putus/timeout: klaimnya dilepas
   (`processed_at` dikosongkan) supaya dicoba lagi di putaran berikutnya. Gagal
   karena alamat ditolak atau galat lain: tetap diproses dan dicatat di log,
   supaya satu alamat rusak tidak mengulang dirinya tiap 5 menit selamanya.

Batas yang disengaja: kalau worker mati TEPAT di antara klaim dan pengiriman,
baris itu tercatat diproses tanpa terkirim (inbox tetap ada). Itu pilihan
"paling banyak sekali": kebalikannya (kirim dulu, tandai belakangan) berarti
email ganda tiap kali worker mati sesudah SMTP menerima pesan.

Bentuk email:
- satu baris persetujuan saja: email persetujuan biasa;
- hanya pembaruan, satu work item: email pembaruan biasa;
- selain itu: email ringkasan (`susun_ringkasan`).
Kalau isinya tentang SATU work item, email ikut utas work item itu
(`ENABLE_EMAIL_THREADING`). Ringkasan banyak work item tidak bisa masuk utas mana
pun, jadi dikirim sebagai pesan berdiri sendiri. Sengaja tidak dipecah jadi satu
email per work item: tujuannya mengurangi jumlah email, dan dalam jendela 15 menit
kebanyakan orang hanya menerima kabar tentang satu work item, jadi utasnya tetap
terbentuk untuk kasus yang paling sering.
"""

import logging
import smtplib
from datetime import timedelta
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from celery import shared_task
from django.db import transaction
from django.db.models import Min
from django.utils import timezone

from plane.db.models import EmailNotificationLog, Issue
from plane.utils.email_merek import (
    UKURAN,
    WARNA,
    bahasa_penerima,
    base_url,
    buat_pesan,
    bungkus,
    judul_bagian,
    judul_html,
    kartu,
    paragraf,
    tombol,
    url_preferensi,
)
from plane.utils.email_pembaruan import baris_perubahan
from plane.utils.email_utas import ENTITY_UTAS, utas_untuk
from plane.utils.exception_logger import log_exception
from plane.utils.notifikasi_persetujuan import ENTITY_EMAIL_APPROVAL
from plane.utils.penerima_aktif import aktif_sejak, batas_aktif
from plane.utils.saklar_instance import EMAIL_BATCH_DELAY_MINUTES, setelan_angka

logger = logging.getLogger("plane.worker")

PANJANG_KOMENTAR = 160
# Galat SMTP yang berarti "coba lagi nanti". Penolakan alamat tidak termasuk:
# mengulanginya hanya menghasilkan penolakan yang sama.
_GALAT_PERMANEN = (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError)

TEKS = {
    "id": {
        "subjek_aksi": "Perlu persetujuanmu: {a} tugas, dan {n} kabar lain",
        "subjek_aksi_saja": "Perlu persetujuanmu: {a} tugas",
        "subjek_kabar": "{n} kabar tentang {m} tugas",
        "judul": "Kabar tugasmu",
        "pratajuk_aksi": "{a} tugas menunggu keputusanmu.",
        "pratajuk_kabar": "{n} kabar tentang {m} tugas sejak email terakhir.",
        "bagian_aksi": "Menunggu persetujuanmu",
        "bagian_kabar": "Pembaruan",
        "aksi_baris": "menandai selesai, menunggu keputusanmu",
        "tombol_aksi": "Periksa dan putuskan",
        "tombol_tugas": "Buka tugas",
        "disetujui": "menyetujui pekerjaanmu",
        "ditolak": "menolak pekerjaanmu",
        "alasan": "Alasan",
        "komentar": "Komentar",
        "penyebutan": "Menyebutmu",
        "alasan_email": (
            "Anda menerima email ini karena mengikuti tugas-tugas ini. "
            "Kabarnya dikumpulkan supaya tidak datang satu per satu."
        ),
    },
    "en": {
        "subjek_aksi": "Needs your approval: {a} work items, and {n} other updates",
        "subjek_aksi_saja": "Needs your approval: {a} work items",
        "subjek_kabar": "{n} updates on {m} work items",
        "judul": "Updates on your work items",
        "pratajuk_aksi": "{a} work items are waiting for your decision.",
        "pratajuk_kabar": "{n} updates on {m} work items since the last email.",
        "bagian_aksi": "Waiting for your approval",
        "bagian_kabar": "Updates",
        "aksi_baris": "marked it done, waiting for your decision",
        "tombol_aksi": "Review and decide",
        "tombol_tugas": "Open work item",
        "disetujui": "approved your work",
        "ditolak": "rejected your work",
        "alasan": "Reason",
        "komentar": "Comment",
        "penyebutan": "Mentioned you",
        "alasan_email": (
            "You received this email because you follow these work items. "
            "Updates are collected so they don't arrive one by one."
        ),
    },
}


# ---------------------------------------------------------------- pengelompokan (murni)


def _aktivitas(baris) -> dict:
    return (baris.data or {}).get("issue_activity") or {}


def _issue_id(baris) -> str:
    return str(baris.entity_identifier or ((baris.data or {}).get("issue") or {}).get("id") or "")


def perlu_tindakan(baris) -> bool:
    """Pengajuan persetujuan ke atasan: satu-satunya kabar yang meminta keputusan penerima."""
    return (baris.entity or "") == ENTITY_EMAIL_APPROVAL and str(_aktivitas(baris).get("verb") or "") == "submitted"


def kelompokkan(daftar) -> tuple[list, dict]:
    """(aksi, {issue_id: [baris]}) dengan urutan `created_at` dipertahankan.

    Work item muncul sesuai kabar PERTAMA-nya; di dalam tiap work item baris tetap
    urut waktu. Pengajuan yang perlu tindakan dipisah ke `aksi`.
    """
    urut = sorted(daftar, key=lambda b: (b.created_at, str(b.id)))
    aksi = [b for b in urut if perlu_tindakan(b)]
    per_issue = {}
    for b in urut:
        if not perlu_tindakan(b):
            per_issue.setdefault(_issue_id(b), []).append(b)
    return aksi, per_issue


# ---------------------------------------------------------------- perakitan


def _teks_html(html, batas=PANJANG_KOMENTAR) -> str:
    teks = " ".join(BeautifulSoup(str(html or ""), "html.parser").get_text(" ").split())
    return teks if len(teks) <= batas else teks[: batas - 3].rstrip() + "..."


def _waktu(baris, zona) -> str:
    return timezone.localtime(baris.created_at, zona).strftime("%H:%M")


def _nama(user) -> str:
    return getattr(user, "display_name", None) or getattr(user, "email", None) or "?"


def keterangan_baris(baris, bahasa="id") -> str:
    """Satu kalimat untuk satu kabar di dalam kartu work item."""
    s = TEKS[bahasa]
    a = _aktivitas(baris)
    if (baris.entity or "") == ENTITY_EMAIL_APPROVAL:
        verb = str(a.get("verb") or "")
        if verb == "rejected":
            alasan = str(a.get("issue_comment") or "").strip()
            return s["ditolak"] + (f". {s['alasan']}: {alasan}" if alasan else "")
        return s["disetujui"] if verb == "approved" else s["aksi_baris"]
    kolom = str(a.get("field") or "")
    if kolom in ("comment", "mention"):
        label = s["komentar"] if kolom == "comment" else s["penyebutan"]
        return f"{label}: {_teks_html(a.get('new_value'))}"
    hasil = baris_perubahan({kolom: {"old_value": [a.get("old_value")], "new_value": [a.get("new_value")]}}, bahasa)
    if not hasil:
        return kolom.replace("_", " ")
    b = hasil[0]
    return f"{b['label']}: {b['lama']} → {b['baru']}" if b["lama"] else f"{b['label']}: {b['baru']}"


def _url_tugas(issue, dasar) -> str:
    return f"{dasar}/{issue.project.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}" if dasar else ""


def _url_antrean(issue, dasar) -> str:
    return f"{dasar}/{issue.project.workspace.slug}/projects/{issue.project_id}/persetujuan" if dasar else ""


def susun_ringkasan(penerima, aksi, per_issue, issues, bahasa="id") -> tuple[str, str, str]:
    """(subjek, html, teks) email ringkasan. `issues` = {issue_id: Issue}."""
    s = TEKS[bahasa]
    zona = _zona(penerima)
    dasar = base_url()
    n_kabar = sum(len(v) for v in per_issue.values())
    semua_issue = {_issue_id(b) for b in aksi} | set(per_issue)
    if aksi and n_kabar:
        subjek = s["subjek_aksi"].format(a=len(aksi), n=n_kabar)
    elif aksi:
        subjek = s["subjek_aksi_saja"].format(a=len(aksi))
    else:
        subjek = s["subjek_kabar"].format(n=n_kabar, m=len(semua_issue))
    pratajuk = (
        s["pratajuk_aksi"].format(a=len(aksi)) if aksi else s["pratajuk_kabar"].format(n=n_kabar, m=len(semua_issue))
    )

    isi = judul_html(s["judul"]) + paragraf(pratajuk, WARNA["teks_2"], UKURAN["isi_2"])
    teks = [s["judul"], "", pratajuk, ""]
    slug = ""

    if aksi:
        isi += judul_bagian(s["bagian_aksi"])
        teks += [f"== {s['bagian_aksi'].upper()} ==", ""]
        for b in aksi:
            issue = issues.get(_issue_id(b))
            if issue is None:
                continue
            slug = slug or issue.project.workspace.slug
            kode = f"{issue.project.identifier}-{issue.sequence_id}"
            baris = [(f"{_waktu(b, zona)} {_nama(b.triggered_by)}", s["aksi_baris"])]
            isi += kartu(kode, issue.name, _url_tugas(issue, dasar), baris) + tombol(
                s["tombol_aksi"], _url_antrean(issue, dasar)
            )
            teks += [f"{kode} {issue.name}", f"  {baris[0][0]}: {baris[0][1]}", f"  {_url_antrean(issue, dasar)}", ""]

    if per_issue:
        isi += judul_bagian(s["bagian_kabar"])
        teks += [f"== {s['bagian_kabar'].upper()} ==", ""]
        for issue_id, daftar in per_issue.items():
            issue = issues.get(issue_id)
            if issue is None:
                continue
            slug = slug or issue.project.workspace.slug
            kode = f"{issue.project.identifier}-{issue.sequence_id}"
            baris = [(f"{_waktu(b, zona)} {_nama(b.triggered_by)}", keterangan_baris(b, bahasa)) for b in daftar]
            isi += kartu(kode, issue.name, _url_tugas(issue, dasar), baris)
            teks += [f"{kode} {issue.name}"] + [f"  {lbl}: {nilai}" for lbl, nilai in baris]
            teks += [f"  {_url_tugas(issue, dasar)}", ""]

    html = bungkus(
        isi,
        bahasa=bahasa,
        judul=subjek,
        pratajuk=pratajuk,
        alasan=s["alasan_email"],
        url_preferensi=url_preferensi(slug),
        email_penerima=getattr(penerima, "email", ""),
    )
    return subjek, html, "\n".join(teks).strip() + "\n"


def _zona(user):
    try:
        return ZoneInfo(getattr(user, "user_timezone", None) or "UTC")
    except Exception:  # noqa: BLE001
        return ZoneInfo("UTC")


def _dasar_redis(issue_id) -> str:
    """Cadangan jalur lama: asal permintaan terakhir yang disimpan per work item di redis."""
    try:
        from plane.settings.redis import redis_instance

        nilai = redis_instance().get(str(issue_id))
        return nilai.decode() if nilai else ""
    except Exception:  # noqa: BLE001
        return ""


def _payload_pembaruan(daftar) -> dict:
    """{actor_id: [data]} seperti yang dirakit jalur lama untuk `aktor_dari_data`."""
    payload = {}
    for b in daftar:
        payload.setdefault(str(b.triggered_by_id), []).append(b.data)
    return payload


def susun_pesan(penerima, daftar) -> dict | None:
    """{subjek, html, teks, gambar, issue} untuk baris-baris satu penerima. None = tak ada yang layak dikirim."""
    from plane.bgtasks.email_notification_task import aktor_dari_data, susun_email_persetujuan
    from plane.utils.email_pembaruan import susun_email_pembaruan

    aksi, per_issue = kelompokkan(daftar)
    ids = {_issue_id(b) for b in daftar} - {""}
    issues = {str(i.id): i for i in Issue.objects.select_related("project", "project__workspace").filter(pk__in=ids)}
    if not issues:
        return None
    satu_issue = next(iter(issues.values())) if len(issues) == 1 else None
    ada_persetujuan = any((b.entity or "") == ENTITY_EMAIL_APPROVAL for b in daftar)

    if len(daftar) == 1 and ada_persetujuan:
        hasil = susun_email_persetujuan(daftar[0])
        if hasil is None:
            return None
        return {
            "subjek": hasil["subject"],
            "html": hasil["html"],
            "teks": hasil["teks"],
            "gambar": hasil["gambar"],
            "issue": hasil["issue"],
        }

    if satu_issue is not None and not ada_persetujuan:
        dasar = base_url() or _dasar_redis(satu_issue.id)
        subjek, html, teks, gambar = susun_email_pembaruan(
            satu_issue,
            aktor_dari_data(_payload_pembaruan(daftar)),
            dasar,
            bahasa_penerima(penerima),
            penerima.email,
        )
        return {"subjek": subjek, "html": html, "teks": teks, "gambar": gambar, "issue": satu_issue}

    subjek, html, teks = susun_ringkasan(penerima, aksi, per_issue, issues, bahasa_penerima(penerima))
    return {"subjek": subjek, "html": html, "teks": teks, "gambar": [], "issue": satu_issue}


# ---------------------------------------------------------------- antrean


def penerima_jatuh_tempo(sekarang=None) -> list:
    """Penerima yang kabar tertuanya (belum diproses) sudah melewati jeda God Mode."""
    sekarang = sekarang or timezone.now()
    batas = sekarang - timedelta(minutes=setelan_angka(EMAIL_BATCH_DELAY_MINUTES))
    return list(
        EmailNotificationLog.objects.filter(processed_at__isnull=True)
        .exclude(entity=ENTITY_UTAS)
        .values("receiver_id")
        .annotate(tertua=Min("created_at"))
        .filter(tertua__lte=batas)
        .order_by("tertua")
        .values_list("receiver_id", flat=True)
    )


def klaim_baris(receiver_id) -> list:
    """Ambil SEMUA baris penerima yang belum diproses dan tandai diproses, atomik.

    `skip_locked`: baris yang sedang dipegang penyapu lain dilewati, bukan ditunggu,
    jadi dua penyapu tidak pernah merakit email dari baris yang sama.
    """
    with transaction.atomic():
        daftar = list(
            EmailNotificationLog.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("receiver", "triggered_by")
            .filter(receiver_id=receiver_id, processed_at__isnull=True)
            .exclude(entity=ENTITY_UTAS)
            .order_by("created_at", "id")
        )
        if daftar:
            EmailNotificationLog.objects.filter(pk__in=[b.pk for b in daftar]).update(processed_at=timezone.now())
    return daftar


def _lepas_klaim(ids) -> None:
    EmailNotificationLog.objects.filter(pk__in=ids, sent_at__isnull=True).update(processed_at=None)


def kirim_kabar_penerima(receiver_id, batas=None, smtp_siap=True) -> str:
    """Kirim satu email berisi semua kabar penerima. Hasil: terkirim | kosong | dilewati | diulang | gagal."""
    daftar = klaim_baris(receiver_id)
    if not daftar:
        return "kosong"
    ids = [b.pk for b in daftar]
    penerima = daftar[0].receiver
    if not smtp_siap or not penerima.email or not penerima.is_active or not aktif_sejak(penerima, batas):
        # Tanpa SMTP, akun mati, atau lama tak aktif (ENABLE_EMAIL_ACTIVE_ONLY):
        # diproses tanpa terkirim. Inbox sudah ditulis di jalur lain.
        return "dilewati"
    try:
        pesan = susun_pesan(penerima, daftar)
        if pesan is None:
            return "dilewati"
        utas = utas_untuk(pesan["issue"], penerima.id) if pesan["issue"] is not None else None
        buat_pesan(
            ke=penerima.email,
            subjek=utas[0] if utas else pesan["subjek"],
            html=pesan["html"],
            teks=pesan["teks"],
            gambar=pesan["gambar"],
            header=utas[1] if utas else None,
        ).send(fail_silently=False)
    except _GALAT_PERMANEN as e:
        log_exception(e)
        return "gagal"
    except OSError as e:
        # Koneksi SMTP putus, timeout, server menolak sementara: coba lagi nanti.
        # (smtplib.SMTPException turunan OSError; yang permanen sudah ditangkap di atas.)
        log_exception(e)
        _lepas_klaim(ids)
        return "diulang"
    except Exception as e:  # noqa: BLE001
        log_exception(e)
        return "gagal"
    EmailNotificationLog.objects.filter(pk__in=ids).update(sent_at=timezone.now())
    return "terkirim"


def sapu_antrean(sekarang=None) -> dict:
    """Satu putaran: kirimi tiap penerima yang jatuh tempo satu email."""
    from plane.license.utils.instance_value import email_aktif, get_email_configuration

    smtp_siap = email_aktif(get_email_configuration()[0])
    batas = batas_aktif(sekarang)
    hasil = {}
    for receiver_id in penerima_jatuh_tempo(sekarang):
        status = kirim_kabar_penerima(receiver_id, batas=batas, smtp_siap=smtp_siap)
        hasil[status] = hasil.get(status, 0) + 1
    if hasil:
        logger.info("Antrean email: %s", hasil)
    return hasil


@shared_task
def kirim_kabar_sekarang(receiver_id):
    """Kirim antrean satu penerima SEKARANG, tanpa menunggu jendelanya habis."""
    from plane.license.utils.instance_value import email_aktif, get_email_configuration

    return kirim_kabar_penerima(receiver_id, batas=batas_aktif(), smtp_siap=email_aktif(get_email_configuration()[0]))
