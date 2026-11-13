# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bawaan email per jabatan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Saklar notifikasi yang BERLAKU untuk satu orang, dengan bawaan menurut jabatan.

Sejak 2026-11-02 satu baris membawa tiga kelompok saklar: email per jenis kabar
(`SAKLAR_EMAIL`), inbox di dalam aplikasi per jenis kabar (`SAKLAR_INBOX`), dan
bagian isi ringkasan harian (`SAKLAR_RINGKASAN`). Ketiganya ikut aturan bawaan
jabatan yang sama di bawah ini.

Keputusan user 2026-10-30, dipecah 2026-11-02 jadi tiga kelompok:

- Direktur (`BAWAAN_DIREKTUR`): hanya penyebutan, obrolan, dan ringkasan. Baris
  direktur di God Mode sekaligus BATAS ATAS untuk setiap direktur, berlaku
  seketika untuk akun lama juga.
- Leader (supervisor, manager; kunci tabel "pimpinan"): satu-satunya email bawaan adalah
  ringkasan harian sesuai jabatannya (tugas sendiri + tim/departemen/divisi).
  Di luar preferensi: email sistem (undangan, reset sandi, dst.) dan ringkasan
  laporan direktur (`direktur_digest_task`, ikhtisar per divisi). Sisanya dinyalakan sendiri.
- Staf (atau jenjang belum diisi, mengikuti `tingkat_efektif`): ringkasan harian
  (hari ini, 7 hari ke depan, terlambat), keputusan persetujuan, tugas
  selesai, dan tugas baru yang diberikan kepadanya (`assigned`). Pengingat per tugas (H-7..H+7)
  mati: ringkasan menggantikannya.

Kenapa dihitung saat dibaca, bukan disimpan saat jabatan berubah: jabatan bisa
berubah lewat lima jalur (God Mode, penempatan, organisasi, migrasi, `.update()`
massal) dan tak satu pun boleh lupa menyetel ulang preferensi. Selama
`ikut_bawaan_jabatan` hidup, bawaan selalu mengikuti jabatan HARI INI.

Yang dihitung saat dibaca hanya PILIHAN barisnya (staf atau pimpinan). Isi kedua
baris dipotret dari God Mode (KEP-44) ke `bawaan_email` saat preferensi lahir, jadi
mengubah bawaan di God Mode hanya mengenai akun baru. Kembali ke bawaan jabatan
memotret ulang tabel God Mode hari itu.

Begitu orangnya (atau Super Admin di God Mode) mengubah satu saklar, seluruh nilai
yang berlaku dibekukan ke kolom dan `ikut_bawaan_jabatan` dimatikan: sejak itu
pilihan manusia yang menang, bukan jabatan.
"""

SAKLAR_EMAIL = (
    "property_change",
    "state_change",
    "comment",
    "mention",
    "issue_completed",
    "approval",
    "daily_digest",
    # Edisi sore ringkasan harian, 17.30 WIB (keputusan user 2026-11-02).
    "daily_digest_sore",
    "deadline_reminder",
    "assigned",
    # Email "ada pesan belum dibaca" (chat_notification_task). Saklar instance
    # ENABLE_CHAT_EMAIL tetap rem utamanya; ini pilihan per orang di bawahnya.
    "chat",
)

# Saklar INBOX di dalam aplikasi, satu per jenis kabar (keputusan user 2026-11-02).
# Sebelumnya inbox selalu ditulis; sekarang orangnya memilih per jenis, sama seperti
# email. Bawaannya hidup semua, jadi perilaku lama tidak berubah sampai ada yang memilih.
SAKLAR_INBOX = (
    "inbox_assigned",
    "inbox_mention",
    "inbox_comment",
    "inbox_approval",
    "inbox_deadline",
    "inbox_issue_completed",
    "inbox_state_change",
    "inbox_property_change",
    "inbox_chat",
)

# Bagian yang dimuat ringkasan harian (daily_digest_email). Hanya berarti selama
# `daily_digest` hidup. `digest_tim` hanya berisi untuk supervisor dan manager.
SAKLAR_RINGKASAN = (
    "digest_terlambat",
    "digest_hari_ini",
    "digest_depan",
    "digest_diberikan",
    "digest_tim",
)

# Semua saklar yang dibawa satu baris preferensi, urutan tetap. Daftar inilah yang
# dipakai endpoint profil, God Mode per member, dan tabel bawaan jabatan, jadi
# ketiganya tidak bisa tidak sinkron. Cermin `NOTIFICATION_PREFERENCE_KEYS` di
# packages/constants/src/notification-preferences.ts.
SAKLAR_NOTIFIKASI = SAKLAR_EMAIL + SAKLAR_INBOX + SAKLAR_RINGKASAN

# Ringkasan harian hidup untuk SEMUA jabatan, isinya disesuaikan jabatan
# (daily_digest_task). Ia menggantikan pengingat per tugas, jadi
# `deadline_reminder` mati secara bawaan (keputusan user 2026-10-30, putaran 2).
# Inbox, email obrolan, dan semua bagian ringkasan hidup untuk semua jabatan:
# itu perilaku sebelum saklarnya ada.
BAWAAN_PIMPINAN = (
    {kunci: False for kunci in SAKLAR_EMAIL}
    | {"daily_digest": True, "daily_digest_sore": True, "chat": True}
    | {kunci: True for kunci in SAKLAR_INBOX + SAKLAR_RINGKASAN}
)
# Direktur (keputusan user 2026-11-02): tidak pernah menerima kabar kerja harian,
# hanya penyebutan, obrolan, dan ringkasan. Persetujuan, perubahan properti/status,
# tugas selesai, tugas baru, komentar, dan pengingat tenggat mati di inbox DAN email.
# Baris ini juga BATAS ATAS (lihat `saklar_efektif`).
KABAR_DIREKTUR = ("mention", "chat")
BAWAAN_DIREKTUR = (
    {kunci: False for kunci in SAKLAR_EMAIL + SAKLAR_INBOX}
    | {kunci: True for kunci in KABAR_DIREKTUR}
    | {"inbox_" + kunci: True for kunci in KABAR_DIREKTUR}
    | {"daily_digest": True, "daily_digest_sore": True}
    | {kunci: True for kunci in SAKLAR_RINGKASAN}
)
BAWAAN_STAF = {
    **BAWAAN_PIMPINAN,
    "issue_completed": True,
    "approval": True,
    # Diberi tugas oleh atasan (keputusan user 2026-11-02). Pimpinan tetap mati:
    # tugas barunya sudah masuk DM penugasan dan ringkasan pagi.
    "assigned": True,
}


# Kelompok tabel bawaan. "pimpinan" = leader (supervisor dan manager); namanya
# dipertahankan karena sudah tersimpan di God Mode dan di potret `bawaan_email`.
# Super Admin TIDAK punya baris sendiri (keputusan user 2026-11-06): ia mengikuti
# jabatannya seperti orang lain. Email yang hanya diterima Super Admin diatur di
# God Mode > Notifications > Sending rules (ENABLE_ADMIN_*).
KELOMPOK_JABATAN = ("staf", "pimpinan", "direktur")


def _kelompok_dari_tingkat(tingkat) -> str:
    from plane.db.models import TINGKAT_SUPERVISOR, menjangkau_seluruh_organisasi

    if tingkat is None or tingkat < TINGKAT_SUPERVISOR:
        return "staf"
    # Sekretaris (KEP-101) memakai baris "direktur": jangkauannya sama, jadi kebijakan
    # notifikasinya juga. Tidak ada baris bawaan keempat di God Mode.
    return "direktur" if menjangkau_seluruh_organisasi(tingkat) else "pimpinan"


def _kelompok_menurut_jabatan(user_ids) -> dict:
    """{user_id: 'staf'|'pimpinan'|'direktur'} dengan satu kueri. Jabatan TERTINGGI di
    workspace mana pun, karena preferensi notifikasi bersifat global."""
    from django.db.models import Max

    from plane.db.models import JabatanOrganisasi

    ids = set(user_ids)
    tertinggi = dict(
        JabatanOrganisasi.objects.filter(member_id__in=ids)
        .values("member_id")
        .annotate(t=Max("tingkat"))
        .values_list("member_id", "t")
    )
    return {u: _kelompok_dari_tingkat(tertinggi.get(u)) for u in ids}


def kelompok_massal(user_ids) -> dict:
    """{user_id: kelompok} menurut jabatan, dengan satu kueri. Super Admin tidak istimewa."""
    return _kelompok_menurut_jabatan(user_ids)


def kelompok_jabatan(user_id) -> str:
    """'staf', 'pimpinan' (leader: supervisor/manager), atau 'direktur'."""
    return kelompok_massal([user_id])[user_id]


def adalah_pimpinan(user_id) -> bool:
    """Supervisor ke atas di workspace MANA PUN. Preferensi email bersifat global."""
    return _kelompok_menurut_jabatan([user_id])[user_id] != "staf"


def tabel_bawaan_sekarang() -> dict:
    """Tabel staf/pimpinan/direktur yang diatur di God Mode hari ini (KEP-44)."""
    from plane.utils.bawaan_member import baca_bawaan

    return baca_bawaan()["email"]


def _baris(kelompok, sekarang, potret) -> dict:
    """Baris tabel satu kelompok. Kunci atau kelompok yang hilang dari potret lama
    (ditambah belakangan) jatuh ke tabel God Mode hari ini."""
    hari_ini = sekarang[kelompok]
    baris = potret.get(kelompok) if isinstance(potret, dict) else None
    if not isinstance(baris, dict):
        return dict(hari_ini)
    return {kunci: bool(baris.get(kunci, hari_ini[kunci])) for kunci in SAKLAR_NOTIFIKASI}


def bawaan_jabatan(user_id, tabel=None) -> dict:
    """Baris tabel untuk jabatan orangnya. `tabel` None = tabel God Mode hari ini."""
    return _baris(kelompok_jabatan(user_id), tabel_bawaan_sekarang(), tabel)


def dikunci(user_id, sekarang=None, kelompok=None) -> list:
    """Saklar yang dipaksa mati kebijakan direktur di God Mode. Kosong untuk selain direktur."""
    kelompok = kelompok or kelompok_jabatan(user_id)
    if kelompok != "direktur":
        return []
    batas = (sekarang or tabel_bawaan_sekarang())["direktur"]
    return [kunci for kunci in SAKLAR_NOTIFIKASI if not batas[kunci]]


# Saklar pribadi yang punya saklar induk di God Mode (KEP-83). Induk mati =
# saklar pribadinya terkunci "Turned off by admin" di web; pilihan orangnya tetap
# tersimpan dan berlaku lagi begitu induknya dinyalakan.
INDUK_INSTANCE = {
    "deadline_reminder": "ENABLE_DEADLINE_REMINDER",
    "chat": "ENABLE_CHAT_EMAIL",
}
ALASAN_SAKLAR_INSTANCE = "instance_switch_off"
ALASAN_BATAS_DIREKTUR = "director_cap"


def kunci_admin(user_id, kelompok=None, sekarang=None) -> dict:
    """{saklar: alasan} yang dikunci admin untuk orang ini; tak bisa ia nyalakan.

    Alasan `instance_switch_off` (saklar induk God Mode mati) didahulukan atas
    `director_cap` (baris direktur God Mode, KEP-59), karena itu yang lebih luas.
    """
    from plane.utils.saklar_instance import saklar_aktif

    hasil = {kunci: ALASAN_BATAS_DIREKTUR for kunci in dikunci(user_id, sekarang, kelompok)}
    for kunci, induk in INDUK_INSTANCE.items():
        if not saklar_aktif(induk):
            hasil[kunci] = ALASAN_SAKLAR_INSTANCE
    return {kunci: hasil[kunci] for kunci in SAKLAR_NOTIFIKASI if kunci in hasil}


def saklar_efektif(pref, user_id=None, kelompok=None, sekarang=None) -> dict:
    """Nilai yang berlaku. `pref` boleh None (baris belum ada = ikut bawaan God Mode hari ini).

    Untuk direktur, baris direktur God Mode HARI INI adalah batas atas: saklar yang
    mati di sana mati juga di sini, walau pilihan pribadi atau potret lama
    menyalakannya. "Direktur tidak pernah menerima kabar kerja harian" adalah
    kebijakan, bukan sekadar bawaan (keputusan user 2026-11-02).

    `kelompok` dan `sekarang` diisi pemanggil massal supaya tak ada kueri per orang.
    """
    uid = pref.user_id if pref is not None else user_id
    kelompok = kelompok or kelompok_jabatan(uid)
    sekarang = sekarang or tabel_bawaan_sekarang()
    if pref is None or pref.ikut_bawaan_jabatan:
        # Direktur tidak memakai potret: barisnya kebijakan, jadi selalu tabel hari ini.
        potret = pref.bawaan_email if pref is not None and kelompok != "direktur" else None
        nilai = _baris(kelompok, sekarang, potret)
    else:
        nilai = {kunci: bool(getattr(pref, kunci)) for kunci in SAKLAR_NOTIFIKASI}
    for kunci in dikunci(uid, sekarang, kelompok):
        nilai[kunci] = False
    return nilai


def saklar_untuk(user_id) -> dict:
    """Saklar yang berlaku untuk satu user, dibaca dari baris preferensi globalnya."""
    from plane.db.models import UserNotificationPreference

    pref = UserNotificationPreference.objects.filter(user_id=user_id, workspace=None, project=None).first()
    return saklar_efektif(pref, user_id)


def boleh(user_id, kunci) -> bool:
    """Satu saklar (email, inbox, atau bagian ringkasan) yang berlaku untuk satu orang."""
    return saklar_untuk(user_id)[kunci]


boleh_email = boleh


def penyaring(user_ids, kunci) -> set:
    """Id yang saklar `kunci`-nya BERLAKU hidup, dengan satu kueri preferensi.

    Untuk pengirim massal (inbox tenggat, notifikasi issue): `boleh()` per orang
    berarti satu kueri per penerima.
    """
    from plane.db.models import UserNotificationPreference

    ids = set(user_ids)
    if not ids:
        return set()
    pref = {
        p.user_id: p for p in UserNotificationPreference.objects.filter(user_id__in=ids, workspace=None, project=None)
    }
    kelompok = kelompok_massal(ids)
    sekarang = tabel_bawaan_sekarang()
    return {u for u in ids if saklar_efektif(pref.get(u), u, kelompok[u], sekarang)[kunci]}


def terapkan_perubahan(pref, perubahan) -> list:
    """Tulis `perubahan` ke `pref` (belum di-save). Kembalikan update_fields.

    `ikut_bawaan_jabatan=True` di `perubahan` = kembali ke bawaan jabatan GOD MODE
    HARI INI (potret diperbarui); saklar lain di permintaan yang sama diabaikan
    karena bawaan yang menentukan.
    """
    if perubahan.get("ikut_bawaan_jabatan") is True:
        pref.ikut_bawaan_jabatan = True
        pref.bawaan_email = tabel_bawaan_sekarang()
        return ["ikut_bawaan_jabatan", "bawaan_email"]

    saklar = {k: v for k, v in perubahan.items() if k in SAKLAR_NOTIFIKASI}
    # `ikut_bawaan_jabatan=False` tanpa saklar lain = bekukan nilai yang berlaku sekarang.
    if not saklar and perubahan.get("ikut_bawaan_jabatan") is not False:
        return []
    nilai = {**saklar_efektif(pref), **saklar}
    for kunci, v in nilai.items():
        setattr(pref, kunci, v)
    pref.ikut_bawaan_jabatan = False
    return [*SAKLAR_NOTIFIKASI, "ikut_bawaan_jabatan"]
