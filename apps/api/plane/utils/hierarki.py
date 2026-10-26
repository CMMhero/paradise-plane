# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: resolver & gerbang hierarki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu tempat untuk menjawab "siapa atasannya siapa" dan "boleh atau tidak menugaskan".

Rancangan + pertanyaan yang BELUM dijawab user: `.herdr/hierarki-desain.md`.

## Kenapa satu modul, bukan logika yang disalin ke tiap pemanggil

[[Jebakan & Pelajaran]] prinsip #1: kalau ada dua jalur ke sumber daya yang sama,
keduanya wajib sepakat. Penugasan punya **12 titik tulis** (daftarnya di rancangan §4),
dan satu serializer melayani lima di antaranya. Definisi "boleh menugaskan" yang
bercabang dua adalah cara paling rapi untuk membuat satu jalur bilang boleh dan jalur
lain bilang tidak — dan user kehilangan pekerjaannya tanpa peringatan.

## Kenapa aktornya diambil dari `crum`, bukan dari parameter wajib

`BaseModel.save()` sudah memakai `crum.get_current_user()` (`plane/db/models/base.py`),
jadi thread-local itu sudah menjadi sumber aktor untuk `created_by`/`updated_by` di
seluruh aplikasi. Memakainya di sini berarti **tidak perlu** menambahkan `request` ke
`context` serializer di lima pemanggil — dan tiap baris yang tidak ditambahkan ke berkas
upstream adalah divergensi yang tidak perlu dibayar di setiap upstream sync.

Batasnya harus disebut: kalau `crum` tidak menyetel user (mis. dijalankan dari Celery),
aktornya `None`, dan gerbangnya **menolak** (gagal ke arah aman, prinsip #3).
"""

# Python imports
import os

# Module imports
from plane.db.models import (
    JabatanOrganisasi,
    PengawasanDivisi,
    ProjectMember,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
)

__all__ = [
    "gerbang_aktif",
    "peta_tingkat",
    "tingkat_anggota",
    "divisi_anggota",
    "divisi_diawasi",
    "struktur_aktif",
    "penempatan_semua",
    "semua_departemen_ids",
    "semua_divisi_ids",
    "project_departemen",
    "project_divisi",
    "jangkauan_hierarki",
    "calon_penyetuju",
    "galat_penugasan",
    "selesai_perlu_persetujuan",
    "galat_ubah_tugas",
    "periksa_penugasan",
    "aktor_dari_context",
    "catat_persetujuan",
    "butuh_persetujuan",
    "status_persetujuan_tugas",
    "BUTUH_PERSETUJUAN",
    "TANPA_ATASAN",
]

# Nilai balik `periksa_penugasan` untuk keadaan yang BUKAN "boleh" dan BUKAN "ditolak".
# Dipakai antrean persetujuan; sengaja string supaya tidak menambah kelas baru.
BUTUH_PERSETUJUAN = "butuh-persetujuan"
TANPA_ATASAN = "tanpa-atasan"

# Nama variabel lingkungan katup darurat. Default MATI: dengan ini mati, perilaku
# 88 user TIDAK berubah satu pun.
FLAG_GERBANG = "HIERARKI_GERBANG_TUGAS"

# Periksa "member yang dia bawahi" (tingkat penerima HARUS lebih rendah)?
#
# Dinyalakan 2026-10-15 sesudah user menjawab: "manager it bawahi supervisor dan member
# it" -- jadi arah penugasan hanya boleh ke bawah. Sebelumnya sakelar ini mati karena
# jawabannya belum ada, dan menebaknya akan memblokir pekerjaan seluruh kantor.
PERIKSA_TINGKAT_PENERIMA = True


def gerbang_aktif():
    """Katup darurat. Dibaca saat dipanggil, bukan saat modul diimpor.

    Dibaca per panggilan supaya bisa dinyalakan/dimatikan tanpa membuat ulang container
    (jebakan A2: `docker compose restart` tidak membaca ulang `env_file`, jadi mengubah
    nilai ini WAJIB `up -d`).
    """
    return os.environ.get(FLAG_GERBANG, "0") == "1"


# --------------------------------------------------------------------------
# Resolver — semuanya baca-saja
# --------------------------------------------------------------------------


def aktor_dari_context(context):
    """Ambil pelaku dari `context` serializer, dengan cadangan `crum`.

    Urutannya penting dan bukan gaya-gayaan:

    1. `context["actor"]` — jalur utama. Sengaja EKSPLISIT, bukan mengandalkan
       thread-local. Alasannya ditemukan saat menguji: `crum` membaca `request.user`
       dari objek request DJANGO, sedangkan autentikasi DRF (termasuk **API token**)
       memasang user di request DRF yang dibungkus setelahnya. Di bawah autentikasi
       token, `crum` mengembalikan AnonymousUser — dan gerbang yang membaca AnonymousUser
       akan menolak SEMUA penugasan tanpa satu pun error yang menjelaskan kenapa.
       Di test harness hal yang sama terjadi dengan `force_authenticate`, jadi tanpa
       jalur eksplisit ini gerbangnya tidak bisa diuji sama sekali.
    2. `crum` — cadangan untuk pemanggil yang belum diberi `actor`, supaya jalur yang
       terlewat tetap berperilaku benar di produksi alih-alih menolak semuanya.

    None dikembalikan apa adanya; pemanggil yang memutuskan (gerbang menolak).
    """
    if context:
        actor = context.get("actor")
        if actor is not None and not getattr(actor, "is_anonymous", False):
            return actor

    from crum import get_current_user  # noqa: PLC0415

    actor = get_current_user()
    if actor is None or getattr(actor, "is_anonymous", False):
        return None
    return actor


def peta_tingkat(workspace_id):
    """{user_id: tingkat} untuk seluruh workspace, satu query.

    Dipakai resolver yang perlu membandingkan banyak orang sekaligus (mis. mencari
    calon penyetuju). Sengaja tidak difilter `is_active`: orang yang akunnya
    dinonaktifkan tetap punya jabatan, dan barisnya tetap diperlukan untuk membaca
    riwayat.

    Satu orang bisa punya beberapa baris (supervisor multi-departemen): yang dipakai
    adalah TERTINGGI. Tingkat menentukan WEWENANG, departemen menentukan CAKUPAN.
    """
    peta = {}
    for uid, tingkat in JabatanOrganisasi.objects.filter(workspace_id=workspace_id).values_list(
        "member_id", "tingkat"
    ):
        if uid not in peta or tingkat > peta[uid]:
            peta[uid] = tingkat
    return peta


def tingkat_anggota(user_id, workspace_id):
    """Tingkat satu orang, atau None kalau jenjangnya BELUM DIISI.

    None bukan 0 dan bukan TINGKAT_MEMBER. Perbedaan ini yang membuat "datanya kurang"
    tidak pernah diam-diam berubah arti jadi "dia staf".

    Multi-baris (supervisor dua departemen) menyimpan tingkat yang sama di tiap
    baris; MAX di sini pengaman kalau datanya sempat miring, bukan fitur.
    """
    if user_id is None:
        return None
    return (
        JabatanOrganisasi.objects.filter(workspace_id=workspace_id, member_id=user_id)
        .order_by("-tingkat")
        .values_list("tingkat", flat=True)
        .first()
    )


def tingkat_efektif(user_id, workspace_id):
    """Tingkat dengan bawaan staf: jabatan belum diisi dihitung MEMBER.

    Keputusan user 2026-10-26. `tingkat_anggota` tetap mengembalikan None untuk
    "belum diisi" (God Mode & laporan butuh pembedanya); fungsi ini untuk
    keputusan wewenang yang cukup tahu "setidaknya staf".
    """
    tingkat = tingkat_anggota(user_id, workspace_id)
    return TINGKAT_MEMBER if tingkat is None else tingkat


def divisi_anggota(user_id, workspace_id):
    """Set id project tempat orang ini benar-benar anggota (keanggotaan hidup)."""
    if user_id is None:
        return set()
    return set(
        ProjectMember.objects.filter(
            workspace_id=workspace_id,
            member_id=user_id,
            is_active=True,
            deleted_at__isnull=True,
        ).values_list("project_id", flat=True)
    )


def struktur_aktif(workspace_id):
    """True kalau workspace ini sudah memakai struktur divisi -> departemen (KEP-29).

    Sakelarnya DATA, bukan env: selama belum ada satu pun `Divisi`, seluruh resolver
    jatuh ke perilaku lama (jangkauan = keanggotaan project), jadi 88 orang tidak
    berubah apa-apa sampai struktur benar-benar diisi di God Mode.
    """
    from plane.db.models import Divisi  # noqa: PLC0415

    return Divisi.objects.filter(workspace_id=workspace_id).exists()


def penempatan_semua(user_id, workspace_id):
    """Semua baris penempatan satu orang: [(tingkat, departemen_id, divisi_id)].

    Supervisor multi-departemen punya satu baris per departemen (keputusan user
    2026-10-23: tidak ada lagi "utama" vs "tambahan"). Kosong = jenjang belum diisi.
    """
    if user_id is None:
        return []
    return list(
        JabatanOrganisasi.objects.filter(workspace_id=workspace_id, member_id=user_id)
        .order_by("-tingkat", "departemen_id", "divisi_id")
        .values_list("tingkat", "departemen_id", "divisi_id")
    )


def project_departemen(departemen_id):
    """Set id project hidup milik satu departemen."""
    from plane.db.models import DepartemenProject  # noqa: PLC0415

    if departemen_id is None:
        return set()
    return set(
        DepartemenProject.objects.filter(departemen_id=departemen_id, project__deleted_at__isnull=True).values_list(
            "project_id", flat=True
        )
    )


def semua_departemen_ids(user_id, workspace_id):
    """Id SEMUA departemen tempat orang ini ditempatkan (gabungan semua barisnya)."""
    return {dept for _, dept, _ in penempatan_semua(user_id, workspace_id) if dept}


def semua_divisi_ids(user_id, workspace_id):
    """Id SEMUA divisi tempat orang ini ditempatkan (gabungan semua barisnya)."""
    return {div for _, _, div in penempatan_semua(user_id, workspace_id) if div}


def project_divisi(divisi_id):
    """Set id project hidup di semua departemen satu divisi."""
    from plane.db.models import DepartemenProject  # noqa: PLC0415

    if divisi_id is None:
        return set()
    return set(
        DepartemenProject.objects.filter(
            departemen__divisi_id=divisi_id,
            departemen__deleted_at__isnull=True,
            project__deleted_at__isnull=True,
        ).values_list("project_id", flat=True)
    )


def _semua_project(workspace_id):
    from plane.db.models import Project  # noqa: PLC0415 — hindari impor melingkar

    return set(Project.objects.filter(workspace_id=workspace_id, deleted_at__isnull=True).values_list("id", flat=True))


def jangkauan_hierarki(user_id, workspace_id):
    """{project_id: role} yang WAJIB dimiliki orang ini menurut hierarki (KEP-29).

    Ini sisi LIHAT, bukan sisi wewenang (itu `divisi_diawasi`):

        direktur   -> semua project, role 20
        manager    -> semua project di divisinya (semua baris divisinya), role 20
        supervisor -> project SEMUA departemennya, role 20
        staf       -> project departemennya, role 15 (lihat semua, edit hanya
                      tugas miliknya: `galat_ubah_tugas`)

    Kosong kalau struktur belum aktif atau jenjangnya belum diisi.
    """
    if user_id is None or not struktur_aktif(workspace_id):
        return {}
    baris = penempatan_semua(user_id, workspace_id)
    if not baris:
        return {}
    tingkat = max(t for t, _, _ in baris)
    if tingkat >= TINGKAT_DIREKTUR:
        return {pid: 20 for pid in _semua_project(workspace_id)}
    if tingkat >= TINGKAT_MANAGER:
        pids = set()
        for div_id in semua_divisi_ids(user_id, workspace_id):
            pids |= project_divisi(div_id)
        return {pid: 20 for pid in pids}
    role = 20 if tingkat >= TINGKAT_SUPERVISOR else 15
    if tingkat >= TINGKAT_SUPERVISOR:
        # Supervisor boleh ditempatkan di beberapa departemen (2026-10-23):
        # satu baris jabatan per departemen, jangkauan = gabungan semuanya.
        pids = set()
        for dep_id in semua_departemen_ids(user_id, workspace_id):
            pids |= project_departemen(dep_id)
        return {pid: role for pid in pids}
    pids = set()
    for dep_id in semua_departemen_ids(user_id, workspace_id):
        pids |= project_departemen(dep_id)
    return {pid: role for pid in pids}


def divisi_diawasi(user_id, workspace_id):
    """Set id project yang diawasi orang ini ("divisi yang dia bawahi").

    Dengan struktur aktif (KEP-29) jawabannya datang dari hierarki, BUKAN dari
    keanggotaan project: supervisor = project SEMUA departemennya, manager =
    project divisinya, direktur = semua (dibatasi baris `PengawasanDivisi` kalau
    ada). Keanggotaan project eksplisit memberi akses kolaborasi, tidak memberi
    wewenang.

    Tanpa struktur, perilaku lama di bawah ini yang berlaku.

    Dua sumber, dan urutannya penting:

    1. **Baris eksplisit** di `PengawasanDivisi`. Untuk **direktur**, baris ini
       MEMBATASI: kosong = semua divisi, terisi = hanya divisi yang ditulis.
       Untuk supervisor/manager, baris ini tidak menambah kewenangan lintas divisi
       (keputusan user: "tidak cross divisi kecuali direktur").
    2. **Rumus jenjang**, kalau tidak ada baris sama sekali:
         direktur   -> semua divisi di workspace
         manager    -> divisi tempat ia memang anggota
         supervisor -> divisi tempat ia memang anggota
       Tanpa rumus ini, sistem BUNTU sebelum ada yang mengisi tabel: direktur tidak bisa
       apa-apa, padahal kata user "direktur bisa create task cross divisi manapun
       karena tingkat teratas".

    Kosong dikembalikan apa adanya (bukan buntu) kalau orangnya bukan siapa-siapa.
    """
    if user_id is None:
        return set()

    eksplisit = set(
        PengawasanDivisi.objects.filter(workspace_id=workspace_id, member_id=user_id).values_list(
            "project_id", flat=True
        )
    )
    baris = penempatan_semua(user_id, workspace_id)
    tingkat = max((t for t, _, _ in baris), default=None)

    if tingkat is not None and tingkat >= TINGKAT_DIREKTUR:
        # Direktur: semua divisi, KECUALI kalau ada baris eksplisit -- di situ ia
        # dibatasi ke divisi yang ditulis (mis. direktur operasional hanya 12 divisi).
        if eksplisit:
            return eksplisit
        return _semua_project(workspace_id)

    if tingkat is None:
        return set()

    if struktur_aktif(workspace_id):
        if tingkat >= TINGKAT_MANAGER:
            pids = set()
            for div_id in semua_divisi_ids(user_id, workspace_id):
                pids |= project_divisi(div_id)
            return pids
        if tingkat >= TINGKAT_SUPERVISOR:
            pids = set()
            for dep_id in semua_departemen_ids(user_id, workspace_id):
                pids |= project_departemen(dep_id)
            return pids
        return set()

    # Supervisor DAN manager: HANYA divisi tempat ia memang anggota.
    #
    # Keputusan user 2026-10-15: "tidak cross divisi kecuali direktur" dan "manager it
    # bawahi supervisor dan member it". Baris `PengawasanDivisi` karena itu TIDAK
    # menambah kewenangan lintas divisi bagi mereka -- dan itu memang maksudnya: satu
    # baris salah isi (atau warisan) tidak boleh memberi kewenangan yang tidak diminta,
    # terlebih kegagalannya akan senyap.
    if tingkat >= TINGKAT_SUPERVISOR:
        return divisi_anggota(user_id, workspace_id)

    return set()


def calon_penyetuju(workspace_id, project_id, tingkat_pembuat=None):
    """Orang-orang yang boleh menyetujui penugasan di project ini.

    Aturannya (rancangan §5.4): tingkat **lebih tinggi** dari pembuat DAN mengawasi
    divisi tempat tugas itu berada. Sengaja BUKAN "atasan langsung": tabel jenjang +
    pengawasan tidak bisa menjawab siapa atasan langsung siapa, dan menebaknya berarti
    memilih garis komando yang tidak pernah ada di data.

    `tingkat_pembuat=None` berarti jenjang pembuat belum diisi. Dalam keadaan itu
    SEMUA orang yang mengawasi divisi itu dianggap calon penyetuju — lebih baik
    daripada tidak ada seorang pun, karena yang terakhir itu membuat penugasan
    menggantung tanpa jalan keluar.
    """
    if project_id is None:
        return []

    peta = peta_tingkat(workspace_id)
    kandidat = [uid for uid, tingkat in peta.items() if tingkat >= TINGKAT_SUPERVISOR]
    if tingkat_pembuat is not None:
        kandidat = [uid for uid in kandidat if peta[uid] > tingkat_pembuat]

    hasil = []
    for uid in kandidat:
        if project_id in divisi_diawasi(uid, workspace_id):
            hasil.append(uid)
    return sorted(hasil, key=lambda uid: -peta[uid])


# --------------------------------------------------------------------------
# Gerbang penugasan
# --------------------------------------------------------------------------


def _pesan_tolak(tingkat, nama_divisi):
    if tingkat is None:
        return (
            "Jenjang Anda belum diisi, jadi untuk sementara Anda hanya boleh "
            "menugaskan pekerjaan kepada diri sendiri. Hubungi IT untuk mengisi jenjang Anda."
        )
    if tingkat < TINGKAT_SUPERVISOR:
        return (
            "Anggota hanya boleh menugaskan pekerjaan kepada diri sendiri. "
            f"Divisi {nama_divisi} berada di luar divisi yang Anda awasi."
        )
    return f"Divisi {nama_divisi} berada di luar divisi yang Anda awasi."


def galat_penugasan(project_id, assignee_ids, actor=None, abaikan_katup=False):
    """Periksa satu penugasan. Kembalikan pesan galat, atau None kalau boleh.

    Sengaja mengembalikan pesan, bukan melempar: pemanggilnya serializer DRF (yang
    perlu `ValidationError`), skrip, dan tes — dan tiap pemanggil perlu bentuk galat
    yang berbeda. Yang TIDAK boleh berbeda adalah keputusannya.

    `abaikan_katup=True` dipakai census dan tes: keduanya harus bisa menjawab "apa yang
    AKAN terjadi kalau katupnya dinyalakan" tanpa benar-benar menyalakannya untuk 88
    orang. Tanpa ini, census cuma bisa melaporkan "gerbang mati, tidak ada yang terjadi".

    Urutan pemeriksaan penting: gerbang mati diperiksa paling depan, supaya dengan
    katup tertutup fungsi ini tidak menyentuh database sama sekali.
    """
    if not abaikan_katup and not gerbang_aktif():
        return None

    # Tugas tanpa penerima tidak pernah butuh persetujuan: approval melekat pada
    # PENUGASAN, bukan pada pembuatan tugas (kata user: "hanya bisa assign diri sendiri,
    # dan harus di approve").
    assignee_ids = [a for a in (assignee_ids or []) if a is not None]
    if not assignee_ids:
        return None

    # Aktor tidak diketahui -> gagal ke arah aman (prinsip #3).
    if actor is None:
        return "Pelaku penugasan tidak diketahui, jadi penugasan ini tidak dapat diverifikasi."

    from plane.db.superadmin import is_super_admin  # noqa: PLC0415

    if is_super_admin(actor):
        # Super Admin mengurus sistem dan sudah punya akses ke seluruh project (B1).
        # Catatannya: kewenangan ini di luar tangga divisi, jadi ia tidak diperiksa
        # terhadap divisi apa pun. Pertanyaan #7 menanyakan apakah ini yang diinginkan.
        return None

    dari_id = {getattr(actor, "id", None)}
    if set(assignee_ids) <= dari_id:
        # Assign diri sendiri SELALU boleh. Yang BELUM dibangun adalah antrean
        # persetujuannya (arti "approve" belum diputuskan — pertanyaan #5), jadi
        # sengaja tidak ada efek samping di sini.
        return None

    from plane.db.models import Project  # noqa: PLC0415

    project = Project.objects.filter(pk=project_id, deleted_at__isnull=True).first()
    if project is None:
        return "Project tujuan tidak ditemukan."

    workspace_id = project.workspace_id

    # Kolaborasi staf: boleh menambah rekan setingkat di departemen yang sama,
    # tapi dirinya sendiri WAJIB tetap ada (staf hanya membuat tugasnya sendiri).
    if _adalah_staf(actor.id, workspace_id):
        return _galat_kolaborasi_staf(actor.id, workspace_id, project_id, assignee_ids)

    # Batas KEP-02: orang luar divisi memang tidak boleh menugaskan ke dalamnya.
    # Jalur REST sudah menolaknya lebih dulu; ini pertahanan kedua supaya jalur yang
    # tidak lewat REST (mis. skrip) tidak berbeda pendapat.
    if project_id not in divisi_anggota(actor.id, workspace_id):
        return f"Anda bukan anggota divisi {project.identifier}, jadi tidak dapat menugaskan pekerjaan di sana."

    tingkat = tingkat_anggota(actor.id, workspace_id)

    if tingkat is not None and tingkat >= TINGKAT_DIREKTUR:
        # "direktur bisa create task cross divisi manapun karena tingkat teratas".
        return None

    if project_id in divisi_diawasi(actor.id, workspace_id):
        if PERIKSA_TINGKAT_PENERIMA:
            peta = peta_tingkat(workspace_id)
            for uid in assignee_ids:
                if uid in dari_id:
                    continue
                lain = peta.get(uid)
                if lain is not None and lain >= (tingkat or TINGKAT_MEMBER):
                    return (
                        "Penerima tugas berada pada jenjang yang sama atau lebih tinggi "
                        "dari Anda, jadi ia bukan bawahan yang dapat Anda tugaskan."
                    )
        return None

    return _pesan_tolak(tingkat, project.identifier)


def _adalah_staf(user_id, workspace_id):
    tingkat = tingkat_anggota(user_id, workspace_id)
    return tingkat is None or tingkat < TINGKAT_SUPERVISOR


def _galat_kolaborasi_staf(actor_id, workspace_id, project_id, assignee_ids):
    """Aturan staf: diri sendiri wajib ada; rekan = staf setingkat di departemen yang sama.

    Tanpa jabatan = staf (keputusan user 2026-10-26), jadi dua orang yang belum
    diisi jabatannya dihitung setingkat. Syarat departemen yang sama tetap berlaku.
    """
    if actor_id not in assignee_ids:
        return "Staf tidak dapat melepas dirinya sendiri dari tugas yang ia buat."
    rekan = set(assignee_ids) - {actor_id}
    if not rekan:
        return None
    tingkat = tingkat_efektif(actor_id, workspace_id)
    peta = peta_tingkat(workspace_id)
    dept_saya = semua_departemen_ids(actor_id, workspace_id)
    for uid in rekan:
        if peta.get(uid, TINGKAT_MEMBER) != tingkat:
            return "Staf hanya boleh mengajak rekan yang jabatannya sama."
        if not (dept_saya & semua_departemen_ids(uid, workspace_id)):
            return "Rekan harus berada di departemen yang sama dengan Anda."
        if project_id not in divisi_anggota(uid, workspace_id):
            return "Rekan harus anggota project ini."
    return None


def rekan_staf_ids(actor_id, workspace_id, project_id):
    """Id rekan yang boleh diajak staf: setingkat, satu departemen, anggota project ini."""
    tingkat = tingkat_efektif(actor_id, workspace_id)
    if tingkat >= TINGKAT_SUPERVISOR:
        return set()
    dept_saya = semua_departemen_ids(actor_id, workspace_id)
    if not dept_saya:
        return set()
    peta = peta_tingkat(workspace_id)
    # Kandidat = yang ditempatkan di departemen yang sama (tanpa jabatan = staf).
    kandidat = set(
        JabatanOrganisasi.objects.filter(workspace_id=workspace_id, departemen_id__in=dept_saya).values_list(
            "member_id", flat=True
        )
    )
    return {
        uid
        for uid in kandidat
        if uid != actor_id
        and peta.get(uid, TINGKAT_MEMBER) == tingkat
        and project_id in divisi_anggota(uid, workspace_id)
    }


def _bawahan_ids(actor_id, workspace_id, project_id):
    """Id bawahan actor di divisi ini: diawasi actor + bukan setingkat/lebih tinggi.

    Dua sumber, dan keduanya: (a) tingkat lebih rendah, (b) jenjang BELUM DIISI
    tapi anggota divisi ini. (b) karena "belum diisi" BUKAN "bukan bawahan":
    gerbang `galat_penugasan` memang mengizinkan atasan menugaskan ke mereka
    (hanya menolak penerima yang JELAS setingkat/lebih tinggi), jadi
    menyembunyikannya dari dropdown berarti dropdown berbohong tentang apa
    yang server izinkan. Pengecualian: actor sendiri, dan anggota di divisi
    yang tidak diawasi actor.
    """
    if actor_id is None:
        return set()
    peta = peta_tingkat(workspace_id)
    tingkat_actor = peta.get(actor_id)
    if tingkat_actor is None or tingkat_actor < TINGKAT_SUPERVISOR:
        return set()
    # Normalisasi ke string: pemanggil dari URL (kwargs) membawa UUID sebagai
    # string, pemanggil dari serializer membawa objek UUID — tanpa ini
    # perbandingan `in` selalu gagal dan atasan tidak pernah punya bawahan
    # (bug kedua 2026-10-16; ditemukan karena tes unit lolos tapi endpoint tidak).
    target = str(project_id)
    bawahan = set()
    diawasi_actor = {str(p) for p in divisi_diawasi(actor_id, workspace_id)}
    if target not in diawasi_actor:
        return set()
    # `diawasi_actor` hanya berisi project workspace ini (resolver memfilter
    # workspace_id), jadi lolos dari cek di atas berarti project-nya valid —
    # tidak perlu fetch Project tambahan.
    for uid, tingkat in peta.items():
        if (
            uid != actor_id
            and tingkat < tingkat_actor
            and target in {str(p) for p in divisi_anggota(uid, workspace_id)}
        ):
            # Syarat DUA arah yang benar: penerima (a) tingkatnya di bawah
            # actor, (b) ANGGOTA divisi ini, (c) divisi ini diawasi actor
            # (diperiksa sekali di atas). Sebelumnya (b) salah memeriksa
            # "divisi yang DIAWASI bawahan" — member tidak mengawasi apa pun,
            # jadi member tidak pernah muncul sebagai bawahan (bug 2026-10-16).
            bawahan.add(uid)
    # Anggota divisi ini yang jenjangnya BELUM DIISI: bukan atasan (tidak ada
    # di peta), bukan actor, dan hanya kalau actornya supervisor+ di divisi
    # yang dia awasi (diperiksa di atas). Lihat docstring kenapa termasuk.
    anggota = set(
        ProjectMember.objects.filter(
            workspace_id=workspace_id, project_id=project_id, is_active=True, deleted_at__isnull=True
        ).values_list("member_id", flat=True)
    )
    for uid in anggota:
        if uid != actor_id and uid not in peta:
            bawahan.add(uid)
    return bawahan


def selesai_perlu_persetujuan(project_id, actor, state_baru, penerima_ids):
    """True kalau perpindahan ke status selesai ini harus DITAHAN untuk persetujuan.

    Keputusan user 2026-10-26 (menggantikan 2026-10-24): persetujuan TIDAK
    diminta saat tugas dibuat. Ia baru muncul saat assignee staf menggeser
    progres ke selesai. Perpindahan itu tidak ditolak, tapi ditahan: tugas tetap
    di status semula, pengajuan dibuat (`catat_persetujuan`), dan atasan yang
    menyelesaikannya lewat setujui. Supervisor/manager/direktur/Super Admin
    menyelesaikan langsung (`butuh_persetujuan` hanya benar untuk staf).

    Berlaku saat create (langsung-done) maupun update (pindah status). Persetujuan
    lama TIDAK dipakai ulang: setujui sendiri yang memindahkan tugas ke selesai,
    jadi tugas yang dibuka lalu diselesaikan lagi diajukan lagi.
    """
    if not gerbang_aktif() or actor is None or state_baru is None:
        return False
    group = getattr(state_baru, "group", None)
    if group is None:
        from plane.db.models import State  # noqa: PLC0415

        group = State.objects.filter(pk=state_baru).values_list("group", flat=True).first()
    if group != "completed":
        return False

    from plane.db.superadmin import is_super_admin  # noqa: PLC0415

    if is_super_admin(actor):
        return False
    return butuh_persetujuan(actor, project_id, penerima_ids or [])

# (Dihapus 2026-10-24: tidak ada lagi kunci tulis. Persetujuan hanya di
# gerbang selesai -- `selesai_perlu_persetujuan` di atas. Lihat riwayat git untuk
# `galat_terkunci` / `KunciPersetujuanMixin` / masa susun.)


def galat_ubah_tugas(project_id, issue, actor=None, mengubah_assignee=False, abaikan_katup=False):
    """Bolehkah actor mengubah tugas ini? Kembalikan pesan galat atau None.

    Keputusan user: member hanya boleh mengerjakan tugas yang di-assign ke
    dirinya; supervisor/manager/direktur boleh mengubah tugas bawahannya
    (siapa pun yang tingkatnya lebih rendah di divisi yang dia awasi).

    - Super Admin: selalu boleh (B1).
    - Supervisor+: boleh kalau ia pembuat/assignee tugas ini, ATAU assignee-nya
      termasuk bawahannya.
    - Member (dan jenjang belum diisi): hanya kalau ia assignee tugas ini.
    - `mengubah_assignee=True`: DITOLAK untuk semua orang KECUALI atasan yang
      berwenang menugaskan ulang (supervisor+ atas bawahannya, direktur di
      mana pun ia anggota). Member tidak bisa mengubah assignee SAMA SEKALI —
      bahkan miliknya sendiri (auto-assign saat create sudah menanganinya).
    """
    if not abaikan_katup and not gerbang_aktif():
        return None
    if actor is None:
        return "Pelaku perubahan tidak diketahui, jadi perubahan ini tidak dapat diverifikasi."
    if issue is None:
        return None

    from plane.db.superadmin import is_super_admin  # noqa: PLC0415

    if is_super_admin(actor):
        return None

    from plane.db.models import Project  # noqa: PLC0415

    project = Project.objects.filter(pk=project_id, deleted_at__isnull=True).first()
    if project is None:
        return "Project tujuan tidak ditemukan."
    workspace_id = project.workspace_id
    tingkat = tingkat_anggota(actor.id, workspace_id)

    assignee_ids = set(issue.issue_assignee.values_list("assignee_id", flat=True))
    saya_terlibat = actor.id in assignee_ids or issue.created_by_id == actor.id

    if mengubah_assignee:
        # Kewenangan menugaskan ulang = kewenangan `galat_penugasan` (siapa boleh
        # menugaskan ke siapa). Pemeriksaan NILAI barunya ada di serializer
        # validate() yang jalan sesudah gate ini — di sini hanya dipastikan
        # yang menyentuh assignee memang bukan staf terkunci. Supervisor+ dan
        # direktur lolos dari gate ini, lalu nilai barunya tetap diperiksa di
        # sana (atasan tidak bisa assign ke orang setingkat/lebih tinggi, dan
        # tidak bisa di luar divisinya).
        if tingkat is not None and tingkat >= TINGKAT_SUPERVISOR:
            return None
        return (
            "Penugasan tugas ini dikunci. Minta atasan Anda untuk mengubahnya "
            "kalau memang perlu dipindahkan."
        )

    # Bukan assignee: staf tidak boleh menyentuh tugas orang lain.
    if saya_terlibat:
        return None
    if tingkat is not None and tingkat >= TINGKAT_SUPERVISOR:
        if assignee_ids <= _bawahan_ids(actor.id, workspace_id, project_id):
            return None
        # Atasan di divisi yang sama tapi tugasnya milik orang setingkat/lebih
        # tinggi: tetap ditolak, supaya supervisor tidak saling mengedit.
        if project_id in divisi_diawasi(actor.id, workspace_id):
            return (
                "Tugas ini dipegang orang yang bukan bawahan Anda, "
                "jadi Anda tidak dapat mengubahnya."
            )
    nama = getattr(project, "identifier", "") or "divisi ini"
    return f"Anda tidak terlibat di tugas ini ({nama}), jadi tidak dapat mengubahnya."


def periksa_penugasan(project_id, assignee_ids, actor=None, abaikan_katup=False):
    """Versi yang bisa dibaca pemanggil non-serializer.

    Kembalikan salah satu dari: None (boleh) · BUTUH_PERSETUJUAN · TANPA_ATASAN ·
    pesan galat (ditolak). Belum dipakai irisan pertama — ini tempat antrean
    persetujuan akan masuk, dan sengaja ditulis sekarang supaya keputusannya ada di
    SATU tempat, bukan di view.
    """
    galat = galat_penugasan(project_id, assignee_ids, actor=actor, abaikan_katup=abaikan_katup)
    if galat:
        return galat
    if (not abaikan_katup and not gerbang_aktif()) or actor is None:
        return None

    from plane.db.models import Project  # noqa: PLC0415

    project = Project.objects.filter(pk=project_id).first()
    if project is None:
        return None

    diterima = [a for a in (assignee_ids or []) if a is not None]
    if not diterima:
        return None  # tugas tanpa penerima: tidak ada penugasan yang perlu disetujui

    workspace_id = project.workspace_id
    tingkat = tingkat_anggota(actor.id, workspace_id)

    # Kalau sampai di sini, `galat_penugasan` sudah menyatakan "boleh". Yang tersisa
    # adalah pertanyaan KEDUA: bolehnya langsung, atau menunggu persetujuan?
    #
    # Kata user: "normal member bisa create task, tapi hanya bisa assign diri sendiri,
    # dan harus di approve oleh orang yang satu tingkat diatas atau lebih." Jadi
    # - assign diri sendiri oleh member  -> BUTUH PERSETUJUAN (di sinilah letaknya)
    # - assign diri sendiri oleh supervisor+ -> langsung
    # - menugaskan orang lain -> hanya supervisor+ di divisi yang diawasi, dan
    #   `galat_penugasan` sudah memutuskannya, jadi di sini langsung.
    # Staf boleh juga mengajak rekan (kolaborasi); tetap butuh persetujuan.
    if not butuh_persetujuan(actor, project_id, diterima):
        return None

    if calon_penyetuju(workspace_id, project_id, tingkat_pembuat=tingkat):
        return BUTUH_PERSETUJUAN
    # Tidak ada seorang pun yang bisa menyetujui. BUKAN "ditolak": tugasnya tetap boleh
    # dibuat -- kalau ditolak, kekosongan data organisasi berubah jadi larangan bekerja --
    # tapi hasilnya WAJIB berlabel supaya tidak menggantung tanpa ada yang tahu.
    #
    # Keputusan user 2026-10-15 untuk keadaan ini: "buat atasan dan assign jabatan",
    # yaitu ditutup dari sisi DATA lewat God Mode, bukan dengan memblokir orangnya.
    return TANPA_ATASAN


def butuh_persetujuan(actor, project_id, assignee_ids):
    """True hanya untuk kasus yang user sebut: **member** menugaskan ke DIRINYA sendiri.

    Keputusan user 2026-10-15: "approval dari atasan pembuat (khusus yang jabatan member
    saja)". Jadi supervisor/manager/direktur -- walau menugaskan ke dirinya sendiri --
    tidak menghasilkan permintaan persetujuan. Dan karena member memang hanya boleh
    menugaskan ke dirinya sendiri, keadaan itu satu-satunya yang perlu disetujui.
    """
    if actor is None:
        return False
    diterima = [a for a in (assignee_ids or []) if a is not None]
    # Staf yang ikut jadi assignee (sendiri atau bersama rekan) = butuh persetujuan.
    # Siapa saja rekan yang sah sudah diputuskan `galat_penugasan`.
    if getattr(actor, "id", None) not in diterima:
        return False

    from plane.db.models import Project  # noqa: PLC0415

    project = Project.objects.filter(pk=project_id).first()
    if project is None:
        return False

    return _adalah_staf(actor.id, project.workspace_id)


def catat_persetujuan(issue, actor=None):
    """Buat baris persetujuan kalau penugasan ini memang butuh persetujuan.

    Dipanggil SESUDAH tugasnya tersimpan, dari `create()`/`update()` serializer -- jadi
    ia berjalan di semua jalur yang memakai serializer itu, bukan cuma di satu view.

    Mengembalikan barisnya, atau None. Aman dipanggil berkali-kali: kalau sudah ada baris
    menunggu untuk tugas itu, ia tidak membuat yang kedua (dan constraint parsial di
    model menutupnya juga kalau ada balapan).
    """
    if issue is None or not gerbang_aktif():
        return None
    if actor is None:
        return None

    penerima_ids = list(issue.issue_assignee.values_list("assignee_id", flat=True))
    if not butuh_persetujuan(actor, issue.project_id, penerima_ids):
        return None

    from plane.db.models import PersetujuanPenugasan, STATUS_PERSETUJUAN_MENUNGGU  # noqa: PLC0415

    sudah = PersetujuanPenugasan.objects.filter(issue_id=issue.id, status=STATUS_PERSETUJUAN_MENUNGGU).first()
    if sudah:
        return sudah

    baris = PersetujuanPenugasan.objects.create(
        workspace_id=issue.workspace_id,
        project_id=issue.project_id,
        issue_id=issue.id,
        pemohon=actor,
        penerima=actor,
    )
    # Inbox + email ke atasan yang boleh memutuskan (KEP-30 lanjutan).
    # Menelan galat sendiri di dalam — pengajuan tidak boleh gagal hanya
    # karena pemberitahuannya gagal.
    from plane.utils.notifikasi_persetujuan import beritahu_diajukan  # noqa: PLC0415

    beritahu_diajukan(baris, issue=issue)
    return baris


def status_persetujuan_tugas(issue_id):
    """Status persetujuan terakhir sebuah tugas: menunggu/disetujui/ditolak/None.

    Dibaca dari baris `PersetujuanPenugasan` TERBARU (keputusan final menutup
    baris menunggu, jadi yang terbaru adalah kebenaran saat ini). None =
    tidak pernah butuh persetujuan (tugas atasan, atau gerbang mati saat dibuat).
    Dipakai serializer read supaya kartu & sidebar bisa menampilkan badge
    tanpa request tambahan per baris.
    """
    if issue_id is None:
        return None
    from plane.db.models import PersetujuanPenugasan  # noqa: PLC0415

    baris = (
        PersetujuanPenugasan.objects.filter(issue_id=issue_id)
        .order_by("-created_at")
        .values_list("status", flat=True)
        .first()
    )
    return baris
