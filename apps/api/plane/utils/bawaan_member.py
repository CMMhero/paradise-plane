# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bawaan member baru di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Setelan yang diterima akun BARU, diatur Super Admin di God Mode (KEP-44).

Satu baris `InstanceConfiguration` (`PARADISE_BAWAAN_MEMBER`, JSON), dibaca ulang
tiap dipakai seperti saklar KEP-40. Tiga bagian, dengan saat berlaku yang beda:

- `profile`: bahasa, zona waktu, tema, awal pekan, tampilan notifikasi, kursor,
  rel aplikasi. Ditulis SEKALI saat baris Profile/User lahir (signal pre_save di
  `db/models/user.py`). Akun lama tidak berubah.
- `email`: tabel bawaan jabatan KEP-42 (staf, leader/pimpinan, direktur). Baris
  direktur berlaku seketika untuk semua direktur (batas atas, bukan potret). Dipotret ke
  `UserNotificationPreference.bawaan_email` saat preferensi lahir, jadi hanya
  mengenai akun baru. Akun lama tetap ikut jabatannya (staf/pimpinan dipilih saat
  dibaca), tapi dengan tabel miliknya sendiri.
- `keanggotaan`: hak akses workspace dan jabatan yang diberikan saat akun dibuat
  dari God Mode (`InstanceMemberEndpoint.post`, satu-satunya pintu masuk akun).
- `navigasi`: item sidebar yang disematkan, gaya daftar project (accordion/tab),
  dan batas jumlah project di sidebar. Ditulis saat baris preferensi sidebar
  (`WorkspaceUserPreference`) atau `WorkspaceUserProperties` lahir.
- `work_items`: tata letak daftar work item (Board, List, ...). Dibaca bawaan
  kolom `ProjectUserProperty.display_filters`, jadi berlaku untuk setiap pasangan
  member+project yang baru, termasuk member lama yang baru masuk project.

Akun lama bisa disamakan sekaligus lewat `terapkan_ke_semua` (tombol "Apply to
existing members" di God Mode), tidak pernah diam-diam.

Nilai yang belum pernah disimpan jatuh ke `PABRIK`, yang sama persis dengan
perilaku sebelum menu ini ada.
"""

import json
import logging

import pytz

from plane.utils.preferensi_email import (
    BAWAAN_DIREKTUR,
    BAWAAN_PIMPINAN,
    BAWAAN_STAF,
    KELOMPOK_JABATAN,
    SAKLAR_NOTIFIKASI,
)

logger = logging.getLogger("plane.api")

KUNCI = "PARADISE_BAWAAN_MEMBER"

# cermin packages/i18n/src/constants/language.ts
BAHASA_SAH = frozenset(
    {
        "en",
        "fr",
        "es",
        "ja",
        "zh-CN",
        "zh-TW",
        "ru",
        "it",
        "cs",
        "sk",
        "de",
        "ua",
        "pl",
        "ko",
        "pt-BR",
        "id",
        "ro",
        "vi-VN",
        "tr-TR",
    }
)
# Tema siap pakai saja. "custom" butuh palet yang hanya bisa disusun orangnya sendiri.
TEMA_SAH = frozenset({"system", "light", "dark", "light-contrast", "dark-contrast"})
HARI_PEKAN_SAH = frozenset(range(7))  # Profile.START_OF_THE_WEEK_CHOICES
# Semua nama IANA: /api/timezones/ memuat "America/Godthab" yang tak ada di common_timezones.
ZONA_WAKTU_SAH = pytz.all_timezones_set
# Sengaja TIDAK diatur dari sini: `notification_view_mode`, `is_smooth_cursor_enabled`,
# dan `is_app_rail_docked`. Kolomnya ada di Profile (bawaan upstream), tapi
# apps/web edisi ini tidak pernah membacanya; app rail bahkan mati di CE dan
# status sematnya disimpan di localStorage. Saklar yang tak berefek cuma menipu
# admin, jadi dicabut dari God Mode (30 Okt 2026). Nilai lama yang masih
# tersimpan di bawaan ikut terbuang sendiri oleh `_gabung` (hanya kunci PABRIK).
KOLOM_PROFIL = ("language", "start_of_the_week")
# Preferensi tampilan (KEP-64). Disimpan di `Profile.theme` (JSONField) di samping
# `theme`, bukan kolom sendiri, jadi tanpa migrasi. Cermin `TAMPILAN_PABRIK` di
# apps/web/core/lib/tampilan.ts; nilai pertama tiap himpunan = bawaan pabrik.
GAYA_SAH = {
    "skema": ("bara", "senja", "sumi", "hutan", "netral"),
    "font": (
        "jakarta",
        "inter",
        "geist",
        "figtree",
        "bricolage",
        "archivo",
        "sora",
        "shantell",
        "jetbrains",
        "serif",
        "sistem",
    ),
    "gerak": ("halus", "kurangi"),
}
GAYA_PABRIK = {kunci: pilihan[0] for kunci, pilihan in GAYA_SAH.items()}
# Suara pemberitahuan: volume 0..100 dan bisu. Tinggal di `Profile.theme` yang
# sama dengan GAYA_SAH (tanpa migrasi), tapi bukan pilihan dari daftar, jadi
# diperiksa tipenya. Cermin `SUARA_PABRIK` di apps/web/core/lib/suara.ts.
SUARA_PABRIK = {"volume_suara": 80, "suara_bisu": False}


def suara_sah(kunci: str, nilai) -> bool:
    if kunci == "suara_bisu":
        return isinstance(nilai, bool)
    # bool adalah int di Python; True tidak boleh lolos sebagai volume 1.
    return isinstance(nilai, int) and not isinstance(nilai, bool) and 0 <= nilai <= 100


def suara_efektif(tema) -> dict:
    """Nilai suara yang berlaku: kosong atau rusak = pabrik."""
    tema = tema if isinstance(tema, dict) else {}
    return {k: tema[k] if suara_sah(k, tema.get(k)) else v for k, v in SUARA_PABRIK.items()}


# Semua kunci yang disimpan di `Profile.theme` selain `theme` itu sendiri.
KUNCI_TEMA_PARADISE = (*GAYA_SAH, *SUARA_PABRIK)

# Hanya Member dan Guest. Admin workspace untuk SETIAP akun baru adalah lubang,
# bukan bawaan; Admin tetap diberikan per orang di halaman Member.
PERAN_BAWAAN_SAH = frozenset({5, 15})
# None = jabatan belum diisi (tetap dihitung staf oleh `tingkat_efektif`).
# Direktur sengaja tidak bisa jadi bawaan: direktur tanpa penempatan menjangkau
# seluruh perusahaan, jadi harus diberikan dengan sadar per orang.
TINGKAT_BAWAAN_SAH = frozenset({None, 10, 20, 30})

# Item sidebar yang bisa disematkan. Cermin `PERSONAL_ITEMS` dan
# WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS_LINKS di apps/web; kuncinya juga harus
# ada di `WorkspaceUserPreference.UserPreferenceKeys`, kalau tidak barisnya tak
# pernah dibuat dan saklar semat di web tidak berbuat apa-apa.
NAV_PRIBADI = ("your_work", "stickies", "drafts", "quick_links")
NAV_WORKSPACE = ("views", "analytics", "dashboard_divisi", "initiatives", "chat", "wiki", "archives")
NAV_KUNCI = NAV_PRIBADI + NAV_WORKSPACE
MODE_NAVIGASI_SAH = frozenset({"ACCORDION", "TABBED"})
# 0 = tampilkan semua project. Batas atas sekadar penjaga salah ketik.
BATAS_PROJECT_MAKS = 50
# Cermin EIssueLayoutTypes di packages/types, tanpa gantt (dicabut bersama cycles).
TATA_LETAK_SAH = frozenset({"list", "kanban", "calendar", "spreadsheet"})

PABRIK = {
    "profile": {
        "language": "en",
        "timezone": "Asia/Jakarta",
        "theme": "system",
        "start_of_the_week": 0,
        **GAYA_PABRIK,
        **SUARA_PABRIK,
    },
    # "pimpinan" = leader (supervisor, manager). Baris direktur juga batas atas.
    "email": {"staf": dict(BAWAAN_STAF), "pimpinan": dict(BAWAAN_PIMPINAN), "direktur": dict(BAWAAN_DIREKTUR)},
    "keanggotaan": {"workspace_role": 15, "tingkat": 10},
    # Semua menu tersemat, project bertab, semua project tampil (permintaan user
    # 2 Nov 2026). Menu khusus admin tetap disaring izin di web.
    "navigasi": {
        "pinned": dict.fromkeys(NAV_KUNCI, True),
        "project_mode": "TABBED",
        "project_limit": 0,
    },
    # Board, bukan List (permintaan user 2 Nov 2026).
    "work_items": {"layout": "kanban"},
}


def _gabung(dasar: dict, atas: dict) -> dict:
    """Timpa `dasar` dengan `atas`, hanya untuk kunci yang dikenal `dasar`."""
    hasil = {}
    for kunci, nilai in dasar.items():
        lain = atas.get(kunci, nilai) if isinstance(atas, dict) else nilai
        hasil[kunci] = _gabung(nilai, lain) if isinstance(nilai, dict) else lain
    return hasil


def baca_bawaan() -> dict:
    """Bawaan yang berlaku sekarang. Baris rusak = pabrik, dicatat ke log, tidak meledak."""
    from plane.license.models import InstanceConfiguration

    mentah = InstanceConfiguration.objects.filter(key=KUNCI).values_list("value", flat=True).first()
    tersimpan = {}
    if mentah:
        try:
            tersimpan = json.loads(mentah)
        except (TypeError, ValueError):
            logger.warning("%s bukan JSON sah; memakai bawaan pabrik", KUNCI)
    return _gabung(PABRIK, tersimpan if isinstance(tersimpan, dict) else {})


def periksa_profil(profil) -> tuple[dict, str | None]:
    """Saring dan cek kolom profil. Dipakai bawaan ini DAN preferensi per member."""
    if not isinstance(profil, dict):
        return {}, "Invalid profile format."
    baru = {}
    if "language" in profil:
        if profil["language"] not in BAHASA_SAH:
            return {}, "Language not supported."
        baru["language"] = profil["language"]
    if "start_of_the_week" in profil:
        # bool lolos `in` set angka (True == 1), jadi tolak eksplisit.
        hari = profil["start_of_the_week"]
        if isinstance(hari, bool) or hari not in HARI_PEKAN_SAH:
            return {}, "Invalid start of the week."
        baru["start_of_the_week"] = hari
    if "timezone" in profil:
        if profil["timezone"] not in ZONA_WAKTU_SAH:
            return {}, "Invalid timezone."
        baru["timezone"] = profil["timezone"]
    if "theme" in profil:
        if profil["theme"] not in TEMA_SAH:
            return {}, "Invalid theme."
        baru["theme"] = profil["theme"]
    for kunci, pilihan in GAYA_SAH.items():
        if kunci in profil:
            if profil[kunci] not in pilihan:
                return {}, f"Invalid {kunci}."
            baru[kunci] = profil[kunci]
    for kunci in SUARA_PABRIK:
        if kunci in profil:
            if not suara_sah(kunci, profil[kunci]):
                return {}, f"Invalid {kunci}."
            baru[kunci] = profil[kunci]
    return baru, None


def _periksa_email(email) -> tuple[dict, str | None]:
    if not isinstance(email, dict) or set(email) - set(KELOMPOK_JABATAN):
        return {}, "Email defaults only accept 'staf', 'pimpinan', and 'direktur'."
    baru = {}
    for kelompok, saklar in email.items():
        if not isinstance(saklar, dict) or set(saklar) - set(SAKLAR_NOTIFIKASI):
            return {}, f"Unknown email toggles for {kelompok}."
        if any(not isinstance(v, bool) for v in saklar.values()):
            return {}, f"Email toggles for {kelompok} must be true or false."
        baru[kelompok] = dict(saklar)
    return baru, None


def _periksa_keanggotaan(data) -> tuple[dict, str | None]:
    if not isinstance(data, dict) or set(data) - {"workspace_role", "tingkat"}:
        return {}, "Membership defaults only accept 'workspace_role' and 'tingkat'."
    baru = {}
    if "workspace_role" in data:
        peran = data["workspace_role"]
        if isinstance(peran, bool) or peran not in PERAN_BAWAAN_SAH:
            return {}, "Default workspace role must be Member (15) or Guest (5)."
        baru["workspace_role"] = peran
    if "tingkat" in data:
        tingkat = data["tingkat"]
        if isinstance(tingkat, bool) or tingkat not in TINGKAT_BAWAAN_SAH:
            return {}, "Default level must be empty, Member (10), Supervisor (20), or Manager (30)."
        baru["tingkat"] = tingkat
    return baru, None


def periksa_navigasi(data) -> tuple[dict, str | None]:
    """Cek bagian navigasi. Dipakai bawaan ini DAN preferensi per member."""
    if not isinstance(data, dict) or set(data) - {"pinned", "project_mode", "project_limit"}:
        return {}, "Navigation only accepts 'pinned', 'project_mode', and 'project_limit'."
    baru = {}
    if "pinned" in data:
        semat = data["pinned"]
        if not isinstance(semat, dict) or set(semat) - set(NAV_KUNCI):
            return {}, "Unknown navigation items."
        if any(not isinstance(v, bool) for v in semat.values()):
            return {}, "Pinned items must be true or false."
        baru["pinned"] = dict(semat)
    if "project_mode" in data:
        if data["project_mode"] not in MODE_NAVIGASI_SAH:
            return {}, "Project navigation must be ACCORDION or TABBED."
        baru["project_mode"] = data["project_mode"]
    if "project_limit" in data:
        batas = data["project_limit"]
        if isinstance(batas, bool) or not isinstance(batas, int) or not 0 <= batas <= BATAS_PROJECT_MAKS:
            return {}, f"Project limit must be a whole number from 0 to {BATAS_PROJECT_MAKS}."
        baru["project_limit"] = batas
    return baru, None


def periksa_work_items(data) -> tuple[dict, str | None]:
    """Cek bagian tata letak work item. Dipakai bawaan ini DAN preferensi per member."""
    if not isinstance(data, dict) or set(data) - {"layout"}:
        return {}, "Work item defaults only accept 'layout'."
    baru = {}
    if "layout" in data:
        if data["layout"] not in TATA_LETAK_SAH:
            return {}, "Unknown work item layout."
        baru["layout"] = data["layout"]
    return baru, None


def periksa_perubahan(data) -> tuple[dict, str | None]:
    """Cek PATCH parsial. Kembalikan (bawaan_lengkap_sesudahnya, galat).

    Semua bagian dicek sebelum apa pun ditulis; kunci tak dikenal ditolak supaya
    salah ketik tidak diam-diam diabaikan.
    """
    if not isinstance(data, dict) or not data:
        return {}, "No changes."
    asing = set(data) - set(PABRIK)
    if asing:
        return {}, f"Unknown sections: {', '.join(sorted(asing))}."

    perubahan = {}
    for bagian, pemeriksa in (
        ("profile", periksa_profil),
        ("email", _periksa_email),
        ("keanggotaan", _periksa_keanggotaan),
        ("navigasi", periksa_navigasi),
        ("work_items", periksa_work_items),
    ):
        if bagian in data:
            if bagian == "profile" and isinstance(data[bagian], dict) and set(data[bagian]) - set(PABRIK["profile"]):
                return {}, "Unknown profile fields."
            bersih, galat = pemeriksa(data[bagian])
            if galat:
                return {}, galat
            perubahan[bagian] = bersih
    return _gabung(baca_bawaan(), perubahan), None


def simpan_bawaan(bawaan: dict) -> None:
    from plane.license.models import InstanceConfiguration

    InstanceConfiguration.objects.update_or_create(
        key=KUNCI,
        defaults={"value": json.dumps(bawaan), "category": "PARADISE", "is_encrypted": False},
    )


def terapkan_ke_profil_baru(profil) -> None:
    """Isi Profile yang BARU akan disimpan. Nilai yang diberikan pemanggil menang.

    "Diberikan" = berbeda dari bawaan kolom model. Kolom yang masih bernilai bawaan
    model dianggap belum dipilih siapa pun, jadi diisi dari God Mode.
    """
    bawaan = baca_bawaan()["profile"]
    for kolom in KOLOM_PROFIL:
        if getattr(profil, kolom) == profil._meta.get_field(kolom).get_default():
            setattr(profil, kolom, bawaan[kolom])
    if not profil.theme:
        profil.theme = {"theme": bawaan["theme"], **{kunci: bawaan[kunci] for kunci in KUNCI_TEMA_PARADISE}}


def terapkan_ke_user_baru(user) -> None:
    if user.user_timezone == user._meta.get_field("user_timezone").get_default():
        user.user_timezone = baca_bawaan()["profile"]["timezone"]


def filter_tampilan(layout: str, lama: dict | None = None) -> dict:
    """`display_filters` dengan tata letak `layout`.

    Board butuh pengelompokan; tanpa `group_by` web memaksakan "state" sendiri,
    jadi diisi di sini juga supaya server dan web sepakat.
    """
    hasil = dict(lama or {})
    hasil["layout"] = layout
    if layout == "kanban" and not hasil.get("group_by"):
        hasil["group_by"] = "state"
    return hasil


def tata_letak_bawaan() -> str:
    """Tata letak work item bawaan, aman dipanggil dari bawaan kolom model.

    Bawaan kolom ikut terpanggil di migrasi dan `bulk_create`. Kueri yang gagal
    (tabel belum ada) di dalam transaksi Postgres meracuni seluruh transaksi, jadi
    kuerinya dibungkus savepoint dan kegagalan jatuh ke pabrik.
    """
    from django.db import DatabaseError, transaction

    try:
        with transaction.atomic():
            return baca_bawaan()["work_items"]["layout"]
    except DatabaseError:
        return PABRIK["work_items"]["layout"]


def terapkan_ke_properti_workspace_baru(properti) -> None:
    """Isi `WorkspaceUserProperties` yang BARU. Nilai selain bawaan model = dipilih pemanggil."""
    bawaan = baca_bawaan()["navigasi"]
    meta = properti._meta
    if properti.navigation_project_limit == meta.get_field("navigation_project_limit").get_default():
        properti.navigation_project_limit = bawaan["project_limit"]
    if properti.navigation_control_preference == meta.get_field("navigation_control_preference").get_default():
        properti.navigation_control_preference = bawaan["project_mode"]


BAGIAN_MASSAL = frozenset({"navigasi", "work_items"})


def terapkan_ke_semua(bagian) -> dict:
    """Samakan member LAMA dengan bawaan sekarang, hanya `navigasi` dan `work_items`.

    Mengembalikan jumlah baris yang diubah per bagian. Profil dan email sengaja
    tidak ikut: bahasa dan surel adalah pilihan pribadi yang tak boleh tertimpa massal.
    """
    from django.db import transaction

    from plane.db.models import ProjectUserProperty, WorkspaceUserPreference, WorkspaceUserProperties

    bawaan = baca_bawaan()
    hasil = {}
    with transaction.atomic():
        if "navigasi" in bagian:
            nav = bawaan["navigasi"]
            jumlah = 0
            for kunci, semat in nav["pinned"].items():
                jumlah += (
                    WorkspaceUserPreference.objects.filter(key=kunci, user__is_bot=False)
                    .exclude(is_pinned=semat)
                    .update(is_pinned=semat)
                )
            jumlah += (
                WorkspaceUserProperties.objects.filter(user__is_bot=False)
                .exclude(
                    navigation_control_preference=nav["project_mode"],
                    navigation_project_limit=nav["project_limit"],
                )
                .update(
                    navigation_control_preference=nav["project_mode"],
                    navigation_project_limit=nav["project_limit"],
                )
            )
            hasil["navigasi"] = jumlah
        if "work_items" in bagian:
            layout = bawaan["work_items"]["layout"]
            berubah = []
            for prop in ProjectUserProperty.objects.filter(user__is_bot=False).only("id", "display_filters"):
                lama = prop.display_filters if isinstance(prop.display_filters, dict) else {}
                baru = filter_tampilan(layout, lama)
                if baru != lama:
                    prop.display_filters = baru
                    berubah.append(prop)
            ProjectUserProperty.objects.bulk_update(berubah, ["display_filters"], batch_size=200)
            hasil["work_items"] = len(berubah)
    return hasil
