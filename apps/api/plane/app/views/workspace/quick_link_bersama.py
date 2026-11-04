# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: quick link bersama (KEP-82)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Quick link yang dipasang admin untuk semua orang atau divisi/departemen tertentu.

    GET    /api/workspaces/<slug>/quick-links/shared/
    POST   /api/workspaces/<slug>/quick-links/shared/            (admin)
    PATCH  /api/workspaces/<slug>/quick-links/shared/<id>/       (admin)
    DELETE /api/workspaces/<slug>/quick-links/shared/<id>/       (admin)

GET untuk anggota biasa: `links` = yang berlaku untuknya. Untuk admin juga `semua`
(termasuk yang bukan sasarannya, supaya bisa diurus) dan `organisasi` (pilihan sasaran).
"""

# Django imports
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WorkspaceEntityPermission
from plane.app.views.base import BaseAPIView
from plane.bgtasks.quick_link_task import JENIS_BERSAMA
from plane.db.models import (
    CAKUPAN_QUICK_LINK_ORGANISASI,
    CAKUPAN_QUICK_LINK_SEMUA,
    Departemen,
    Divisi,
    QuickLinkBersama,
    Workspace,
)
from plane.utils.quick_link import (
    MAKS_JUDUL,
    LogoTidakValid,
    berlaku_untuk,
    boleh_kelola_bersama,
    isi_metadata_lama,
    metadata_baru,
    rapikan_logo,
    sasaran_pengguna,
)

_CAKUPAN = {CAKUPAN_QUICK_LINK_SEMUA, CAKUPAN_QUICK_LINK_ORGANISASI}


def _serial(link) -> dict:
    return {
        "id": str(link.id),
        "url": link.url,
        "title": link.title,
        "metadata": link.metadata or {},
        "cakupan": link.cakupan,
        "departemen_ids": [str(d.id) for d in link.departemen.all()],
        "divisi_ids": [str(v.id) for v in link.divisi.all()],
        "sort_order": link.sort_order,
        "created_at": link.created_at,
    }


def _organisasi(workspace_id) -> list[dict]:
    departemen_per_divisi: dict = {}
    for d in Departemen.objects.filter(workspace_id=workspace_id).order_by("nama"):
        departemen_per_divisi.setdefault(d.divisi_id, []).append({"id": str(d.id), "kode": d.kode, "nama": d.nama})
    return [
        {"id": str(v.id), "kode": v.kode, "nama": v.nama, "departemen": departemen_per_divisi.get(v.id, [])}
        for v in Divisi.objects.filter(workspace_id=workspace_id).order_by("nama")
    ]


def _rapikan_url(url) -> str | None:
    url = (url or "").strip() if isinstance(url, str) else ""
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        URLValidator()(url)
    except ValidationError:
        return None
    return url


def _ids(nilai) -> list[str] | None:
    if nilai is None:
        return []
    if not isinstance(nilai, list) or not all(isinstance(i, str) for i in nilai):
        return None
    return list(dict.fromkeys(nilai))


class QuickLinkBersamaEndpoint(BaseAPIView):
    permission_classes = [WorkspaceEntityPermission]

    def _semua(self, workspace_id):
        return list(QuickLinkBersama.objects.filter(workspace_id=workspace_id).prefetch_related("departemen", "divisi"))

    def _baca(self, data, workspace_id, link=None):
        """Masukan POST/PATCH -> (nilai, galat). PATCH hanya menyentuh kunci yang dikirim."""
        nilai = {}
        if link is None or "url" in data:
            url = _rapikan_url(data.get("url"))
            if url is None:
                return None, "Enter a valid URL."
            nilai["url"] = url
        if "title" in data:
            judul = data.get("title")
            if judul is not None and not isinstance(judul, str):
                return None, "The title must be text."
            nilai["title"] = (judul or "").strip()[:MAKS_JUDUL] or None
        if "logo_props" in data:
            try:
                nilai["logo_props"] = rapikan_logo(data.get("logo_props"))
            except LogoTidakValid as e:
                return None, str(e)

        cakupan = data.get("cakupan", link.cakupan if link else CAKUPAN_QUICK_LINK_SEMUA)
        if cakupan not in _CAKUPAN:
            return None, "Choose who sees this link."
        nilai["cakupan"] = cakupan

        if cakupan == CAKUPAN_QUICK_LINK_SEMUA:
            nilai["departemen_ids"], nilai["divisi_ids"] = [], []
            return nilai, None

        departemen_ids = _ids(data.get("departemen_ids")) if "departemen_ids" in data else None
        divisi_ids = _ids(data.get("divisi_ids")) if "divisi_ids" in data else None
        if ("departemen_ids" in data and departemen_ids is None) or ("divisi_ids" in data and divisi_ids is None):
            return None, "Invalid divisions or departments."
        if departemen_ids is None:
            departemen_ids = [str(d.id) for d in link.departemen.all()] if link else []
        if divisi_ids is None:
            divisi_ids = [str(v.id) for v in link.divisi.all()] if link else []
        try:
            n_dep = Departemen.objects.filter(workspace_id=workspace_id, id__in=departemen_ids).count()
            n_div = Divisi.objects.filter(workspace_id=workspace_id, id__in=divisi_ids).count()
        except ValidationError:
            return None, "Invalid divisions or departments."
        if n_dep != len(departemen_ids) or n_div != len(divisi_ids):
            return None, "Some divisions or departments do not exist in this workspace."
        if not departemen_ids and not divisi_ids:
            return None, "Pick at least one division or department, or share with everyone."
        nilai["departemen_ids"], nilai["divisi_ids"] = departemen_ids, divisi_ids
        return nilai, None

    def _simpan(self, link, nilai, url_berubah):
        # `logo_props` sudah dirapikan di `_baca`; hanya diteruskan kalau dikirim.
        logo = {"logo_props": nilai["logo_props"]} if "logo_props" in nilai else {}
        link.metadata = metadata_baru(link.metadata, link.url, url_berubah=url_berubah, **logo)
        with transaction.atomic():
            link.save()
            link.departemen.set(nilai["departemen_ids"])
            link.divisi.set(nilai["divisi_ids"])

    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        semua = self._semua(workspace.id)
        isi_metadata_lama(JENIS_BERSAMA, semua)
        departemen_ids, divisi_ids = sasaran_pengguna(request.user.id, workspace.id)
        hasil = {
            "boleh_kelola": boleh_kelola_bersama(request.user, workspace.id),
            "links": [_serial(link) for link in semua if berlaku_untuk(link, departemen_ids, divisi_ids)],
        }
        if hasil["boleh_kelola"]:
            hasil["semua"] = [_serial(link) for link in semua]
            hasil["organisasi"] = _organisasi(workspace.id)
        return Response(hasil)

    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        if not boleh_kelola_bersama(request.user, workspace.id):
            return Response({"error": "Only workspace admins can add shared links."}, status=status.HTTP_403_FORBIDDEN)
        nilai, galat = self._baca(request.data, workspace.id)
        if galat:
            return Response({"error": galat}, status=status.HTTP_400_BAD_REQUEST)
        terakhir = QuickLinkBersama.objects.filter(workspace=workspace).order_by("-sort_order").first()
        link = QuickLinkBersama(
            workspace=workspace,
            url=nilai["url"],
            title=nilai.get("title"),
            cakupan=nilai["cakupan"],
            sort_order=(terakhir.sort_order + 1000) if terakhir else 65535,
        )
        self._simpan(link, nilai, url_berubah=True)
        return Response(_serial(link), status=status.HTTP_201_CREATED)

    def patch(self, request, slug, pk):
        workspace = Workspace.objects.get(slug=slug)
        if not boleh_kelola_bersama(request.user, workspace.id):
            return Response(
                {"error": "Only workspace admins can change shared links."}, status=status.HTTP_403_FORBIDDEN
            )
        link = (
            QuickLinkBersama.objects.filter(workspace=workspace, pk=pk).prefetch_related("departemen", "divisi").first()
        )
        if link is None:
            return Response({"error": "Shared link not found."}, status=status.HTTP_404_NOT_FOUND)
        nilai, galat = self._baca(request.data, workspace.id, link=link)
        if galat:
            return Response({"error": galat}, status=status.HTTP_400_BAD_REQUEST)
        url_berubah = "url" in nilai and nilai["url"] != link.url
        if "url" in nilai:
            link.url = nilai["url"]
        if "title" in nilai:
            link.title = nilai["title"]
        link.cakupan = nilai["cakupan"]
        self._simpan(link, nilai, url_berubah=url_berubah)
        link = QuickLinkBersama.objects.prefetch_related("departemen", "divisi").get(pk=link.pk)
        return Response(_serial(link))

    def delete(self, request, slug, pk):
        workspace = Workspace.objects.get(slug=slug)
        if not boleh_kelola_bersama(request.user, workspace.id):
            return Response(
                {"error": "Only workspace admins can remove shared links."}, status=status.HTTP_403_FORBIDDEN
            )
        link = QuickLinkBersama.objects.filter(workspace=workspace, pk=pk).first()
        if link is None:
            return Response({"error": "Shared link not found."}, status=status.HTTP_404_NOT_FOUND)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
