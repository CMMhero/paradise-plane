# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: data demo supaya aplikasi terasa hidup
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Isi workspace utama dengan perusahaan rekaan yang lengkap.

    python manage.py seed_demo_data            # isi (berhenti kalau sudah pernah)
    python manage.py seed_demo_data --reset    # hapus data demo lama, lalu isi ulang

Yang dibuat: 5 divisi, 12 departemen (masing-masing otomatis punya project, KEP-32),
~60 akun berjenjang (direktur, manager, supervisor, staf) dengan password
`P@ssw0rd`, label, modul, page, view tersimpan, work item induk + sub-tugas,
assignee, komentar, riwayat aktivitas + notifikasi Inbox, persetujuan
(menunggu/disetujui/ditolak), permintaan lintas divisi di intake, dan isi
pribadi tiap orang (pin sidebar, favorit, sticky, quick link).

Cycles TIDAK dibuat: modulnya dicabut (KEP-50), jadi `cycle_view` tetap mati.
Fitur project lain dinyalakan eksplisit, sama dengan migrasi 0154, supaya hasilnya
benar walau migrasi itu belum diterapkan di database tujuan.

## Kenapa aktivitas lewat `issue_activity`, bukan baris `IssueActivity` mentah

Fungsi yang sama dengan yang diantrekan endpoint, dipanggil langsung (sinkron).
Ia menulis riwayat "created/assigned/comment" dan mengantrekan notifikasi, jadi
Inbox tiap orang berisi. Notifikasinya diproses worker Celery, karena itu bagian
isi project tidak dibungkus satu transaksi: worker harus bisa membaca tugasnya.

## Kenapa lewat helper God Mode, bukan menulis baris mentah

Departemen dibuat lewat `_adopsi_atau_buat_project` (jalur tombol "Tambah
departemen") dan keanggotaan project lahir dari `sinkronkan_workspace`, bukan
`ProjectMember` yang ditulis tangan. Dengan begitu data demo memakai aturan
jangkauan yang SAMA dengan produksi: kalau seed ini menghasilkan akses yang aneh,
itu bug hierarki, bukan bug seed.

## Kenapa `crum.impersonate`

`BaseModel.save()` menimpa `created_by` dengan user dari request; di management
command tidak ada request, jadi tanpa impersonate semua tugas lahir tanpa pembuat
dan tidak bisa dihapus siapa pun (lihat Jebakan di aturan-tugas).

## Hanya lokal

Bukan data migration dan tidak dipanggil entrypoint mana pun: hanya jalan kalau
dipanggil tangan. Lalu `_pastikan_lokal` menolak settings selain
`plane.settings.local` dan instance yang punya lebih dari `BATAS_AKUN_NYATA` akun
sungguhan, tanpa jalan pintas. Berkas seed juga dikecualikan dari image produksi
lewat `apps/api/.dockerignore`.

## Super Admin ikut

Akun Super Admin pemilik instance (akun sungguhan) dimasukkan ke data: memberi
dan menerima tugas, berkomentar, punya page, mengunggah materi Wiki, ada di Chat.
Semua itu menempel ke project/ruang demo atau bertanda `seed-demo`, jadi
`--reset` membersihkannya tanpa menyentuh data miliknya yang lain. Setelan
pribadinya (pin sidebar, favorit, sticky) sengaja tidak diubah.
"""

# Python imports
import json
import random
from datetime import timedelta

# Django imports
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

# Third party imports
from crum import impersonate

# Module imports
from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.direktur import sinkronkan_direktur
from plane.db.jangkauan import sinkronkan_workspace, tunda_sinkron
from plane.db.management.commands import _demo_data as data
from plane.db.management.commands._demo_berkas import hapus_berkas_demo
from plane.db.management.commands._demo_konten import SUB_TOPIK, SUMBER as SUMBER_KONTEN
from plane.db.management.commands._demo_konten import isi_konten
from plane.db.management.commands._demo_obrolan import isi_obrolan
from plane.db.management.commands._demo_pribadi import isi_pribadi
from plane.utils.inbox_chat import ENTITY_CHAT
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    FileAsset,
    Intake,
    IntakeIssue,
    Issue,
    IssueActivity,
    IssueAssignee,
    IssueComment,
    IssueLabel,
    IssueView,
    JabatanOrganisasi,
    Label,
    Module,
    ModuleIssue,
    ModuleMember,
    Notification,
    Page,
    PermintaanLintasDivisi,
    PersetujuanPenugasan,
    PesanLangsung,
    Profile,
    Project,
    ProjectPage,
    Ruang,
    State,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WikiFolder,
    Workspace,
    WorkspaceMember,
)

# Lebih dari ini akun non-demo = instance yang dipakai orang (produksi punya ~80).
# Sengaja bukan `DEBUG`: stack lokal kita jalan dengan DEBUG mati.
BATAS_AKUN_NYATA = 5
# Satu-satunya settings tempat command ini boleh jalan (docker-compose-local).
SETTINGS_LOKAL = {"plane.settings.local"}
ROLE_ADMIN = 20
ROLE_MEMBER = 15
ZONA_WAKTU = "Asia/Jakarta"
# Fitur project yang menyala (cermin migrasi 0154, KEP-50). Cycles sengaja mati.
FITUR_PROJECT = {
    "module_view": True,
    "issue_views_view": True,
    "page_view": True,
    "intake_view": True,
    "is_time_tracking_enabled": True,
    "cycle_view": False,
}
# Kode emoji yang sama dengan pemilih ikon project di web (RANDOM_EMOJI_CODES).
EMOJI_PROJECT = ["128204", "128188", "128202", "128230", "128737", "128176", "129309", "128187", "127919", "128640"]
PRIORITAS = ["urgent", "high", "medium", "medium", "low", "low", "none"]
# Bobot status induk: (grup state, bobot). Sub-tugas mengikuti induknya dengan sedikit acak.
BOBOT_STATUS = [("backlog", 10), ("unstarted", 25), ("started", 35), ("completed", 25), ("cancelled", 5)]


def _email(nama):
    return f"{nama.lower().replace(' ', '.')}@{data.DEMO_DOMAIN}"


class Command(BaseCommand):
    help = "Isi workspace utama dengan data demo (akun, divisi, departemen, project, work item, persetujuan)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Hapus data demo lama dulu.")
        parser.add_argument("--seed", type=int, default=2026, help="Seed acak (hasil sama tiap kali).")

    def handle(self, *args, **opts):
        self._pastikan_lokal()

        self.rng = random.Random(opts["seed"])
        self.now = timezone.now()
        self.ws = Workspace.objects.filter(deleted_at__isnull=True).order_by("created_at").first()
        if self.ws is None:
            raise CommandError("Belum ada workspace. Selesaikan setup instance dulu.")
        self.actor = self._aktor_admin()

        if opts["reset"]:
            self._reset()
        elif User.objects.filter(email__endswith=f"@{data.DEMO_DOMAIN}").exists():
            raise CommandError("Data demo sudah ada. Pakai --reset untuk mengisi ulang.")

        with transaction.atomic():
            self._buat_orang()
            self._buat_struktur()
            self._tempatkan_jabatan()
        # Sinkron di luar transaksi struktur supaya jangkauan membaca data yang sudah final.
        sinkronkan_workspace(self.ws.id)
        sinkronkan_direktur(self.ws.id)
        self._sinkron_wiki()

        # Tanpa transaksi: notifikasi diproses worker dan harus bisa membaca tugasnya.
        # Gagal di tengah jalan cukup dibereskan dengan --reset.
        for kode_dep in self.project:
            self._isi_project(kode_dep)
        self._permintaan_lintas_divisi()
        self._isi_pribadi_semua()
        self.konten = isi_konten(self)
        isi_obrolan(self)

        self._ringkasan()

    # ------------------------------------------------------------------ dasar

    def _pastikan_lokal(self):
        """Dua penjaga, keduanya tanpa jalan pintas (`--force` sengaja dibuang).

        1. Settings harus `plane.settings.local`. Image produksi berjalan dengan
           `plane.settings.production` (manage.py dan entrypoint), jadi di server
           command ini berhenti sebelum menyentuh database. Berkasnya pun tidak
           ikut ke image produksi (`apps/api/.dockerignore`).
        2. Instance dengan lebih dari `BATAS_AKUN_NYATA` akun non-demo dianggap
           dipakai orang, walau settings-nya lokal (mis. salinan database produksi).
        """
        modul = settings.SETTINGS_MODULE or ""
        if modul not in SETTINGS_LOKAL:
            raise CommandError(f"Data demo hanya untuk lokal. Settings sekarang: {modul or '(kosong)'}.")
        nyata = (
            User.objects.filter(is_active=True, is_bot=False).exclude(email__endswith=f"@{data.DEMO_DOMAIN}").count()
        )
        if nyata > BATAS_AKUN_NYATA:
            raise CommandError(
                f"Instance ini punya {nyata} akun sungguhan; data demo bukan untuk instance yang dipakai orang."
            )

    def _aktor_admin(self):
        from plane.license.models import InstanceAdmin  # noqa: PLC0415

        admin = InstanceAdmin.objects.select_related("user").order_by("created_at").first()
        if admin:
            return admin.user
        user = User.objects.filter(is_superuser=True).order_by("date_joined").first()
        if user is None:
            raise CommandError("Tidak ada Super Admin untuk dijadikan pembuat struktur.")
        return user

    def _reset(self):
        demo_divisi = [kode for kode, _, _ in data.ORGANISASI]
        dep_kode = [k for _, _, deps in data.ORGANISASI for k, _ in deps]
        project_ids = list(
            DepartemenProject.all_objects.filter(departemen__kode__in=dep_kode, workspace=self.ws).values_list(
                "project_id", flat=True
            )
        )
        demo_users = User.objects.filter(email__endswith=f"@{data.DEMO_DOMAIN}")
        # Yang TIDAK ikut terhapus kaskade project/user, jadi dibuang eksplisit:
        # - semua berkas bertanda seed (objek MinIO + barisnya). Lampiran obrolan
        #   hanya menempel ke workspace; hapus user cuma menolkan created_by-nya,
        #   jadi tanpa ini barisnya tertinggal menunjuk objek yang sudah hilang.
        # - sub-topik Wiki (WikiFolder bukan anak project, jadi tidak ikut kaskade).
        # - ruang obrolan yang punya pelanggan akun demo (DM ke Super Admin dan
        #   kanal Umum ikut, karena keduanya lahir dari seed).
        berkas_demo = FileAsset.all_objects.filter(workspace=self.ws, external_source=SUMBER_KONTEN)
        hapus_berkas_demo(berkas_demo)
        sub_topik = WikiFolder.all_objects.filter(
            workspace=self.ws,
            parent__isnull=False,
            divisi__isnull=True,
            departemen__isnull=True,
            umum=False,
            nama__in=[judul for judul, _ in SUB_TOPIK],
        )
        ruang_demo = Ruang.objects.filter(workspace=self.ws, langganan__user__in=demo_users).distinct()
        with transaction.atomic(), tunda_sinkron():
            berkas_demo.delete()
            # Baris Inbox obrolan tidak punya project, jadi tidak ikut kaskade; tanpa
            # ini Super Admin menyimpan notifikasi yang menunjuk ruang yang sudah hilang.
            Notification.objects.filter(
                workspace=self.ws,
                entity_name=ENTITY_CHAT,
                entity_identifier__in=list(ruang_demo.values_list("id", flat=True)),
            ).delete()
            ruang_demo.delete()
            sub_topik.delete(soft=False)
            # Jabatan dulu: menghapus departemen men-SET_NULL penempatan, dan supervisor
            # dua departemen lalu punya dua baris "tanpa tempat" yang melanggar constraint.
            JabatanOrganisasi.all_objects.filter(workspace=self.ws, member__in=demo_users).delete()
            Project.all_objects.filter(pk__in=project_ids).delete()
            Departemen.all_objects.filter(workspace=self.ws, kode__in=dep_kode).delete()
            Divisi.all_objects.filter(workspace=self.ws, kode__in=demo_divisi).delete()
            demo_users.delete()
            # DM yang dibuka worker Celery (saklar "tugas ke DM") bisa lahir SESUDAH
            # `ruang_demo` di atas dihitung, kalau worker masih mengerjakan antrean run
            # sebelumnya. Begitu user demo terhapus, ruang itu tinggal tanpa pelanggan:
            # tak terjangkau siapa pun, jadi aman dibuang. Akun yang dihapus lewat
            # aplikasi tidak kena: KEP-50 menggosok user, bukan menghapus barisnya.
            Ruang.objects.filter(workspace=self.ws, tipe=Ruang.Tipe.DM).annotate(n=Count("langganan")).filter(
                n=0
            ).delete()
        sinkronkan_workspace(self.ws.id)
        self.stdout.write(self.style.WARNING(f"Data demo lama dihapus ({len(project_ids)} project)."))

    def _user(self, nama, role):
        depan, _, belakang = nama.partition(" ")
        email = _email(nama)
        u = User(
            email=email,
            username=email.split("@")[0].replace(".", "_"),
            display_name=nama,
            first_name=depan,
            last_name=belakang,
            is_password_autoset=False,
            is_email_verified=True,
        )
        u.set_password(data.DEMO_PASSWORD)
        u.save()
        profil, _ = Profile.objects.get_or_create(user=u)
        Profile.objects.filter(pk=profil.pk).update(
            is_onboarded=True, is_tour_completed=True, last_workspace_id=self.ws.id
        )
        WorkspaceMember.objects.get_or_create(workspace=self.ws, member=u, defaults={"role": role})
        return u

    def _buat_orang(self):
        self.direktur = [self._user(n, ROLE_ADMIN) for n, _ in data.DIREKTUR]
        self.manager = {div: self._user(n, ROLE_MEMBER) for div, n in data.MANAGER.items()}
        self.supervisor_user = {n: self._user(n, ROLE_MEMBER) for n in data.SUPERVISOR}
        self.supervisor = {dep: self.supervisor_user[n] for n, deps in data.SUPERVISOR.items() for dep in deps}
        self.staf = {dep: [self._user(n, ROLE_MEMBER) for n in names] for dep, names in data.STAF.items()}

    # --------------------------------------------------------------- struktur

    def _buat_struktur(self):
        from plane.license.api.views.organisasi import _adopsi_atau_buat_project  # noqa: PLC0415

        self.divisi, self.project, self.dep_obj = {}, {}, {}
        with tunda_sinkron():
            for kode, nama, deps in data.ORGANISASI:
                div = Divisi.objects.create(workspace=self.ws, kode=kode, nama=nama)
                self.divisi[kode] = div
                for kode_dep, nama_dep in deps:
                    dep = Departemen.objects.create(workspace=self.ws, divisi=div, kode=kode_dep, nama=nama_dep)
                    with impersonate(self.actor):
                        project = _adopsi_atau_buat_project(dep, self.actor, self.ws)
                    Project.objects.filter(pk=project.pk).update(
                        **FITUR_PROJECT,
                        project_lead=self.supervisor[kode_dep],
                        timezone=ZONA_WAKTU,
                        # Bentuk yang sama dengan yang dikirim modal "project baru" di web.
                        logo_props={"in_use": "emoji", "emoji": {"value": self.rng.choice(EMOJI_PROJECT)}},
                    )
                    with impersonate(self.actor):
                        Intake.objects.get_or_create(
                            project=project, workspace=self.ws, is_default=True, defaults={"name": "Intake"}
                        )
                    self.project[kode_dep] = project
                    self.dep_obj[kode_dep] = dep

    def _jabatan(self, user, tingkat, departemen=None, divisi=None):
        JabatanOrganisasi.objects.create(
            workspace=self.ws,
            member=user,
            tingkat=tingkat,
            departemen=departemen,
            divisi=divisi,
            sumber=data.SUMBER_DEMO,
        )

    def _tempatkan_jabatan(self):
        with tunda_sinkron():
            for u in self.direktur:
                self._jabatan(u, TINGKAT_DIREKTUR)
            for div, u in self.manager.items():
                self._jabatan(u, TINGKAT_MANAGER, divisi=self.divisi[div])
            for dep, u in self.supervisor.items():
                self._jabatan(u, TINGKAT_SUPERVISOR, departemen=self.dep_obj[dep])
            for dep, users in self.staf.items():
                for u in users:
                    self._jabatan(u, TINGKAT_MEMBER, departemen=self.dep_obj[dep])

    def _sinkron_wiki(self):
        from plane.license.api.views.organisasi import _sinkron_wiki  # noqa: PLC0415

        _sinkron_wiki(self.ws, self.actor)

    # ------------------------------------------------------------- isi project

    def _isi_project(self, kode_dep):
        project = self.project[kode_dep]
        spv = self.supervisor[kode_dep]
        staf = self.staf[kode_dep]
        states = {s.group: s for s in State.objects.filter(project=project).exclude(group="triage")}
        with impersonate(spv):
            labels = [Label.objects.create(project=project, workspace=self.ws, name=n, color=c) for n, c in data.LABEL]
            modules = self._modul(project, kode_dep, spv, staf)
            self._page(project, spv)
            self._view(project, spv)

        for i, (judul, subs) in enumerate(data.TUGAS[kode_dep]):
            induk = self._tugas_induk(project, judul, spv, staf, states, labels)
            ModuleIssue.objects.create(
                project=project, workspace=self.ws, module=modules[i % len(modules)], issue=induk["issue"]
            )
            for sub in subs:
                self._sub_tugas(project, sub, induk, spv, staf, states)
        self._tugas_admin(project, spv, staf, states, modules[0])

    def _tugas_admin(self, project, spv, staf, states, modul):
        """Super Admin ikut di data: sekali sebagai pemberi tugas, sekali sebagai penerima."""
        dep = project.name
        dari_admin = self._simpan_tugas(
            project, data.ADMIN_MEMBERI.format(dep=dep), self.actor, [self.rng.choice(staf)], states, "unstarted"
        )
        judul, subs = data.ADMIN_DIBERI
        ke_admin = self._simpan_tugas(project, judul.format(dep=dep), spv, [self.actor], states, "started")
        for sub in subs:
            self._simpan_tugas(project, sub.format(dep=dep), spv, [self.actor], states, "unstarted", parent=ke_admin)
        for issue in (dari_admin, ke_admin):
            ModuleIssue.objects.create(project=project, workspace=self.ws, module=modul, issue=issue)

    def _page(self, project, spv):
        halaman = [(spv, j, i) for j, i in data.PAGE] + [(self.actor, *data.ADMIN_PAGE)]
        for pemilik, judul, isi in halaman:
            with impersonate(pemilik):
                page = Page.objects.create(
                    workspace=self.ws,
                    owned_by=pemilik,
                    name=judul.format(dep=project.name),
                    description_html=isi.format(dep=project.name),
                    access=0,  # publik di dalam project
                    # Tanda seed: page milik Super Admin tidak ikut terhapus kaskade user demo.
                    external_source=data.SUMBER_DEMO,
                )
                ProjectPage.objects.create(workspace=self.ws, project=project, page=page)

    def _view(self, project, spv):
        from plane.utils.filters.converters import LegacyToRichFiltersConverter  # noqa: PLC0415

        konversi = LegacyToRichFiltersConverter()
        for nama, filters in data.VIEW:
            IssueView.objects.create(
                workspace=self.ws,
                project=project,
                owned_by=spv,
                name=nama,
                filters=filters,
                rich_filters=konversi.convert(filters),
                access=1,  # publik untuk anggota project
            )

    def _modul(self, project, kode_dep, spv, staf):
        hasil = []
        status = ["in-progress", "planned", "backlog"]
        for i, nama in enumerate(data.MODUL[kode_dep]):
            mulai = (self.now - timedelta(days=30 - i * 7)).date()
            m = Module.objects.create(
                project=project,
                workspace=self.ws,
                name=nama,
                description=f"Lingkup kerja {nama} untuk {project.name}.",
                status=status[i % len(status)],
                lead=spv,
                start_date=mulai,
                target_date=mulai + timedelta(days=60),
            )
            for u in [spv, *staf]:
                ModuleMember.objects.create(project=project, workspace=self.ws, module=m, member=u)
            hasil.append(m)
        return hasil

    def _pilih_grup(self):
        grup = [g for g, _ in BOBOT_STATUS]
        bobot = [b for _, b in BOBOT_STATUS]
        return self.rng.choices(grup, weights=bobot, k=1)[0]

    def _tugas_induk(self, project, judul, spv, staf, states, labels):
        # 70% diberi supervisor ke staf, 30% staf membuat tugas untuk dirinya sendiri.
        if self.rng.random() < 0.7:
            pembuat = spv
            penerima = self.rng.sample(staf, k=self.rng.choice([1, 1, 2]))
        else:
            pembuat = self.rng.choice(staf)
            penerima = [pembuat]
        grup = self._pilih_grup()
        issue = self._simpan_tugas(project, judul, pembuat, penerima, states, grup)
        for label in self.rng.sample(labels, k=self.rng.choice([0, 1, 1, 2])):
            IssueLabel.objects.create(project=project, workspace=self.ws, issue=issue, label=label)
        return {"issue": issue, "grup": grup, "penerima": penerima}

    def _sub_tugas(self, project, judul, induk, spv, staf, states):
        penerima = [self.rng.choice(induk["penerima"] if self.rng.random() < 0.7 else staf)]
        grup = induk["grup"] if self.rng.random() < 0.6 else self._pilih_grup()
        if induk["grup"] == "completed":
            grup = "completed"
        self._simpan_tugas(project, judul, spv, penerima, states, grup, parent=induk["issue"])

    def _simpan_tugas(self, project, judul, pembuat, penerima, states, grup, parent=None):
        dibuat = self.now - timedelta(days=self.rng.randint(4, 40), hours=self.rng.randint(0, 9))
        mulai = dibuat.date()
        tenggat = (self.now + timedelta(days=self.rng.randint(-8, 28))).date()
        if tenggat < mulai:
            tenggat = mulai + timedelta(days=self.rng.randint(2, 10))

        # Staf yang menggeser ke selesai harus menunggu atasan (KEP-28). Sebagian
        # tugas "selesai" milik staf dibuat masih menunggu: tugas tetap di In Progress.
        persetujuan = None
        if grup == "completed" and self.rng.random() < 0.25:
            persetujuan, grup = "menunggu", "started"
        elif grup == "started" and self.rng.random() < 0.1:
            persetujuan = "ditolak"
        elif grup == "completed":
            persetujuan = "disetujui"

        with impersonate(pembuat):
            issue = Issue(
                project=project,
                workspace=self.ws,
                name=judul,
                description_html=f"<p>{judul}. Detail dan lampiran ada di komentar.</p>",
                priority=self.rng.choice(PRIORITAS),
                state=states[grup],
                parent=parent,
                start_date=mulai,
                target_date=tenggat,
            )
            issue.save()
            for u in penerima:
                IssueAssignee.objects.create(project=project, workspace=self.ws, issue=issue, assignee=u)

        selesai = None
        if grup == "completed":
            selesai = min(self.now - timedelta(hours=self.rng.randint(2, 72)), dibuat + timedelta(days=14))
        # Tanggal dimundurkan SEBELUM aktivitas: `create_issue_activity` menyalin
        # `issue.created_at` ke baris "created the issue".
        Issue.objects.filter(pk=issue.pk).update(
            created_at=dibuat, updated_at=selesai or dibuat, start_date=mulai, target_date=tenggat, completed_at=selesai
        )
        self._aktivitas(
            "issue.activity.created",
            {"name": judul, "priority": issue.priority, "assignee_ids": [str(u.id) for u in penerima]},
            issue,
            pembuat,
            dibuat,
        )

        self._komentar(issue, project, pembuat, penerima, dibuat)
        if persetujuan:
            self._persetujuan(issue, project, penerima, persetujuan, states, selesai or self.now)
        return issue

    def _komentar(self, issue, project, pembuat, penerima, dibuat):
        if self.rng.random() > 0.45:
            return
        orang = list({pembuat, *penerima})
        # Super Admin sesekali ikut menimpali, supaya namanya muncul di riwayat diskusi.
        admin_ikut = self.actor not in orang and self.rng.random() < 0.2
        for n in range(self.rng.randint(1, 3) + admin_ikut):
            aktor = self.actor if admin_ikut and n == 0 else self.rng.choice(orang)
            teks = self.rng.choice(data.ADMIN_KOMENTAR if aktor == self.actor else data.KOMENTAR)
            with impersonate(aktor):
                c = IssueComment(
                    issue=issue,
                    project=project,
                    workspace=self.ws,
                    actor=aktor,
                    comment_html=f"<p>{teks}</p>",
                )
                c.save()
            waktu = min(dibuat + timedelta(days=n + 1, hours=n * 3), self.now - timedelta(minutes=30))
            IssueComment.objects.filter(pk=c.pk).update(created_at=waktu)
            self._aktivitas(
                "comment.activity.created", {"id": str(c.id), "comment_html": c.comment_html}, issue, aktor, waktu
            )

    def _aktivitas(self, jenis, requested, issue, aktor, waktu):
        """Riwayat + notifikasi lewat jalur yang sama dengan API, lalu dimundurkan ke `waktu`.

        Hanya baris aktivitas BARU yang dimundurkan; notifikasinya tetap bertanggal
        sekarang (dibuat worker), jadi Inbox terasa baru masuk.
        """
        sebelum = set(IssueActivity.objects.filter(issue=issue).values_list("id", flat=True))
        issue_activity(
            type=jenis,
            requested_data=json.dumps(requested),
            current_instance=None,
            issue_id=str(issue.id),
            actor_id=str(aktor.id),
            project_id=str(issue.project_id),
            epoch=int(waktu.timestamp()),
            notification=True,
            origin=getattr(settings, "WEB_URL", None),
        )
        IssueActivity.objects.filter(issue=issue).exclude(id__in=sebelum).update(created_at=waktu)

    def _persetujuan(self, issue, project, penerima, status, states, waktu):
        pemohon = next((u for u in penerima if self._staf_di(project, u)), None)
        if pemohon is None:
            return  # hanya staf yang butuh persetujuan
        penyetuju = self.supervisor[self._dep_dari_project(project)]
        baris = PersetujuanPenugasan(
            workspace=self.ws,
            project=project,
            issue=issue,
            pemohon=pemohon,
            penerima=pemohon,
            status=status,
            state_sebelumnya=states["started"],
        )
        if status != "menunggu":
            baris.diputuskan_oleh = penyetuju
            baris.diputuskan_pada = waktu
        if status == "ditolak":
            baris.alasan = self.rng.choice(data.ALASAN_TOLAK)
        baris.save(created_by_id=pemohon.id)
        PersetujuanPenugasan.objects.filter(pk=baris.pk).update(created_at=waktu - timedelta(hours=6))
        # Log persetujuan di riwayat aktivitas (KEP-55), dimundurkan ke waktu barisnya.
        from plane.db.models import IssueActivity  # noqa: PLC0415
        from plane.utils.hierarki import (  # noqa: PLC0415
            AKTIVITAS_DIAJUKAN,
            AKTIVITAS_DISETUJUI,
            AKTIVITAS_DITOLAK,
            catat_aktivitas_persetujuan,
        )

        diajukan = catat_aktivitas_persetujuan(baris, AKTIVITAS_DIAJUKAN, pemohon)
        IssueActivity.objects.filter(pk=diajukan.pk).update(created_at=waktu - timedelta(hours=6))
        if status != "menunggu":
            verb = AKTIVITAS_DISETUJUI if status == "disetujui" else AKTIVITAS_DITOLAK
            putusan = catat_aktivitas_persetujuan(baris, verb, penyetuju, baris.alasan)
            IssueActivity.objects.filter(pk=putusan.pk).update(created_at=waktu)
        if status == "menunggu":
            # Sama dengan `catat_persetujuan`: atasan yang boleh memutuskan dapat Inbox + email.
            from plane.utils.notifikasi_persetujuan import beritahu_diajukan  # noqa: PLC0415

            beritahu_diajukan(baris, issue=issue)

    def _dep_dari_project(self, project):
        return next(k for k, p in self.project.items() if p.pk == project.pk)

    def _staf_di(self, project, user):
        return user in self.staf[self._dep_dari_project(project)]

    # ------------------------------------------------------- lintas divisi

    def _permintaan_lintas_divisi(self):
        for asal_dep, tujuan_dep, judul, prioritas, catatan in data.PERMINTAAN_LINTAS:
            asal, tujuan = self.project[asal_dep], self.project[tujuan_dep]
            peminta = self.supervisor[asal_dep]
            intake = Intake.objects.get(project=tujuan, is_default=True)
            triage = State.triage_objects.filter(project=tujuan).first()
            # Sama dengan endpoint lintas divisi: Issue tanpa pembuat (penerima yang triase).
            issue = Issue(
                name=judul,
                description_html=f"<p>{catatan or judul}</p>",
                priority=prioritas,
                project=tujuan,
                workspace=self.ws,
                state=triage,
            )
            issue.save(disable_auto_set_user=True)
            with impersonate(peminta):
                intake_issue = IntakeIssue.objects.create(
                    intake=intake,
                    project=tujuan,
                    workspace=self.ws,
                    issue=issue,
                    source="CROSSDIV",
                    external_source=asal.identifier,
                    external_id=str(asal.id),
                    extra={
                        "crossdiv": {
                            "asal_project_id": str(asal.id),
                            "asal_identifier": asal.identifier,
                            "peminta_id": str(peminta.id),
                            "peminta": peminta.display_name,
                        }
                    },
                )
                PermintaanLintasDivisi.objects.create(
                    workspace=self.ws,
                    asal_project=asal,
                    tujuan_project=tujuan,
                    intake_issue=intake_issue,
                    diminta_oleh=peminta,
                    catatan=catatan,
                )

    # --------------------------------------------------------- isi pribadi

    def _isi_pribadi_semua(self):
        """Sidebar, favorit, sticky, quick link tiap akun demo. Favoritnya project departemennya."""
        rumah = {}
        for dep, u in self.supervisor.items():
            rumah.setdefault(u.id, self.project[dep])
        for dep, users in self.staf.items():
            for u in users:
                rumah[u.id] = self.project[dep]
        dep_pertama = {kode: deps[0][0] for kode, _, deps in data.ORGANISASI}
        for div, u in self.manager.items():
            rumah[u.id] = self.project[dep_pertama[div]]
        semua = [*self.direktur, *self.manager.values(), *self.supervisor_user.values()]
        semua += [u for users in self.staf.values() for u in users]
        for u in semua:
            with impersonate(u):
                isi_pribadi(self.ws, u, rumah.get(u.id), self.rng)

    # ------------------------------------------------------------ ringkasan

    def _jumlah_obrolan(self):
        ruang = Ruang.objects.filter(
            workspace=self.ws, langganan__user__email__endswith=f"@{data.DEMO_DOMAIN}"
        ).distinct()
        pesan = PesanLangsung.objects.filter(ruang__in=ruang).count()
        return f"{ruang.count()} ruang, {pesan} pesan"

    def _ringkasan(self):
        demo_projects = [p.pk for p in self.project.values()]
        status = {
            s: PersetujuanPenugasan.objects.filter(project_id__in=demo_projects, status=s).count()
            for s in ("menunggu", "disetujui", "ditolak")
        }
        self.stdout.write(
            self.style.SUCCESS(
                "Data demo siap:\n"
                f"  akun        {User.objects.filter(email__endswith='@' + data.DEMO_DOMAIN).count()}"
                f" (password {data.DEMO_PASSWORD})\n"
                f"  divisi      {len(self.divisi)}, departemen/project {len(self.project)}\n"
                f"  work item   {Issue.objects.filter(project_id__in=demo_projects).count()}\n"
                f"  modul       {Module.objects.filter(project_id__in=demo_projects).count()},"
                f" page {ProjectPage.objects.filter(project_id__in=demo_projects).count()},"
                f" view {IssueView.objects.filter(project_id__in=demo_projects).count()}\n"
                f"  persetujuan {status}\n"
                f"  konten      {self.konten}\n"
                f"  obrolan     {self._jumlah_obrolan()}\n"
                f"  contoh login: {_email(data.DIREKTUR[0][0])} (direktur),"
                f" {_email(data.MANAGER['SLS'])} (manager),"
                f" {_email(next(iter(data.SUPERVISOR)))} (supervisor),"
                f" {_email(data.STAF['SLS-DOM'][0])} (staf)"
            )
        )
