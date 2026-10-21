# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu sumber kebenaran untuk batas tingkatan, dan penegakannya.

KENAPA SEMUA DI SATU BERKAS

Batas hanya berguna kalau tidak bisa dilewati, dan cara paling umum sebuah batas
jadi bisa dilewati adalah lahir dua kali dengan angka yang lama-lama berbeda.
Di repo ini ada DELAPAN titik yang mencetak URL unggahan, tersebar di lima
berkas. Menaruh pemeriksaan di tiap pemanggil berarti delapan tempat yang harus
diingat orang berikutnya. Jadi yang ditulis di sini fungsinya, dan kedelapan
titik itu memanggilnya.

Aturannya: jangan pernah menyalin angka dari berkas ini ke tempat lain, dan
jangan pernah menghitung ulang kuota di TypeScript. Tanya ke sini.

ANGKANYA KEPUTUSAN BISNIS, BUKAN KEPUTUSAN TEKNIS

Angka bawaan di bawah adalah tebakan awal yang diturunkan dari matriks fitur di
rencana produk, bukan hasil pengukuran. Ketiganya untuk tingkatan gratis bisa
disetel lewat variabel lingkungan justru karena tingkatan itulah yang ongkosnya
paling perlu dipantau, dan yang paling mungkin diubah tanpa mau menunggu rilis.
"""

import os

from rest_framework.exceptions import APIException

# 1 GiB, basis 1024, supaya cocok dengan angka yang dilihat orang di sistem
# berkasnya sendiri.
GIB = 1024**3


def _int_env(nama, bawaan):
    """Baca angka dari lingkungan, dan JATUH KE BAWAAN kalau isinya bukan angka.

    Kuota yang gagal dibaca tidak boleh berarti kuota tak terbatas. Instance yang
    salah ketik satu variabel lingkungan sebaiknya tetap punya rem.
    """
    try:
        return int(os.environ.get(nama, bawaan))
    except (TypeError, ValueError):
        return int(bawaan)


def _bool_env(nama, bawaan="0"):
    return os.environ.get(nama, bawaan) == "1"


# None berarti TIDAK TERBATAS, bukan nol. Dibaca begitu di seluruh berkas ini.
BATAS_TINGKATAN = {
    "FREE": {
        # Perorangan. Keputusan user 28 Agt: gratis dijual per orang, dan
        # kolaborasi adalah alasan naik ke Pro. Angka 1 berarti pemiliknya
        # sudah memenuhi kursinya sendiri, jadi undangan ditolak sejak dikirim.
        "members": _int_env("FREE_MAX_MEMBERS", 1),
        "storage_bytes": _int_env("FREE_MAX_STORAGE_BYTES", 1 * GIB),
        "workspaces_per_owner": _int_env("FREE_MAX_WORKSPACES", 1),
    },
    "PRO": {"members": 30, "storage_bytes": 20 * GIB, "workspaces_per_owner": 3},
    "EXPERT": {"members": None, "storage_bytes": 200 * GIB, "workspaces_per_owner": None},
    # Enterprise memang "khusus" di rencana produk: batasnya dinegosiasikan dan
    # ditulis per baris di WorkspacePlan, bukan di sini.
    "ENTERPRISE": {"members": None, "storage_bytes": None, "workspaces_per_owner": None},
}

TINGKATAN_BAWAAN = "FREE"

# Rem 4. Mati secara bawaan, dan itu disengaja: instance pasang-sendiri sering
# jalan tanpa SMTP sama sekali, dan menyalakannya di sana berarti tidak ada yang
# bisa membuat workspace selamanya. Kolam gratis yang menyalakannya.
WAJIB_VERIFIKASI_EMAIL = _bool_env("REQUIRE_EMAIL_VERIFICATION_FOR_WORKSPACE")

# Rem 3. Hari tanpa aktivitas sebelum tiap tahap. Nol berarti tahap itu mati.
TIDUR_PERINGATAN_HARI = _int_env("DORMANT_WARN_AFTER_DAYS", 60)
TIDUR_BEKU_HARI = _int_env("DORMANT_FREEZE_AFTER_DAYS", 90)
TIDUR_TANDAI_HAPUS_HARI = _int_env("DORMANT_MARK_DELETION_AFTER_DAYS", 180)


class BatasTerlampaui(APIException):
    """Dilempar saat sebuah batas tingkatan menolak permintaan.

    Turunan APIException, dan itu keputusan yang disengaja. Kalau ia exception
    biasa, tiap pemanggil harus membungkusnya dengan try/except dan mengubahnya
    jadi Response sendiri, dan penjaga yang menuntut delapan pemanggil ingat
    sesuatu adalah penjaga yang cepat atau lambat terlewat di pemanggil
    kesembilan. Sebagai APIException ia ditangani penanganan galat bawaan DRF,
    jadi tidak ada yang perlu diingat siapa pun.

    `detail` sengaja berupa dict, bukan teks: DRF mengembalikan dict apa adanya
    sebagai badan respons, jadi bentuknya cocok dengan kebiasaan repo ini
    (`{"error": ...}`) tanpa perlu penangan galat kustom.

    `code` ikut dikirim karena klien harus bisa membedakan "kuota habis" dari
    "permintaanmu salah" untuk menawarkan naik tingkatan, dan membedakannya
    lewat pencocokan teks pesan pasti rusak begitu teksnya diterjemahkan.
    """

    status_code = 400

    def __init__(self, pesan, kode, status_code=400):
        self.status_code = status_code
        self.kode = kode
        self.pesan = pesan
        super().__init__({"error": pesan, "code": kode})


# --- Membaca tingkatan -------------------------------------------------------


def plan_for(workspace_id):
    """Baris WorkspacePlan sebuah workspace, atau None kalau belum ada.

    Tidak pernah membuat baris. Workspace tanpa baris adalah keadaan yang SAH dan
    berarti gratis, jadi tidak ada backfill yang wajib dan instance pasang-sendiri
    yang tidak peduli tingkatan tetap berjalan tanpa satu baris pun.
    """
    from plane.db.models import WorkspacePlan

    return WorkspacePlan.objects.filter(
        workspace_id=workspace_id, deleted_at__isnull=True
    ).first()


def tingkatan(workspace_id):
    baris = plan_for(workspace_id)
    return baris.tier if baris else TINGKATAN_BAWAAN


def batas(workspace_id, nama):
    """Batas efektif sebuah workspace. None berarti tidak terbatas.

    Urutannya: nilai per baris kalau diisi, kalau tidak angka bawaan
    tingkatannya. Tingkatan yang tidak dikenal diperlakukan sebagai gratis,
    karena tingkatan yang tidak dikenal biasanya berarti data rusak, dan jawaban
    yang benar untuk data rusak adalah menutup, bukan membuka.
    """
    baris = plan_for(workspace_id)
    if baris is not None:
        per_baris = getattr(baris, f"max_{nama}", None)
        if per_baris is not None:
            return per_baris
    tier = baris.tier if baris else TINGKATAN_BAWAAN
    return BATAS_TINGKATAN.get(tier, BATAS_TINGKATAN[TINGKATAN_BAWAAN])[nama]


# --- Rem 2: kuota penyimpanan ------------------------------------------------


def penyimpanan_terpakai(workspace_id):
    """Jumlah byte berkas yang BENAR-BENAR terunggah di sebuah workspace.

    Yang dihitung hanya `is_uploaded=True`. Batas atas yang diketahui: URL
    unggahan yang sudah dicetak tapi berkasnya belum masuk tidak terhitung, jadi
    seseorang yang mencetak banyak URL sekaligus bisa melewati kuota sekali.
    Dibiarkan begitu karena menghitung yang belum masuk berarti menolak orang
    karena unggahan yang mereka batalkan, dan itu kesalahan yang lebih sering
    terjadi daripada penyalahgunaannya. Kalau nanti terbukti disalahgunakan,
    tempat memperbaikinya satu: fungsi ini.
    """
    from django.db.models import Sum

    from plane.db.models import FileAsset

    total = FileAsset.objects.filter(
        workspace_id=workspace_id, is_uploaded=True, deleted_at__isnull=True
    ).aggregate(total=Sum("size"))["total"]
    return int(total or 0)


def periksa_unggahan(workspace_id, ukuran):
    """Penjaga tunggal untuk SETIAP titik yang mencetak URL unggahan.

    Melempar BatasTerlampaui kalau workspace-nya sedang dibekukan karena tidur,
    atau kalau berkas ini akan melewati kuotanya.
    """
    if workspace_id is None:
        # Aset milik pengguna (avatar, sampul) tidak menempel ke workspace mana
        # pun, jadi tidak ada kuota yang bisa ditagihkan. Ukurannya sudah dijaga
        # FILE_SIZE_LIMIT per berkas, dan jumlahnya tetap karena diganti bukan
        # ditumpuk.
        return

    baris = plan_for(workspace_id)
    if baris is not None and baris.uploads_frozen_at is not None and not bangunkan(baris):
        raise BatasTerlampaui(
            "Workspace ini dibekukan karena lama tidak dipakai. "
            "Masuk lagi lalu coba sekali lagi untuk melanjutkan mengunggah.",
            kode="WORKSPACE_DORMANT",
            status_code=409,
        )

    kuota = batas(workspace_id, "storage_bytes")
    if kuota is None:
        return

    terpakai = penyimpanan_terpakai(workspace_id)
    if terpakai + int(ukuran) > kuota:
        raise BatasTerlampaui(
            f"Kuota penyimpanan workspace habis. Terpakai {terpakai / GIB:.2f} GiB "
            f"dari {kuota / GIB:.2f} GiB.",
            kode="STORAGE_QUOTA_EXCEEDED",
            status_code=413,
        )


# --- Rem 1 & 4: pembuatan workspace ------------------------------------------


def periksa_pembuatan_workspace(user):
    """Penjaga sebelum sebuah workspace baru lahir.

    Dua rem sekaligus, karena keduanya menjaga pintu yang sama:

      rem 4  surel harus terverifikasi dulu (kalau saklarnya menyala)
      rem 1  satu akun gratis hanya boleh memiliki sejumlah workspace

    Batas yang dipakai adalah batas TERLONGGAR di antara workspace yang sudah
    dimiliki orang ini. Jadi pelanggan Pro yang juga punya workspace gratis lama
    tidak ikut terkunci oleh angka gratis, dan tidak perlu ada kolom tingkatan
    kedua yang menempel di User.
    """
    from plane.db.models import Workspace

    if WAJIB_VERIFIKASI_EMAIL and not getattr(user, "is_email_verified", False):
        raise BatasTerlampaui(
            "Verifikasi alamat surelmu dulu sebelum membuat workspace.",
            kode="EMAIL_NOT_VERIFIED",
            status_code=403,
        )

    dimiliki = list(
        Workspace.objects.filter(owner=user, deleted_at__isnull=True).values_list(
            "id", flat=True
        )
    )
    if not dimiliki:
        # Belum punya apa-apa. Yang pertama selalu boleh, apa pun angkanya, kalau
        # tidak orang baru tidak akan pernah bisa mulai.
        return

    caps = [batas(ws_id, "workspaces_per_owner") for ws_id in dimiliki]
    if any(c is None for c in caps):
        return
    if len(dimiliki) >= max(caps):
        raise BatasTerlampaui(
            f"Tingkatanmu hanya mengizinkan {max(caps)} workspace. "
            "Naikkan tingkatan atau hapus workspace yang tidak dipakai.",
            kode="WORKSPACE_LIMIT_REACHED",
            status_code=403,
        )


def kursi_terpakai(workspace_id):
    """Anggota aktif DITAMBAH undangan yang belum dijawab.

    Undangan ikut dihitung karena ia adalah kursi yang sudah dijanjikan. Kalau
    yang dihitung hanya anggota aktif, sebuah workspace yang tinggal punya satu
    kursi bisa mengirim sepuluh undangan sekaligus, dan kesepuluhnya akan
    diterima. Batas yang bisa dilewati dengan mengundang lebih banyak orang
    bukan batas.
    """
    from plane.db.models import WorkspaceMember, WorkspaceMemberInvite

    anggota = WorkspaceMember.objects.filter(
        workspace_id=workspace_id, is_active=True, deleted_at__isnull=True
    ).count()
    undangan = WorkspaceMemberInvite.objects.filter(
        workspace_id=workspace_id, responded_at__isnull=True, deleted_at__isnull=True
    ).count()
    return anggota + undangan


def periksa_penambahan_anggota(workspace_id, jumlah_baru=1):
    """Penjaga kursi. Dipanggil saat undangan DIKIRIM dan saat undangan DITERIMA.

    Dua titik, bukan satu. Menjaga hanya saat mengirim memberi umpan balik yang
    enak tapi bisa dilewati; menjaga hanya saat menerima menegakkan batasnya tapi
    membuat orang menerima undangan lalu ditolak, dan yang disalahkan orang itu
    adalah dirinya sendiri.
    """
    kuota = batas(workspace_id, "members")
    if kuota is None:
        return

    sekarang = kursi_terpakai(workspace_id)
    if sekarang + jumlah_baru > kuota:
        raise BatasTerlampaui(
            f"Tingkatan workspace ini dibatasi {kuota} anggota, dan {sekarang} kursi "
            "sudah terpakai (termasuk undangan yang belum dijawab). "
            "Naikkan tingkatan untuk mengundang lebih banyak orang.",
            kode="MEMBER_LIMIT_REACHED",
            status_code=403,
        )


def batas_ukuran_unggahan(slug, ukuran):
    """Pengganti `min(settings.FILE_SIZE_LIMIT, size)` di SETIAP titik unggahan.

    Sengaja dibuat menggantikan baris itu, bukan berdiri di sampingnya. Kuota
    yang dipasang sebagai baris tambahan adalah kuota yang lupa dipasang di titik
    berikutnya; kuota yang menjadi baris penghitung ukurannya sendiri ikut
    tersalin setiap kali orang menyalin polanya.

    Mengembalikan ukuran yang boleh dipakai, dan melempar BatasTerlampaui kalau
    workspace-nya beku atau kuotanya habis.
    """
    from django.conf import settings

    from plane.db.models import Workspace

    ukuran = int(ukuran)
    workspace_id = (
        Workspace.objects.filter(slug=slug, deleted_at__isnull=True)
        .values_list("id", flat=True)
        .first()
        if slug
        else None
    )
    periksa_unggahan(workspace_id, min(settings.FILE_SIZE_LIMIT, ukuran))
    return min(settings.FILE_SIZE_LIMIT, ukuran)


# --- Rem 3: tidur ------------------------------------------------------------


def aktivitas_terakhir(workspace_id):
    """Kapan sebuah workspace terakhir dipakai MANUSIA, atau None kalau tidak pernah.

    Diturunkan dari `User.last_active`, yang sudah dipelihara
    `middleware/last_active.py` dari lalu lintas yang memang sudah terjadi.
    Sengaja TIDAK menambah kolom stempel sendiri: menulis satu baris tiap
    permintaan hanya untuk tahu kapan workspace terakhir hidup adalah ongkos
    tetap di jalur terpanas, demi jawaban yang cuma dibaca sekali sehari.

    Hanya anggota AKTIF yang dihitung. Workspace yang seluruh anggotanya sudah
    dinonaktifkan memang tidak dipakai siapa pun, dan itu jawaban yang benar.
    """
    from django.db.models import Max

    from plane.db.models import WorkspaceMember

    return WorkspaceMember.objects.filter(
        workspace_id=workspace_id, is_active=True, deleted_at__isnull=True
    ).aggregate(terakhir=Max("member__last_active"))["terakhir"]


def bangunkan(baris):
    """Cabut status tidur kalau ternyata workspace-nya sudah dipakai lagi.

    Dipanggil dari jalur unggahan, bukan hanya dari task harian, dan itu yang
    membuat pesan galatnya jujur. Kalau pencabutan hanya terjadi di task harian,
    orang yang baru masuk lagi tetap tertolak sampai besok, padahal pesannya
    menyuruh mereka masuk lagi dan mencoba. Penjaga yang menyuruh melakukan
    sesuatu yang belum berlaku lebih buruk daripada penjaga yang diam.

    Mengembalikan True kalau memang dibangunkan.
    """
    from datetime import timedelta

    from django.utils import timezone

    if TIDUR_BEKU_HARI <= 0:
        return True

    terakhir = aktivitas_terakhir(baris.workspace_id)
    if terakhir is None:
        return False

    ambang = timezone.now() - timedelta(days=TIDUR_BEKU_HARI)
    if terakhir < ambang:
        return False

    baris.dormant_warned_at = None
    baris.uploads_frozen_at = None
    baris.pending_deletion_at = None
    baris.last_activity_at = terakhir
    baris.save(
        update_fields=[
            "dormant_warned_at",
            "uploads_frozen_at",
            "pending_deletion_at",
            "last_activity_at",
        ],
        disable_auto_set_user=True,
    )
    return True
