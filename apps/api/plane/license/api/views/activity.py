# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: sesi, kick, dan dashboard aktivitas
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Pemantauan sesi & aktivitas untuk God Mode.

Tiga hal yang sering dikira sama padahal berbeda, dan seluruh berkas ini
bersandar pada pembedaan itu:

- **Masih login** , ada baris di tabel `sessions` yang belum kedaluwarsa.
  Bisa bertahan berhari-hari sesudah orangnya menutup laptop.
- **Sedang memakai**, `User.last_active` dalam AMBANG_AKTIF_MENIT terakhir.
  Distempel `LastActiveMiddleware` dari request yang memang sudah terjadi.
- **Pernah login** , ada di `login_activities`. Riwayat, bukan keadaan.

Kolom "online" di God Mode memakai yang **kedua**. Memakai yang pertama akan
menampilkan setengah kantor sebagai online pada jam 11 malam.
"""

# Python imports
from datetime import timedelta

# Django imports
from django.db.models import Count
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .base import BaseAPIView
from plane.license.audit_godmode import catat_godmode
from plane.db.models import (
    DOMAIN_AKUN_TERHAPUS,
    AMBANG_AKTIF_MENIT,
    LoginActivity,
    Session,
    User,
)
from plane.utils.saklar_instance import LOGIN_HISTORY_RETENTION_DAYS, setelan_angka


def _batas_aktif():
    return timezone.now() - timedelta(minutes=AMBANG_AKTIF_MENIT)


def _rentang(request):
    """Baca ?hari=N, dijepit ke 1..retensi."""
    try:
        hari = int(request.GET.get("hari", 30))
    except (TypeError, ValueError):
        hari = 30
    # Batas atas = retensi (God Mode > Features). Meminta lebih jauh hanya
    # menghasilkan grafik yang sebagian besar kosong lalu dikira "sepi".
    hari = max(1, min(hari, setelan_angka(LOGIN_HISTORY_RETENTION_DAYS)))
    return hari, timezone.now() - timedelta(days=hari)


def _sesi_hidup_per_user():
    """{user_id(str): jumlah sesi belum kedaluwarsa}.

    `Session.user_id` di repo ini `CharField`, bukan ForeignKey (SESSION_ENGINE
    kustom, tabel `sessions`), jadi kuncinya string, dan menyamakannya dengan
    UUID akan diam-diam tidak pernah cocok.
    """
    baris = (
        Session.objects.filter(expire_date__gt=timezone.now())
        .exclude(user_id__isnull=True)
        .exclude(user_id="")
        .values("user_id")
        .annotate(n=Count("session_key"))
    )
    return {b["user_id"]: b["n"] for b in baris}


def _sesi_user(user_id):
    """Daftar sesi hidup satu user, terbaru dulu."""
    hasil = []
    for s in Session.objects.filter(user_id=str(user_id), expire_date__gt=timezone.now()).order_by("-expire_date"):
        info = s.device_info if isinstance(s.device_info, dict) else {}
        hasil.append(
            {
                "session_key": s.session_key,
                "expire_date": s.expire_date,
                "user_agent": info.get("user_agent", ""),
                "ip_address": info.get("ip_address", ""),
                "domain": info.get("domain", ""),
            }
        )
    return hasil


class InstanceMemberSessionEndpoint(BaseAPIView):
    """`/api/instances/members/<pk>/sessions/`, lihat & putuskan sesi.

    GET    daftar sesi hidup + keadaan aktivitas orang itu.
    DELETE putuskan semua sesinya (kick). `?nonaktifkan=1` sekalian mengunci
           akunnya sehingga tidak bisa login lagi sampai diaktifkan kembali.
    """

    def get(self, request, pk):
        try:
            u = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Member not found."}, status=status.HTTP_404_NOT_FOUND)

        sesi = _sesi_user(u.id)
        return Response(
            {
                "id": str(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "is_active": u.is_active,
                # Sesi hidup DAN keaktifan baru, lihat alasannya di
                # InstanceActivityEndpoint.
                "sedang_memakai": bool(sesi) and bool(u.last_active and u.last_active >= _batas_aktif()),
                "masih_login": bool(sesi),
                "last_active": u.last_active,
                "last_login_time": u.last_login_time,
                "last_logout_time": u.last_logout_time,
                "sesi": sesi,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        try:
            u = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Member not found."}, status=status.HTTP_404_NOT_FOUND)

        # Menendang diri sendiri akan langsung membuang sesi God Mode yang
        # sedang dipakai untuk mengirim request ini. Ditolak di depan supaya
        # admin tidak mengunci dirinya sendiri karena salah klik baris.
        if str(u.id) == str(request.user.id):
            return Response(
                {"error": "You cannot kick your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nonaktifkan = str(request.GET.get("nonaktifkan", "")).lower() in ("1", "true", "ya")

        # Tidak ada penjaga "instance admin terakhir" di sini, dan itu disengaja.
        # Penolakan menendang diri sendiri di atas sudah menjaminnya: si pemanggil
        # WAJIB instance admin aktif dan tidak boleh menyasar dirinya sendiri,
        # jadi sesudah operasi apa pun selalu tersisa minimal satu admin aktif,
        # dia sendiri. Penjaga tambahan hanya akan jadi cabang yang tak pernah
        # dieksekusi. `InstanceMemberEndpoint.patch` memakai alasan yang sama.
        jumlah = Session.objects.filter(user_id=str(u.id)).delete()[0]

        if nonaktifkan:
            u.is_active = False
        u.last_logout_time = timezone.now()
        u.save(update_fields=["is_active", "last_logout_time"] if nonaktifkan else ["last_logout_time"])

        # Dicatat sebagai LOGOUT supaya sesi ini tertutup rapi di riwayat,
        # tanpa ini, login-nya menggantung selamanya dan durasi tak terhitung.
        LoginActivity.catat(
            user=u,
            jenis=LoginActivity.Jenis.LOGOUT,
            request=request,
            permukaan="kick",
        )

        catat_godmode(
            request,
            kind="account_session",
            label=f"Account session: {u.email}",
            object_pk=str(u.pk),
            changes={"sessions": [str(jumlah), "0"]},
            detail="Sessions ended" + (" and account deactivated" if nonaktifkan else ""),
        )
        return Response(
            {
                "sesi_diputus": jumlah,
                "dinonaktifkan": nonaktifkan,
                "is_active": u.is_active,
            },
            status=status.HTTP_200_OK,
        )


class InstanceActivityEndpoint(BaseAPIView):
    """`/api/instances/activity/`, angka untuk dashboard aktivitas.

    `?hari=N` (1..90, default 30).
    """

    def get(self, request):
        hari, sejak = _rentang(request)
        batas_aktif = _batas_aktif()

        peristiwa = LoginActivity.objects.filter(terjadi_pada__gte=sejak)
        login_qs = peristiwa.filter(jenis=LoginActivity.Jenis.LOGIN)

        # Akun terhapus bukan pengguna lagi; mereka tinggal di Trash.
        pengguna = User.objects.filter(is_bot=False).exclude(email__endswith=f"@{DOMAIN_AKUN_TERHAPUS}")
        total_user = pengguna.count()

        # "Sedang memakai" mensyaratkan DUA hal: ada sesi hidup, DAN last_active
        # masih baru. `last_active` sendiri tidak cukup, field itu ber-`default=
        # timezone.now`, jadi akun yang baru dibuat lewat God Mode akan terbaca
        # sedang memakai selama 5 menit padahal belum pernah login sekali pun.
        punya_sesi = set(_sesi_hidup_per_user())
        masih_login = len(punya_sesi)
        sedang_memakai = pengguna.filter(id__in=punya_sesi, last_active__gte=batas_aktif).count()

        # Keluar-masuk: berapa kali tiap orang login dalam rentang ini. Inilah
        # yang tidak mungkin dijawab sebelum tabel login_activities ada,
        # `last_login_time` cuma satu nilai yang ditimpa tiap login.
        per_user = list(login_qs.values("user_id").annotate(n=Count("id")))
        jumlah_login = [p["n"] for p in per_user]
        total_login = sum(jumlah_login)

        # Sepuluh terbanyak. "Seberapa sering keluar-masuk" adalah pertanyaan
        # per-orang; angka rata-rata menyembunyikan satu orang yang login 40 kali
        # sehari karena sesinya terus putus.
        teratas = sorted(per_user, key=lambda p: -p["n"])[:10]
        nama = dict(User.objects.filter(id__in=[p["user_id"] for p in teratas]).values_list("id", "email"))
        teraktif = [
            {
                "user_id": str(p["user_id"]),
                "email": nama.get(p["user_id"], ""),
                "login": p["n"],
            }
            for p in teratas
        ]

        # Aktif harian: berapa orang berbeda yang login tiap hari.
        # Daftar, bukan objek, urutan waktu adalah bagian dari maknanya, dan
        # objek JSON menyerahkan urutan itu ke cara klien mem-parsing kuncinya.
        harian = [
            {
                "tgl": str(row["terjadi_pada__date"]),
                "orang": row["orang"],
                "login": row["login"],
            }
            for row in (
                login_qs.values("terjadi_pada__date")
                .annotate(orang=Count("user_id", distinct=True), login=Count("id"))
                .order_by("terjadi_pada__date")
            )
        ]

        # Impor lokal: bgtasks menarik Celery, dan modul view ini dimuat saat
        # URLconf disusun.
        from plane.bgtasks.login_activity_retention import hitung_peringatan

        retensi = hitung_peringatan()

        return Response(
            {
                "rentang_hari": hari,
                "sejak": sejak,
                "ambang_aktif_menit": AMBANG_AKTIF_MENIT,
                "ringkas": {
                    "total_user": total_user,
                    "sedang_memakai": sedang_memakai,
                    "masih_login": masih_login,
                    "belum_pernah_login": pengguna.filter(last_login_time__isnull=True).count(),
                    "total_login": total_login,
                    "user_yang_login": len(jumlah_login),
                    "rata_login_per_user": round(total_login / len(jumlah_login), 1) if jumlah_login else 0,
                },
                "harian": harian,
                "teraktif": teraktif,
                # Sumbernya sama persis dengan yang dipakai task pembersih, jadi
                # peringatan di layar tidak mungkin berbeda dari yang benar-benar
                # akan dihapus.
                "retensi": {
                    **retensi,
                    "peristiwa_tersimpan": LoginActivity.objects.count(),
                },
            },
            status=status.HTTP_200_OK,
        )


class InstanceLoginHistoryEndpoint(BaseAPIView):
    """`/api/instances/login-history/`, riwayat mentah, bisa disaring.

    Nilai ganda dipisah koma, `*_not` = kebalikannya:
      ?user_id= / ?user_id_not=       <user_id>,...
      ?jenis= / ?jenis_not=           LOGIN,LOGOUT
      ?permukaan= / ?permukaan_not=   web,admin,... (nilai kosong = `none`)
      ?medium= / ?medium_not=         email,google,... (nilai kosong = `none`)
      ?ip=<sebagian IP>  ?search=<nama, email, atau IP>
      ?date_from=YYYY-MM-DD  ?date_to=YYYY-MM-DD  (di dalam jendela ?hari=N)
      ?sort=-time|time|person|event|source|medium|ip   ?page=  ?per_page=

    Respons ikut membawa `pilihan` (permukaan & medium yang benar-benar ada di
    jendela ini), supaya filter di God Mode tidak menawarkan nilai yang mustahil.
    """

    def get(self, request):
        from django.db.models import Q

        from .audit_log import _daftar, _parse_tanggal

        _, sejak = _rentang(request)
        dasar = LoginActivity.objects.filter(terjadi_pada__gte=sejak)
        qs = dasar.select_related("user")

        def saring(qs, kolom, kunci):
            # `none` mewakili string kosong: event lama sebelum kolom ini diisi.
            for negasi, k in ((False, kunci), (True, f"{kunci}_not")):
                nilai = ["" if v == "none" else v for v in _daftar(request, k)]
                if nilai:
                    q = Q(**{f"{kolom}__in": nilai})
                    qs = qs.exclude(q) if negasi else qs.filter(q)
            return qs

        qs = saring(qs, "user_id", "user_id")
        qs = saring(qs, "jenis", "jenis")
        qs = saring(qs, "permukaan", "permukaan")
        qs = saring(qs, "medium", "medium")

        if ip := (request.GET.get("ip") or "").strip():
            qs = qs.filter(ip__icontains=ip)
        if cari := (request.GET.get("search") or "").strip():
            qs = qs.filter(
                Q(user__email__icontains=cari) | Q(user__display_name__icontains=cari) | Q(ip__icontains=cari)
            )
        if dari := _parse_tanggal(request.GET.get("date_from")):
            qs = qs.filter(terjadi_pada__gte=dari)
        if sampai := _parse_tanggal(request.GET.get("date_to"), akhir_hari=True):
            qs = qs.filter(terjadi_pada__lte=sampai)

        urutan = {
            "-time": "-terjadi_pada",
            "time": "terjadi_pada",
            "person": "user__display_name",
            "-person": "-user__display_name",
            "event": "jenis",
            "-event": "-jenis",
            "source": "permukaan",
            "-source": "-permukaan",
            "medium": "medium",
            "-medium": "-medium",
            "ip": "ip",
            "-ip": "-ip",
        }.get(request.GET.get("sort") or "", "-terjadi_pada")
        qs = qs.order_by(urutan, "-terjadi_pada")

        pilihan = {
            kolom: sorted(set(dasar.order_by().values_list(kolom, flat=True).distinct()))
            for kolom in ("permukaan", "medium")
        }

        try:
            page = max(1, int(request.GET.get("page", 1)))
            per_page = min(200, max(1, int(request.GET.get("per_page", 50))))
        except (TypeError, ValueError):
            page, per_page = 1, 50

        total = qs.count()
        awal = (page - 1) * per_page
        baris = [
            {
                "id": str(a.id),
                "user_id": str(a.user_id),
                "email": a.user.email,
                "display_name": a.user.display_name,
                "jenis": a.jenis,
                "terjadi_pada": a.terjadi_pada,
                "ip": a.ip,
                "user_agent": a.user_agent,
                "medium": a.medium,
                "permukaan": a.permukaan,
            }
            for a in qs[awal : awal + per_page]
        ]

        return Response(
            {
                "count": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
                "results": baris,
                "pilihan": pilihan,
            },
            status=status.HTTP_200_OK,
        )
