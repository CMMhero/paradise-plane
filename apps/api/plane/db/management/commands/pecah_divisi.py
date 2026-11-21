# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pecah satu divisi jadi beberapa divisi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`python manage.py pecah_divisi --sumber PC --rencana <berkas.json|->`
`[--workspace <slug>] [--manager KODE=<username|email|id>]... [--apply] [--no-hapus-sumber]`

Memecah satu divisi menjadi beberapa divisi baru di cabang yang SAMA, menurut
berkas rencana (contoh: `paradise/rencana/pecah-plant-cilegon.json`). Tanpa
`--apply` hanya mencetak apa yang akan ditulis.

Yang ditulis, semuanya dalam satu transaksi:

1. Divisi baru dibuat di cabang divisi sumber (sama dengan POST divisi God Mode).
2. Tiap departemen dipindah ke divisi barunya. Id departemen dan baris
   `DepartemenProject`-nya tidak berubah, jadi papan kerja, tugas, dan anggotanya
   tetap (sama dengan PATCH departemen God Mode).
3. Folder Wiki divisi sumber dilepas dari divisinya (foldernya tetap), dan quick
   link bersama yang menyasar divisi sumber dilepas dari sasaran itu. Judulnya
   dicetak, karena sasaran itu hilang.
4. Divisi sumber dihapus lunak kalau sudah kosong.
5. Manager ditempatkan di divisi barunya lewat `setel_penempatan`, persis jalur
   POST /api/instances/hierarki/ dengan `divisi_id`: jenjang naik ke Manager,
   departemen lamanya di dalam divisi yang kini ia pimpin dilepas (KEP-93),
   departemen di divisi lain tetap.
6. Sinkron hierarki satu kali (akses project + kanal obrolan), lalu turunan Wiki
   (folder divisi baru, folder departemen pindah induk).

Idempoten: rencana dihitung dari keadaan sekarang. Divisi rencana yang sudah ada
dengan kode, nama, dan cabang yang sama dipakai ulang; departemen yang sudah di
divisi tujuannya dilewati. Jalan ulang sesudah berhasil mencetak "Nothing to
change." Keadaan yang tidak cocok dengan rencana dihentikan sebelum ada yang
ditulis.
"""

# Python imports
import json
import sys
import uuid
from argparse import BooleanOptionalAction
from dataclasses import dataclass, field

# Django imports
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

# Module imports
from plane.db.jangkauan import sinkronkan_workspace, tunda_sinkron
from plane.db.models import (
    DOMAIN_AKUN_TERHAPUS,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    JabatanOrganisasi,
    ProjectMember,
    QuickLinkBersama,
    TINGKAT_MANAGER,
    TINGKAT_NAMA,
    User,
    WikiFolder,
    Workspace,
    WorkspaceMember,
)
from plane.db.penempatan import departemen_dalam_divisi, penempatan_sekarang, setel_penempatan
from plane.license.api.views.organisasi import _kode_nama, _sinkron_wiki
from plane.utils.hierarki import jangkauan_hierarki

SUMBER = "pecah-divisi"


# --------------------------------------------------------------------------
# Rencana (hanya baca)
# --------------------------------------------------------------------------


@dataclass
class DivisiRencana:
    kode: str
    nama: str
    departemen_kode: list
    perlu_manager: bool
    ada: Divisi | None = None
    departemen: list = field(default_factory=list)
    pindah: list = field(default_factory=list)
    manager: User | None = None
    manager_baru: bool = False
    manager_tingkat: int | None = None
    manager_lama: list = field(default_factory=list)


@dataclass
class Rencana:
    workspace: Workspace
    sumber: Divisi
    divisi: list
    hapus_sumber: bool
    folder_wiki: list = field(default_factory=list)
    quick_link: list = field(default_factory=list)
    # {user_id: [nama departemen yang barisnya dilepas karena divisinya kini ia pimpin]}
    dilepas: dict = field(default_factory=dict)

    @property
    def cabang(self):
        return self.sumber.cabang

    def langkah(self):
        hasil = []
        tempat = f"branch {self.cabang.kode}" if self.cabang else "head office"
        for d in self.divisi:
            if d.ada is None:
                hasil.append(f"Create division {d.kode} {d.nama} in {tempat}.")
            for dep in d.pindah:
                hasil.append(f"Move department {dep.kode} {dep.nama} from {self.sumber.kode} to {d.kode}.")
        for f in self.folder_wiki:
            hasil.append(f"Detach Wiki folder '{f.nama}' from division {self.sumber.kode} (the folder stays).")
        for q in self.quick_link:
            hasil.append(
                f"Remove division {self.sumber.kode} from shared quick link '{judul_quick_link(q)}'. "
                "Its readers in that division lose it."
            )
        if self.hapus_sumber:
            hasil.append(f"Soft-delete the emptied division {self.sumber.kode} {self.sumber.nama}.")
        for d in self.divisi:
            if d.manager_baru:
                sekarang = TINGKAT_NAMA.get(d.manager_tingkat, "Member")
                hasil.append(f"Place {d.manager.display_name} (now {sekarang}) as Manager of {d.kode} {d.nama}.")
                for nama in self.dilepas.get(d.manager.id, []):
                    hasil.append(
                        f"{d.manager.display_name} leaves their seat in department {nama}: "
                        "the division they now lead covers it (KEP-93)."
                    )
        return hasil


def judul_quick_link(q):
    return q.title or (q.metadata or {}).get("title") or q.url


def baca_rencana(teks, sumber_kode):
    """Isi berkas rencana -> daftar (kode, nama, [kode departemen], perlu_manager).

    Murni: tidak membaca database. Semua kesalahan dikumpulkan dan dilempar sekaligus.
    """
    try:
        data = json.loads(teks)
    except json.JSONDecodeError as e:
        raise CommandError(f"The plan is not valid JSON: {e}.") from e
    if not isinstance(data, dict) or not isinstance(data.get("divisi"), list) or not data["divisi"]:
        raise CommandError('The plan needs a non-empty "divisi" list.')
    galat = []
    if data.get("sumber") and str(data["sumber"]).strip().upper() != sumber_kode:
        galat.append(f"The plan is for division {data['sumber']}, not {sumber_kode}.")
    hasil, kode_divisi, kode_dep = [], set(), set()
    for i, baris in enumerate(data["divisi"], 1):
        if not isinstance(baris, dict):
            galat.append(f"Division #{i} must be an object.")
            continue
        kode, nama, salah = _kode_nama(baris, wajib=True)
        if salah:
            galat.append(f"Division #{i}: {salah}")
            continue
        if kode in kode_divisi:
            galat.append(f"Division code {kode} appears twice in the plan.")
        if kode == sumber_kode:
            galat.append(f"Division code {kode} is the division being split.")
        kode_divisi.add(kode)
        deps = baris.get("departemen")
        if not isinstance(deps, list) or not deps:
            galat.append(f"Division {kode} needs a non-empty departemen list.")
            continue
        deps = [str(x).strip().upper() for x in deps]
        for dk in deps:
            if dk in kode_dep:
                galat.append(f"Department {dk} appears in more than one division of the plan.")
            kode_dep.add(dk)
        hasil.append((kode, nama, deps, bool(baris.get("manager"))))
    if galat:
        raise CommandError("The plan is invalid:\n- " + "\n- ".join(galat))
    return hasil


def _cari_user(workspace, ref):
    """Tepat satu anggota aktif workspace untuk `ref` (username, email, atau id). (user, galat)."""
    ref = ref.strip()
    kandidat = User.objects.filter(username__iexact=ref) | User.objects.filter(email__iexact=ref)
    try:
        kandidat = kandidat | User.objects.filter(id=uuid.UUID(ref))
    except ValueError:
        pass
    aktif = WorkspaceMember.objects.filter(workspace=workspace, is_active=True).values("member_id")
    cocok = list(
        kandidat.filter(id__in=aktif, is_active=True).exclude(email__endswith=f"@{DOMAIN_AKUN_TERHAPUS}").distinct()
    )
    if not cocok:
        return None, f"'{ref}' is not an active member of {workspace.slug}."
    if len(cocok) > 1:
        daftar = ", ".join(f"{u.display_name} ({u.id})" for u in cocok)
        return None, f"'{ref}' matches more than one member: {daftar}. Use the user id."
    return cocok[0], None


def rencanakan(workspace, sumber_kode, isi_rencana, manager_ref, hapus_sumber=True):
    """Bandingkan rencana dengan database. Hanya membaca; dry-run dan apply sama-sama memakainya.

    `manager_ref` = {kode divisi: username|email|id}. Melempar CommandError berisi
    SEMUA masalah sebelum satu baris pun ditulis.
    """
    sumber = (
        Divisi.all_objects.filter(workspace=workspace, kode=sumber_kode)
        .select_related("cabang")
        .order_by("-deleted_at")  # yang aktif (NULL) dulu di Postgres DESC
        .first()
    )
    if sumber is None:
        raise CommandError(f"Division {sumber_kode} not found in {workspace.slug}.")

    galat = []
    divisi = [DivisiRencana(kode=k, nama=n, departemen_kode=d, perlu_manager=m) for k, n, d, m in isi_rencana]
    per_kode = {d.kode: d for d in divisi}

    # Divisi rencana yang sudah ada: dipakai ulang hanya kalau jelas sisa jalan
    # sebelumnya (cabang dan nama sama). Selain itu kodenya bentrok.
    for d in divisi:
        lain = Divisi.objects.filter(workspace=workspace, kode=d.kode).select_related("cabang").first()
        if lain is None:
            continue
        if lain.id == sumber.id or lain.cabang_id != sumber.cabang_id or lain.nama != d.nama:
            tempat = lain.cabang.kode if lain.cabang else "head office"
            galat.append(f"Division code {d.kode} is already used by {lain.kode} {lain.nama} ({tempat}).")
            continue
        d.ada = lain

    # Departemen: tiap kode rencana harus ada, dan berada di sumber atau sudah di tujuannya.
    tujuan_dep = {dk: d for d in divisi for dk in d.departemen_kode}
    semua_dep = {
        dep.kode: dep
        for dep in Departemen.objects.filter(workspace=workspace, kode__in=list(tujuan_dep)).select_related("divisi")
    }
    for dk, d in tujuan_dep.items():
        dep = semua_dep.get(dk)
        if dep is None:
            galat.append(f"Department {dk} in the plan does not exist.")
            continue
        d.departemen.append(dep)
        if dep.divisi_id == sumber.id:
            d.pindah.append(dep)
        elif d.ada is None or dep.divisi_id != d.ada.id:
            galat.append(f"Department {dk} is in division {dep.divisi.kode}, not in {sumber.kode}.")
    for dep in Departemen.objects.filter(divisi=sumber).exclude(kode__in=list(tujuan_dep)).order_by("kode"):
        galat.append(f"Department {dep.kode} {dep.nama} is in {sumber.kode} but not in the plan.")
    for d in divisi:
        if d.ada is None:
            continue
        for dep in Departemen.objects.filter(divisi=d.ada).exclude(kode__in=d.departemen_kode).order_by("kode"):
            galat.append(f"Existing division {d.kode} holds {dep.kode}, which the plan puts elsewhere.")

    # Manager.
    for kode in sorted(set(manager_ref) - set(per_kode)):
        galat.append(f"--manager {kode}: no division {kode} in the plan.")
    manager_per_user = {}
    for d in divisi:
        if d.ada is not None:
            d.manager_lama = list(
                JabatanOrganisasi.objects.filter(divisi=d.ada, tingkat__gte=TINGKAT_MANAGER)
                .select_related("member")
                .values_list("member__display_name", flat=True)
            )
        ref = manager_ref.get(d.kode)
        if ref is None:
            if d.perlu_manager and not d.manager_lama:
                galat.append(f"Division {d.kode} needs a manager: pass --manager {d.kode}=<username|email|id>.")
            continue
        if not d.perlu_manager:
            galat.append(f"--manager {d.kode}: the plan keeps {d.kode} vacant. Change the plan first.")
            continue
        user, salah = _cari_user(workspace, ref)
        if salah:
            galat.append(f"--manager {d.kode}: {salah}")
            continue
        tingkat, _, _ = penempatan_sekarang(workspace.id, user.id)
        if tingkat is not None and tingkat > TINGKAT_MANAGER:
            galat.append(
                f"--manager {d.kode}: {user.display_name} is {TINGKAT_NAMA.get(tingkat, tingkat)}, "
                "above Manager. Change their level in God Mode first."
            )
            continue
        d.manager = user
        d.manager_tingkat = tingkat
        d.manager_baru = (
            d.ada is None
            or not JabatanOrganisasi.objects.filter(divisi=d.ada, member=user, tingkat__gte=TINGKAT_MANAGER).exists()
        )
        if d.manager_baru:
            manager_per_user.setdefault(user.id, []).append(d)

    hapus = hapus_sumber and sumber.deleted_at is None
    if hapus:
        sisa = list(JabatanOrganisasi.objects.filter(divisi=sumber).values_list("member__display_name", flat=True))
        if sisa:
            galat.append(
                f"Managers are still placed in {sumber.kode}: {', '.join(sisa)}. "
                "Move them in God Mode first, or run with --no-hapus-sumber."
            )

    if galat:
        raise CommandError("Nothing was written. Fix these first:\n- " + "\n- ".join(galat))

    rencana = Rencana(workspace=workspace, sumber=sumber, divisi=divisi, hapus_sumber=hapus)
    rencana.folder_wiki = list(WikiFolder.objects.filter(divisi=sumber))
    rencana.quick_link = list(QuickLinkBersama.objects.filter(divisi=sumber).order_by("sort_order", "created_at"))

    # Departemen lama tiap calon manager yang tertelan divisi yang akan ia pimpin
    # (KEP-93), dihitung pada struktur SESUDAH rencana.
    tujuan = {str(dep.id): d for d in divisi for dep in d.departemen}
    for user_id, dipimpin in manager_per_user.items():
        _, deps, divs = penempatan_sekarang(workspace.id, user_id)
        kode_dipimpin = {d.kode for d in dipimpin} | {d.kode for d in divisi if d.ada and str(d.ada.id) in divs}
        lepas = [dep_id for dep_id in deps if dep_id in tujuan and tujuan[dep_id].kode in kode_dipimpin]
        if lepas:
            rencana.dilepas[user_id] = sorted(
                f"{k} {n}" for k, n in Departemen.objects.filter(id__in=lepas).values_list("kode", "nama")
            )
    return rencana


# --------------------------------------------------------------------------
# Tulis
# --------------------------------------------------------------------------


def terapkan(rencana):
    """Tulis rencana. Pemanggil membungkusnya dengan transaction.atomic() + tunda_sinkron(),
    lalu memanggil sinkronkan_workspace sekali."""
    ws, sumber = rencana.workspace, rencana.sumber
    for d in rencana.divisi:
        if d.ada is None:
            d.ada = Divisi.objects.create(workspace=ws, kode=d.kode, nama=d.nama, cabang_id=sumber.cabang_id)
    for d in rencana.divisi:
        for dep in d.pindah:
            dep.divisi = d.ada
            dep.save(update_fields=["kode", "nama", "divisi", "updated_at"])

    WikiFolder.all_objects.filter(divisi=sumber).update(divisi=None)
    for q in rencana.quick_link:
        q.divisi.remove(sumber)

    if rencana.hapus_sumber:
        # Hapus lunak lewat queryset, BUKAN `sumber.delete()`: versi instance
        # mengirim tugas Celery `soft_delete_related_objects` sebelum transaksi
        # ini commit. Worker yang membacanya lebih dulu masih melihat departemen
        # di divisi ini dan ikut menghapusnya; kalau transaksi batal, ia tetap
        # menghapus divisinya. Relasi SET_NULL (folder Wiki) sudah dilepas di
        # atas, dan divisi ini dipastikan tanpa departemen dan manager.
        Divisi.objects.filter(pk=sumber.pk).delete()

    # Manager terakhir: `departemen_dalam_divisi` harus membaca departemen yang
    # sudah dipindah. Satu panggilan per orang, untuk semua divisi yang ia pimpin.
    per_user = {}
    for d in rencana.divisi:
        if d.manager_baru:
            per_user.setdefault(d.manager.id, (d.manager, set()))[1].add(str(d.ada.id))
    for user, divisi_ids in per_user.values():
        tingkat, deps, divs = penempatan_sekarang(ws.id, user.id)
        divs = divs | divisi_ids
        tingkat = TINGKAT_MANAGER if tingkat is None or tingkat < TINGKAT_MANAGER else tingkat
        deps = deps - departemen_dalam_divisi(deps, divs)
        setel_penempatan(ws, user, tingkat, deps, divs, sumber=SUMBER)


# --------------------------------------------------------------------------
# Ringkasan
# --------------------------------------------------------------------------


def _jangkauan(workspace_id, user_id):
    """(papan kerja, orang) yang dijangkau satu orang lewat hierarki."""
    pids = list(jangkauan_hierarki(user_id, workspace_id))
    orang = (
        ProjectMember.objects.filter(project_id__in=pids, is_active=True, member__is_active=True, member__is_bot=False)
        .values("member_id")
        .distinct()
        .count()
    )
    return len(pids), orang


def _orang(departemen, divisi_ids=()):
    """Orang yang duduk di departemen ini atau memimpin salah satu divisi ini."""
    return set(
        JabatanOrganisasi.objects.filter(Q(departemen__in=departemen) | Q(divisi_id__in=list(divisi_ids))).values_list(
            "member_id", flat=True
        )
    )


def _baris_divisi(divisi):
    deps = list(Departemen.objects.filter(divisi=divisi).order_by("kode"))
    papan = DepartemenProject.objects.filter(departemen__in=deps).count()
    orang = len(_orang(deps, [divisi.id]))
    manager = list(
        JabatanOrganisasi.objects.filter(divisi=divisi, tingkat__gte=TINGKAT_MANAGER).values_list(
            "member__display_name", flat=True
        )
    )
    return (
        f"{divisi.kode} {divisi.nama}",
        ", ".join(d.kode for d in deps) or "-",
        ", ".join(sorted(manager)) or "(vacant)",
        str(papan),
        str(orang),
    )


def _cetak_tabel(out, baris):
    kepala = ("Division", "Departments", "Manager", "Boards", "People")
    lebar = [max(len(r[i]) for r in [kepala, *baris]) for i in range(len(kepala))]
    for r in [kepala, *baris]:
        out.write("  " + "  ".join(r[i].ljust(lebar[i]) for i in range(len(kepala))).rstrip())


class Command(BaseCommand):
    help = "Split one division into several divisions in the same branch, following a JSON plan. Dry run by default."

    def add_arguments(self, parser):
        parser.add_argument("--workspace", help="Workspace slug. Optional when there is exactly one workspace.")
        parser.add_argument("--sumber", required=True, help="Code of the division to split, e.g. PC.")
        parser.add_argument("--rencana", required=True, help="Path to the JSON plan, or - to read it from stdin.")
        parser.add_argument(
            "--manager",
            action="append",
            default=[],
            metavar="KODE=USER",
            help="Place USER (username, email or user id) as Manager of the new division KODE. Repeatable.",
        )
        parser.add_argument("--apply", action="store_true", help="Write the changes. Without it nothing is written.")
        parser.add_argument(
            "--hapus-sumber",
            action=BooleanOptionalAction,
            default=True,
            help="Soft-delete the source division once it is empty (default on).",
        )

    def handle(self, *args, **options):
        workspace = self._workspace(options["workspace"])
        sumber_kode = options["sumber"].strip().upper()
        isi = self._baca(options["rencana"])
        rencana_isi = baca_rencana(isi, sumber_kode)
        manager_ref = {}
        for nilai in options["manager"]:
            kode, sep, ref = nilai.partition("=")
            kode = kode.strip().upper()
            if not sep or not kode or not ref.strip():
                raise CommandError(f"--manager {nilai}: use KODE=<username|email|id>.")
            if kode in manager_ref:
                raise CommandError(f"--manager {kode} is given twice.")
            manager_ref[kode] = ref

        if not options["apply"]:
            rencana = rencanakan(workspace, sumber_kode, rencana_isi, manager_ref, options["hapus_sumber"])
            self._sebelum(rencana)
            langkah = rencana.langkah()
            if not langkah:
                self._selesai(rencana)
                return
            self._cetak_langkah(langkah)
            self._rencana_akhir(rencana)
            self.stdout.write("Dry run: nothing was written. Run again with --apply to write it.")
            return

        with transaction.atomic():
            # Kunci divisi sumber: God Mode yang menyunting PC bersamaan menunggu.
            list(Divisi.all_objects.select_for_update().filter(workspace=workspace, kode=sumber_kode))
            rencana = rencanakan(workspace, sumber_kode, rencana_isi, manager_ref, options["hapus_sumber"])
            self._sebelum(rencana)
            langkah = rencana.langkah()
            if not langkah:
                self._selesai(rencana)
                return
            self._cetak_langkah(langkah)
            jangkauan_sebelum = {
                d.manager.id: _jangkauan(workspace.id, d.manager.id) for d in rencana.divisi if d.manager_baru
            }
            with tunda_sinkron():
                terapkan(rencana)
            berubah = sinkronkan_workspace(workspace.id)
        # Sesudah commit, sama dengan endpoint God Mode: turunan Wiki menelan
        # galatnya sendiri dan menyusul sendiri tiap pohon Wiki dibaca (KEP-95).
        _sinkron_wiki(workspace, None)

        self.stdout.write("After:")
        _cetak_tabel(self.stdout, [_baris_divisi(d.ada) for d in rencana.divisi])
        if rencana.hapus_sumber:
            self.stdout.write(f"  Division {rencana.sumber.kode} {rencana.sumber.nama} is deleted.")
        self._total(rencana)
        if jangkauan_sebelum:
            self.stdout.write("Manager reach (work boards / people on them):")
            for d in rencana.divisi:
                if d.manager_baru:
                    p0, o0 = jangkauan_sebelum[d.manager.id]
                    p1, o1 = _jangkauan(workspace.id, d.manager.id)
                    self.stdout.write(f"  {d.manager.display_name} ({d.kode}): before {p0} / {o0}, after {p1} / {o1}")
        for q in rencana.quick_link:
            self.stdout.write(f"Shared quick link no longer aimed at {rencana.sumber.kode}: '{judul_quick_link(q)}'.")
        self.stdout.write(self.style.SUCCESS(f"Done. {berubah} project memberships changed by the hierarchy sync."))

    # ----------------------------------------------------------------------

    def _workspace(self, slug):
        if slug:
            ws = Workspace.objects.filter(slug=slug).first()
            if ws is None:
                raise CommandError(f"Workspace {slug} not found.")
            return ws
        semua = list(Workspace.objects.all()[:2])
        if len(semua) != 1:
            raise CommandError("More than one workspace exists. Pass --workspace <slug>.")
        return semua[0]

    def _baca(self, path):
        if path == "-":
            return sys.stdin.read()
        try:
            with open(path, encoding="utf-8") as berkas:
                return berkas.read()
        except OSError as e:
            raise CommandError(f"Cannot read the plan {path}: {e}.") from e

    def _sebelum(self, rencana):
        s = rencana.sumber
        tempat = f"branch {rencana.cabang.kode} {rencana.cabang.nama}" if rencana.cabang else "head office"
        self.stdout.write(f"Workspace {rencana.workspace.slug}, {tempat}.")
        self.stdout.write("Before:")
        divisi = list(Divisi.objects.filter(workspace=rencana.workspace, cabang_id=s.cabang_id).order_by("kode"))
        _cetak_tabel(self.stdout, [_baris_divisi(d) for d in divisi])
        if s.deleted_at is not None:
            self.stdout.write(f"  Division {s.kode} is already deleted.")
        if s.cabang_id:
            pusat = list(
                Divisi.objects.filter(workspace=rencana.workspace, cabang__isnull=True)
                .order_by("kode")
                .values_list("kode", flat=True)
            )
            self.stdout.write(f"Head office divisions, not touched: {', '.join(pusat) or '-'}.")
        self._total(rencana)

    def _total(self, rencana):
        """Angka yang harus sama sebelum dan sesudah: bukti tidak ada yang hilang."""
        deps = [dep for d in rencana.divisi for dep in d.departemen]
        projects = list(DepartemenProject.objects.filter(departemen__in=deps).values_list("project_id", flat=True))
        divisi_ids = [rencana.sumber.id, *(d.ada.id for d in rencana.divisi if d.ada)]
        self.stdout.write(
            f"Total: {len(deps)} departments, {len(projects)} work boards, "
            f"{Issue.issue_objects.filter(project_id__in=projects).count()} work items, "
            f"{len(_orang(deps, divisi_ids))} people placed in them or leading them."
        )

    def _cetak_langkah(self, langkah):
        self.stdout.write("Steps:")
        for baris in langkah:
            self.stdout.write(f"- {baris}")

    def _rencana_akhir(self, rencana):
        self.stdout.write("After (planned):")
        baris = []
        for d in rencana.divisi:
            manager = sorted({*d.manager_lama, *([d.manager.display_name] if d.manager else [])})
            baris.append(
                (
                    f"{d.kode} {d.nama}",
                    ", ".join(sorted(dep.kode for dep in d.departemen)),
                    ", ".join(manager) or "(vacant)",
                    str(DepartemenProject.objects.filter(departemen__in=d.departemen).count()),
                    str(
                        len(
                            _orang(d.departemen, [d.ada.id] if d.ada else []) | ({d.manager.id} if d.manager else set())
                        )
                    ),
                )
            )
        _cetak_tabel(self.stdout, baris)
        for d in rencana.divisi:
            if d.manager_baru:
                papan, orang = _jangkauan(rencana.workspace.id, d.manager.id)
                self.stdout.write(f"  {d.manager.display_name} reaches {papan} work boards / {orang} people today.")

    def _selesai(self, rencana):
        kode = ", ".join(d.kode for d in rencana.divisi)
        status = "is deleted" if rencana.sumber.deleted_at is not None else "is empty"
        self.stdout.write(
            self.style.SUCCESS(f"Nothing to change. Division {rencana.sumber.kode} {status} and {kode} are in place.")
        )
