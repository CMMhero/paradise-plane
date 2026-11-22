# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jadikan satu divisi cabang (P29)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`python manage.py jadikan_cabang --divisi PC --kode CLG --nama "Plant Cilegon"`
`[--direktur-cabang <email>] [--dry-run]`

Membuat cabang (kalau belum ada), memindahkan satu divisi ke dalamnya, dan
opsional menempatkan Direktur Cabang. Departemen, project, tugas, dan penempatan
orang di divisi itu tidak disentuh: yang berubah hanya `Divisi.cabang`, jadi
keanggotaan project mereka tetap sama. Yang bertambah hanya jangkauan Direktur
Cabang (sinkron hierarki sesudahnya) dan kanal obrolan cabang.

Idempoten: tiap langkah dihitung dari keadaan sekarang, jadi menjalankannya lagi
sesudah berhasil tidak mengubah apa pun. `--dry-run` hanya mencetak langkahnya.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from plane.db.jangkauan import sinkronkan_workspace, tunda_sinkron
from plane.db.models import (
    Cabang,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    JabatanOrganisasi,
    TINGKAT_CABANG,
    User,
    WorkspaceMember,
)
from plane.db.penempatan import cabang_sekarang, penempatan_sekarang, setel_penempatan
from plane.license.api.views.organisasi import _kode_nama, _workspace_utama

SUMBER = "jadikan-cabang"


class Command(BaseCommand):
    help = "Turn a division into a branch: create the branch, move the division into it, place Branch Managers."

    def add_arguments(self, parser):
        parser.add_argument("--divisi", required=True, help="Code of the division to move, e.g. PC.")
        parser.add_argument("--kode", required=True, help="Code of the branch, e.g. CLG.")
        parser.add_argument("--nama", required=True, help='Name of the branch, e.g. "Plant Cilegon".')
        parser.add_argument(
            "--direktur-cabang",
            dest="direktur",
            action="append",
            default=[],
            metavar="EMAIL",
            help="Place this person as Branch Manager. Repeat for more than one.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Print the steps without changing anything.")

    def handle(self, *args, **options):
        workspace = _workspace_utama()
        if workspace is None:
            raise CommandError("No workspace found.")
        kode, nama, galat = _kode_nama({"kode": options["kode"], "nama": options["nama"]}, wajib=True)
        if galat:
            raise CommandError(galat)

        divisi = Divisi.objects.filter(workspace=workspace, kode=options["divisi"].strip().upper()).first()
        if divisi is None:
            raise CommandError(f"Division {options['divisi']} not found.")
        cabang = Cabang.objects.filter(workspace=workspace, kode=kode).first()
        if divisi.cabang_id and (cabang is None or divisi.cabang_id != cabang.id):
            raise CommandError(
                f"Division {divisi.kode} already belongs to branch {divisi.cabang.kode}. "
                "Move it to head office in God Mode first."
            )

        direktur = []
        for email in options["direktur"]:
            user = User.objects.filter(email__iexact=email.strip()).first()
            if (
                user is None
                or not WorkspaceMember.objects.filter(workspace=workspace, member=user, is_active=True).exists()
            ):
                raise CommandError(f"{email} is not an active member of {workspace.slug}.")
            tingkat, _, _ = penempatan_sekarang(workspace.id, user.id)
            if tingkat is not None and tingkat > TINGKAT_CABANG:
                raise CommandError(f"{email} is above Branch Manager. Change their level in God Mode first.")
            direktur.append(user)

        self._ringkasan(divisi)

        langkah = []
        if cabang is None:
            langkah.append(f"Create branch {kode} {nama}.")
        elif cabang.nama != nama:
            langkah.append(f"Rename branch {kode} from {cabang.nama} to {nama}.")
        if cabang is None or divisi.cabang_id != cabang.id:
            langkah.append(f"Move division {divisi.kode} {divisi.nama} from head office into branch {kode}.")
        promosi = [
            u
            for u in direktur
            if cabang is None
            or penempatan_sekarang(workspace.id, u.id)[0] != TINGKAT_CABANG
            or str(cabang.id) not in cabang_sekarang(workspace.id, u.id)
        ]
        for u in promosi:
            langkah.append(f"Place {u.display_name} <{u.email}> as Branch Manager of {kode}.")

        if not langkah:
            self.stdout.write(self.style.SUCCESS("Nothing to change."))
            return
        for baris in langkah:
            self.stdout.write(f"- {baris}")
        if options["dry_run"]:
            self.stdout.write("Dry run: nothing was written.")
            return

        with transaction.atomic(), tunda_sinkron():
            if cabang is None:
                cabang = Cabang.objects.create(workspace=workspace, kode=kode, nama=nama)
            elif cabang.nama != nama:
                cabang.nama = nama
                cabang.save(update_fields=["nama", "updated_at"])
            if divisi.cabang_id != cabang.id:
                divisi.cabang = cabang
                divisi.save(update_fields=["cabang", "updated_at"])
            for u in promosi:
                _, deps, divs = penempatan_sekarang(workspace.id, u.id)
                setel_penempatan(
                    workspace,
                    u,
                    TINGKAT_CABANG,
                    deps,
                    divs,
                    sumber=SUMBER,
                    cabang_ids=cabang_sekarang(workspace.id, u.id) | {str(cabang.id)},
                )
        berubah = sinkronkan_workspace(workspace.id)
        self._ringkasan(divisi)
        self.stdout.write(self.style.SUCCESS(f"Done. {berubah} project memberships changed by the hierarchy sync."))

    def _ringkasan(self, divisi):
        """Angka yang harus sama sebelum dan sesudah: bukti tidak ada yang hilang."""
        departemen = Departemen.objects.filter(divisi=divisi)
        projects = DepartemenProject.objects.filter(departemen__in=departemen).values_list("project_id", flat=True)
        self.stdout.write(
            f"{divisi.kode}: {departemen.count()} departments, {len(projects)} projects, "
            f"{Issue.issue_objects.filter(project_id__in=list(projects)).count()} work items, "
            f"{JabatanOrganisasi.objects.filter(departemen__in=departemen).values('member_id').distinct().count()} "
            "people placed in its departments."
        )
