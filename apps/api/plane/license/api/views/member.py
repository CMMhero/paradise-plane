# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kelola member di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.core.paginator import Paginator
from django.db.models import Q

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.db.models import Profile, Session, User, UserNotificationPreference, Workspace, WorkspaceMember
from plane.db.models.workspace import ROLE_CHOICES
from plane.db.superadmin import sinkronkan_super_admin, super_admin_user_ids
from plane.license.api.views.base import BaseAPIView
from plane.license.models import Instance, InstanceAdmin

_DEFAULT_PER_PAGE = 50
_MAX_PER_PAGE = 200
_PANJANG_PASSWORD_MIN = 8
_PERAN_SAH = {nilai for nilai, _ in ROLE_CHOICES}

# Pengaturan pribadi yang boleh diubah Super Admin atas nama orang lain.
# Daftar putih, bukan `fields = "__all__"`: Profile juga memuat status onboarding,
# alamat tagihan, dan kolom lain yang bukan urusan admin.
_BAHASA_SAH = frozenset(
    {"en", "fr", "es", "ja", "zh-CN", "zh-TW", "ru", "it", "cs", "sk", "de", "ua", "pl", "ko", "pt-BR", "id", "ro", "vi-VN", "tr-TR"}
)  # cermin packages/i18n/src/constants/language.ts
_MODE_NOTIFIKASI_SAH = {nilai for nilai, _ in Profile.NotificationViewMode.choices}
_HARI_PEKAN_SAH = {nilai for nilai, _ in Profile.START_OF_THE_WEEK_CHOICES}
_SAKLAR_NOTIFIKASI = (
    "property_change",
    "state_change",
    "comment",
    "mention",
    "issue_completed",
    "approval",
    "daily_digest",
)
_SAKLAR_PROFIL = ("is_smooth_cursor_enabled", "is_app_rail_docked")

_URUTAN = {
    "name": "display_name",
    "email": "email",
    "last_active": "-last_active",
    "last_login": "-last_login_time",
    "created": "-created_at",
}


def _uname(email):
    """Pola username di repo ini: email dengan '.' dan '@' jadi '_'."""
    return email.replace(".", "_").replace("@", "_")


def _pecah_nama(nama):
    """`display_name` satu kolom → `first_name` + `last_name`.

    Dipakai bersama oleh buat-akun dan ubah-nama supaya keduanya tidak pernah
    memecah nama dengan aturan yang berbeda.
    """
    bagian = nama.split()
    return bagian[0], " ".join(bagian[1:]) if len(bagian) > 1 else ""


# Frasa konfirmasi ketik-ulang untuk MEMBERI Super Admin (keputusan user
# 2026-10-22, menggantikan passphrase `SUPER_ADMIN_GRANT_PASSPHRASE`).
# Keduanya diterima apa pun bahasa UI pemanggil: yang diperiksa BUKAN bahasa,
# melainkan niat eksplisit — mengetik frasa tidak bisa terjadi karena salah
# klik. Normalisasi (huruf kecil, spasi tunggal) supaya "JADIKAN  SUPERADMIN"
# yang sah tidak ditolak karena caps-lock atau spasi ganda.
_KONFIRMASI_GRANT = frozenset({"jadikan superadmin", "make superadmin"})


def _normalisasi_konfirmasi(nilai):
    return " ".join(str(nilai or "").casefold().split())


def _tolak_tanpa_konfirmasi_ketik(request):
    """Periksa konfirmasi ketik-ulang untuk MEMBERI Super Admin.

    Balikkan `Response` kalau ditolak, `None` kalau lolos.

    Punya God Mode saja tidak cukup: status Super Admin membuka akses ke SELURUH
    project sekaligus, jadi aksi itu minta konfirmasi sekali lagi — berupa
    frasa yang DIKETIK pemanggil, bukan rahasia bersama dari environment.
    """
    if _normalisasi_konfirmasi(request.data.get("grant_confirm")) not in _KONFIRMASI_GRANT:
        return Response(
            {"error": "Ketik 'jadikan superadmin' persis untuk memberi Super Admin."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _workspace_utama():
    """Workspace tertua yang belum dihapus = workspace produksi.

    `Workspace.objects.first()` tanpa order mengikuti `Meta.ordering`
    (`-created_at`) = yang TERBARU. Memakainya di sini:
      memecah placeholder UI, dan menulis peran ke workspace yang salah.
    Satu-satunya definisi yang dipakai endpoint ini.
    """
    return Workspace.objects.filter(deleted_at__isnull=True).order_by("created_at").first()


def _akhiri_sesi(user_id):
    """Buang semua sesi milik satu user.

    WAJIB dipanggil sesudah password atau email berubah. Tanpa ini, sesi lama
    tetap sah: orang yang passwordnya baru saja direset masih bisa memakai tab
    yang sudah terbuka, dan itu membuat reset password kehilangan gunanya.

    `Session.user_id` di repo ini `CharField` ber-index (SESSION_ENGINE kustom,
    bukan `django_session`, jebakan D2), jadi cocokkan sebagai string.
    """
    return Session.objects.filter(user_id=str(user_id)).delete()[0]


def _keanggotaan(user_ids):
    """user_id -> (peran, slug) keanggotaan workspace AKTIF orang itu.

    Hanya yang aktif: keanggotaan lama yang dinonaktifkan saat dipindah
    workspace tidak boleh terbaca sebagai workspace-nya. Kalau ternyata aktif
    di beberapa workspace, yang tertua menang (konsisten dengan `_workspace_utama`).
    """
    hasil = {}
    for uid, peran, slug in (
        WorkspaceMember.objects.filter(member_id__in=user_ids, is_active=True, workspace__deleted_at__isnull=True)
        .order_by("workspace__created_at")
        .values_list("member_id", "role", "workspace__slug")
    ):
        hasil.setdefault(uid, (peran, slug))
    return hasil


def _serialize(u, super_admin_ids, ws, sesi_hidup=None, batas_aktif=None):
    """`sesi_hidup` = himpunan user_id (string) yang punya sesi belum kedaluwarsa.

    Dihitung SEKALI untuk seluruh halaman oleh pemanggil, bukan per baris,
    50 baris x 1 query akan jadi 50 query untuk informasi yang satu query bisa
    jawab sekaligus.
    """
    return {
        "id": str(u.id),
        "email": u.email,
        "display_name": u.display_name,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "is_active": u.is_active,
        "is_super_admin": u.id in super_admin_ids,
        "workspace_role": (ws.get(u.id) or (None, None))[0],
        "workspace_slug": (ws.get(u.id) or (None, None))[1],
        # Aktivitas: sudah direkam otomatis oleh alur autentikasi, selama ini
        # tidak pernah ditampilkan di mana pun.
        "last_active": u.last_active,
        "last_login_time": u.last_login_time,
        "last_logout_time": u.last_logout_time,
        "last_login_ip": u.last_login_ip,
        "last_login_medium": u.last_login_medium,
        "created_at": u.created_at,
        # Dua keadaan yang berbeda: sesi bisa hidup berhari-hari sesudah
        # orangnya pulang. "sedang memakai" mensyaratkan keduanya karena
        # last_active ber-default timezone.now, jadi akun yang baru dibuat
        # akan terbaca aktif tanpa pernah login.
        "masih_login": str(u.id) in (sesi_hidup or set()),
        "sedang_memakai": (
            str(u.id) in (sesi_hidup or set())
            and batas_aktif is not None
            and u.last_active is not None
            and u.last_active >= batas_aktif
        ),
    }


class InstanceMemberEndpoint(BaseAPIView):
    """Kelola member dari God Mode, daftar, buat, ubah, nonaktifkan.

    Hanya instance admin (izin dari `BaseAPIView` God Mode).

    Ini **satu-satunya** pintu masuk akun sekarang: pendaftaran mandiri sudah
    dimatikan (`ENABLE_SIGNUP=0`) dan undangan lewat email belum bisa dipakai
    selama SMTP masih patah. Tanpa halaman ini, menambah karyawan baru harus
    lewat skrip.

    Menonaktifkan, bukan menghapus baris: menghapus User akan memutus rujukan
    di jejak audit, worklog, dan riwayat mana pun yang menyentuhnya. Nonaktif
    sudah menghasilkan yang dimaksud, tidak bisa masuk, tidak muncul sebagai
    anggota, dan bisa dibalik.
    """

    def get(self, request):
        qs = User.objects.filter(is_bot=False)

        cari = (request.GET.get("search") or "").strip()
        if cari:
            qs = qs.filter(Q(email__icontains=cari) | Q(display_name__icontains=cari) | Q(first_name__icontains=cari))

        status_filter = request.GET.get("status")
        if status_filter == "active":
            qs = qs.filter(is_active=True)
        elif status_filter == "inactive":
            qs = qs.filter(is_active=False)

        qs = qs.order_by(_URUTAN.get(request.GET.get("sort"), "display_name"))

        try:
            per_page = min(int(request.GET.get("per_page", _DEFAULT_PER_PAGE)), _MAX_PER_PAGE)
        except ValueError:
            per_page = _DEFAULT_PER_PAGE
        per_page = max(per_page, 1)

        paginator = Paginator(qs, per_page)
        page = paginator.get_page(request.GET.get("page", 1))

        sa = super_admin_user_ids()
        ws = _keanggotaan([u.id for u in page.object_list])

        # Keadaan sesi untuk seluruh halaman dalam satu query.
        from datetime import timedelta

        from django.utils import timezone

        from plane.db.models import AMBANG_AKTIF_MENIT, Session

        sesi_hidup = set(
            Session.objects.filter(
                expire_date__gt=timezone.now(),
                user_id__in=[str(u.id) for u in page.object_list],
            ).values_list("user_id", flat=True)
        )
        batas_aktif = timezone.now() - timedelta(minutes=AMBANG_AKTIF_MENIT)

        return Response(
            {
                "count": paginator.count,
                "total_pages": paginator.num_pages,
                "page": page.number,
                "results": [_serialize(u, sa, ws, sesi_hidup, batas_aktif) for u in page.object_list],
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """Buat akun baru. Satu-satunya jalan masuk selama signup mati."""
        email = (request.data.get("email") or "").strip().lower()
        nama = (request.data.get("display_name") or "").strip()
        password = request.data.get("password") or ""

        if not email or "@" not in email:
            return Response({"error": "Email tidak sah."}, status=status.HTTP_400_BAD_REQUEST)
        if not nama:
            return Response({"error": "Nama wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)
        # Tanpa batas minimum, akun baru bisa lahir dengan password satu huruf,
        # dan orangnya tidak akan pernah tahu itu lemah.
        if len(password) < _PANJANG_PASSWORD_MIN:
            return Response(
                {"error": f"Password minimal {_PANJANG_PASSWORD_MIN} karakter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email sudah dipakai."}, status=status.HTTP_400_BAD_REQUEST)

        depan, belakang = _pecah_nama(nama)
        u = User.objects.create(
            email=email,
            username=_uname(email),
            display_name=nama,
            first_name=depan,
            last_name=belakang,
            is_password_autoset=False,
        )
        u.set_password(password)
        u.save()

        # Tanpa WorkspaceMember, akunnya ada tapi tidak bisa masuk ke mana pun.
        ws = _workspace_utama()
        if ws:
            WorkspaceMember.objects.get_or_create(workspace=ws, member=u, defaults={"role": 15})

        return Response(_serialize(u, super_admin_user_ids(), _keanggotaan([u.id])), status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        """Hapus akun secara AMAN (soft-delete + anonimisasi), bukan `User.delete()`.

        Hapus baris User akan merambat CASCADE ke pages, views, votes, devices
        (`on_delete=CASCADE`) — data milik orang lain ikut hilang. Di sini yang
        terjadi: nonaktif + email/nama digosok + sesi diakhiri + status Super
        Admin dicabut + keanggotaan workspace dinonaktifkan. FK dan riwayat
        (audit, worklog, work item) tetap utuh, pemiliknya tampil "Akun dihapus".

        Gerbang (gagal-tertutup semua):
        - `konfirmasi` harus persis display_name akun (ketik-ulang ala hapus
          data sensitif; bukan sekadar `{"yakin": true}` yang bisa terpencet).
        - Tidak bisa menghapus diri sendiri.
        - Tidak bisa menghapus Super Admin terakhir.
        """
        from django.db import transaction

        u = User.objects.filter(pk=pk, is_bot=False).first()
        if not u:
            return Response({"error": "Akun tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if u.id == request.user.id:
            return Response(
                {"error": "Tidak bisa menghapus akun sendiri."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        konfirmasi = (request.data.get("konfirmasi") or "").strip() if isinstance(request.data, dict) else ""
        if not konfirmasi or konfirmasi != (u.display_name or "").strip():
            return Response(
                {"error": "Ketik nama lengkap akun persis seperti tampil untuk konfirmasi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance = Instance.objects.first()
        if instance and InstanceAdmin.objects.filter(instance=instance).count() <= 1:
            if InstanceAdmin.objects.filter(instance=instance, user=u).exists():
                return Response(
                    {"error": "Harus ada minimal satu Super Admin."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            if instance:
                InstanceAdmin.objects.filter(instance=instance, user=u).delete()
            email_gosok = f"terhapus-{str(u.id)[:8]}@deleted.local"
            u.email = email_gosok
            u.username = _uname(email_gosok)
            u.display_name = "Akun dihapus"
            u.first_name = "Akun"
            u.last_name = "dihapus"
            u.is_active = False
            u.save(update_fields=["email", "username", "display_name", "first_name", "last_name", "is_active"])
            WorkspaceMember.objects.filter(member=u).update(is_active=False)
            sesi = _akhiri_sesi(u.id)

        return Response(
            {"id": str(u.id), "email": u.email, "display_name": u.display_name, "sessions_ended": sesi},
            status=status.HTTP_200_OK,
        )
    def patch(self, request, pk):
        """Ubah profil, identitas, password, hak akses, status aktif, Super Admin.

        Semua kolom opsional, hanya yang dikirim yang disentuh, jadi satu form
        di God Mode bisa mengirim sebagian saja tanpa menimpa sisanya dengan
        nilai kosong.
        """
        u = User.objects.filter(pk=pk, is_bot=False).first()
        if not u:
            return Response({"error": "Akun tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        # Gerbang konfirmasi diperiksa DI DEPAN, sebelum satu kolom pun disentuh.
        # Kalau di belakang, permintaan gabungan (ubah password + beri Super
        # Admin) dengan konfirmasi salah akan menyimpan passwordnya lalu membalas
        # 403, balasan yang bagi pemanggilnya berarti "tidak terjadi apa-apa".
        if request.data.get("is_super_admin"):
            ditolak = _tolak_tanpa_konfirmasi_ketik(request)
            if ditolak is not None:
                return ditolak

        kolom = []  # dikumpulkan dulu, satu `save()` di akhir
        sesi_diakhiri = 0

        # --- Nama ---
        if "display_name" in request.data:
            nama = (request.data.get("display_name") or "").strip()
            if not nama:
                return Response({"error": "Nama tidak boleh kosong."}, status=status.HTTP_400_BAD_REQUEST)
            u.display_name = nama
            u.first_name, u.last_name = _pecah_nama(nama)
            kolom += ["display_name", "first_name", "last_name"]

        # --- Email: ini identitas login (`USERNAME_FIELD`), bukan sekadar kontak ---
        if "email" in request.data:
            email = (request.data.get("email") or "").strip().lower()
            if not email or "@" not in email:
                return Response({"error": "Email tidak sah."}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(email=email).exclude(pk=u.pk).exists():
                return Response({"error": "Email sudah dipakai akun lain."}, status=status.HTTP_400_BAD_REQUEST)
            username_baru = _uname(email)
            # `username` juga unik. Tanpa pemeriksaan ini, dua email berbeda yang
            # memetakan ke username sama (titik vs garis bawah) menabrak
            # IntegrityError → 500, bukan pesan yang bisa dibaca orang.
            if User.objects.filter(username=username_baru).exclude(pk=u.pk).exists():
                return Response(
                    {"error": "Username turunan email itu sudah dipakai akun lain."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if email != u.email:
                u.email = email
                u.username = username_baru
                kolom += ["email", "username"]
                sesi_diakhiri += _akhiri_sesi(u.id)

        # --- Password: reset oleh admin, bukan lupa-password lewat email ---
        if "password" in request.data:
            password = request.data.get("password") or ""
            if len(password) < _PANJANG_PASSWORD_MIN:
                return Response(
                    {"error": f"Password minimal {_PANJANG_PASSWORD_MIN} karakter."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            u.set_password(password)
            # `is_password_autoset=True` berarti "password belum pernah dipilih
            # sendiri" dan memicu alur ganti-password paksa. Admin yang mengeset
            # password bukan itu, nilainya harus False.
            u.is_password_autoset = False
            kolom += ["password", "is_password_autoset"]
            sesi_diakhiri += _akhiri_sesi(u.id)

        if kolom:
            u.save(update_fields=kolom)

        # --- Hak akses workspace ---
        # Dua kunci, masing-masing boleh dikirim sendiri: dulu `workspace_slug`
        # diabaikan kalau perannya tidak ikut berubah, jadi pindah workspace
        # dari God Mode diam-diam tidak terjadi.
        if "workspace_role" in request.data or "workspace_slug" in request.data:
            sekarang = _keanggotaan([u.id]).get(u.id)  # (peran, slug) atau None
            peran = sekarang[0] if sekarang else 15
            if "workspace_role" in request.data:
                try:
                    peran = int(request.data["workspace_role"])
                except (TypeError, ValueError):
                    return Response({"error": "Peran tidak sah."}, status=status.HTTP_400_BAD_REQUEST)
                if peran not in _PERAN_SAH:
                    return Response(
                        {"error": f"Peran harus salah satu dari {sorted(_PERAN_SAH)}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            ws_slug = str(request.data.get("workspace_slug") or "").strip()
            # Tanpa slug = workspace orang itu sekarang; belum punya = utama.
            # Bukan `Workspace.objects.first()`: itu yang TERBARU (lihat `_workspace_utama`).
            ws_slug = ws_slug or (sekarang[1] if sekarang else "")
            ws = (
                Workspace.objects.filter(slug=ws_slug, deleted_at__isnull=True).first() if ws_slug else _workspace_utama()
            )
            if not ws:
                return Response({"error": "Workspace tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)
            # `update_or_create`, bukan `filter().update()`: akun yang belum
            # pernah jadi anggota workspace (`workspace_role: null`) harus ikut
            # bisa diberi peran dari sini. `is_active=True` menghidupkan lagi
            # keanggotaan lama kalau orangnya dipindah balik.
            WorkspaceMember.objects.update_or_create(
                workspace=ws, member=u, defaults={"role": peran, "is_active": True}
            )
            # Pindah workspace: keanggotaan lama dinonaktifkan, bukan dihapus,
            # supaya riwayat & ProjectMember utuh dan bisa dibalik.
            if sekarang and sekarang[1] != ws.slug:
                WorkspaceMember.objects.filter(member=u, is_active=True).exclude(workspace=ws).update(is_active=False)

        if "is_active" in request.data:
            aktif = bool(request.data["is_active"])
            # Menonaktifkan diri sendiri akan mengunci orang itu keluar dari
            # halaman yang sedang ia pakai, tolak, jangan biarkan.
            if not aktif and u.id == request.user.id:
                return Response(
                    {"error": "Tidak bisa menonaktifkan akun sendiri."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            u.is_active = aktif
            u.save(update_fields=["is_active"])
            # Nonaktif tapi sesinya masih hidup = masih bisa memakai tab yang
            # sudah terbuka. Sama kelasnya dengan reset password.
            if not aktif:
                sesi_diakhiri += _akhiri_sesi(u.id)

        if "is_super_admin" in request.data:
            jadikan = bool(request.data["is_super_admin"])
            instance = Instance.objects.first()
            if not instance:
                return Response({"error": "Instance belum terdaftar."}, status=status.HTTP_400_BAD_REQUEST)
            if jadikan:
                InstanceAdmin.objects.get_or_create(
                    instance=instance, user=u, defaults={"role": 20, "is_verified": True}
                )
                # Susulkan akses ke project yang sudah ada; project baru ikut
                # sendiri lewat signal.
                sinkronkan_super_admin(user_id=u.id)
            else:
                if u.id == request.user.id:
                    return Response(
                        {"error": "Tidak bisa mencabut status Super Admin sendiri."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if InstanceAdmin.objects.filter(instance=instance).count() <= 1:
                    return Response(
                        {"error": "Harus ada minimal satu Super Admin."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                InstanceAdmin.objects.filter(instance=instance, user=u).delete()

        hasil = _serialize(u, super_admin_user_ids(), _keanggotaan([u.id]))
        # Supaya UI bisa memberi tahu terus terang bahwa orangnya baru saja
        # dikeluarkan dan harus masuk ulang, bukan dibiarkan menebak.
        hasil["sessions_ended"] = sesi_diakhiri
        return Response(hasil, status=status.HTTP_200_OK)


def _preferensi_notifikasi(u):
    """Baris notifikasi GLOBAL (tanpa workspace/project) milik user; dibuat kalau belum ada."""
    pref, _ = UserNotificationPreference.objects.get_or_create(user=u, workspace=None, project=None)
    return pref


def _bentuk_preferensi(profil, notif):
    return {
        "profile": {
            "language": profil.language,
            "start_of_the_week": profil.start_of_the_week,
            "notification_view_mode": profil.notification_view_mode,
            **{k: getattr(profil, k) for k in _SAKLAR_PROFIL},
        },
        "notifications": {k: getattr(notif, k) for k in _SAKLAR_NOTIFIKASI},
    }


def _periksa_preferensi(data):
    """Balikkan (profil_baru, notif_baru, galat). Semua dicek SEBELUM satu kolom pun ditulis."""
    profil = data.get("profile") or {}
    notif = data.get("notifications") or {}
    if not isinstance(profil, dict) or not isinstance(notif, dict):
        return None, None, "Format tidak sah."

    baru_profil = {}
    if "language" in profil:
        if profil["language"] not in _BAHASA_SAH:
            return None, None, "Bahasa tidak didukung."
        baru_profil["language"] = profil["language"]
    if "start_of_the_week" in profil:
        # bool lolos `in` set angka (True == 1), jadi tolak eksplisit.
        hari = profil["start_of_the_week"]
        if isinstance(hari, bool) or hari not in _HARI_PEKAN_SAH:
            return None, None, "Hari awal pekan tidak sah."
        baru_profil["start_of_the_week"] = hari
    if "notification_view_mode" in profil:
        if profil["notification_view_mode"] not in _MODE_NOTIFIKASI_SAH:
            return None, None, "Mode tampilan notifikasi tidak sah."
        baru_profil["notification_view_mode"] = profil["notification_view_mode"]
    for kolom in _SAKLAR_PROFIL:
        if kolom in profil:
            if not isinstance(profil[kolom], bool):
                return None, None, f"{kolom} harus true/false."
            baru_profil[kolom] = profil[kolom]

    baru_notif = {}
    for kolom in _SAKLAR_NOTIFIKASI:
        if kolom in notif:
            if not isinstance(notif[kolom], bool):
                return None, None, f"{kolom} harus true/false."
            baru_notif[kolom] = notif[kolom]
    return baru_profil, baru_notif, None


class InstanceMemberPreferenceEndpoint(BaseAPIView):
    """Baca/ubah pengaturan pribadi satu member dari God Mode (bahasa, awal pekan,
    mode notifikasi, saklar email notifikasi).

    Hanya kolom di daftar putih di atas yang bisa disentuh. Tidak mengakhiri sesi:
    ini preferensi tampilan, bukan kredensial.
    """

    def _user(self, pk):
        return User.objects.filter(pk=pk, is_bot=False).first()

    def get(self, request, pk):
        u = self._user(pk)
        if not u:
            return Response({"error": "Akun tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        profil, _ = Profile.objects.get_or_create(user=u)
        return Response(_bentuk_preferensi(profil, _preferensi_notifikasi(u)), status=status.HTTP_200_OK)

    def patch(self, request, pk):
        from django.db import transaction

        u = self._user(pk)
        if not u:
            return Response({"error": "Akun tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        baru_profil, baru_notif, galat = _periksa_preferensi(request.data)
        if galat:
            return Response({"error": galat}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            profil, _ = Profile.objects.get_or_create(user=u)
            notif = _preferensi_notifikasi(u)
            for kolom, nilai in baru_profil.items():
                setattr(profil, kolom, nilai)
            for kolom, nilai in baru_notif.items():
                setattr(notif, kolom, nilai)
            if baru_profil:
                profil.save(update_fields=list(baru_profil))
            if baru_notif:
                notif.save(update_fields=list(baru_notif))
        return Response(_bentuk_preferensi(profil, notif), status=status.HTTP_200_OK)
