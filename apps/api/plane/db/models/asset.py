# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from uuid import uuid4

# Django import
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

# Module import
from plane.utils.path_validator import sanitize_filename

from .base import BaseModel


def get_upload_path(instance, filename):
    filename = sanitize_filename(filename) or uuid4().hex
    if instance.workspace_id is not None:
        return f"{instance.workspace.id}/{uuid4().hex}-{filename}"
    return f"user-{uuid4().hex}-{filename}"


def file_size(value):
    if value.size > settings.FILE_SIZE_LIMIT:
        raise ValidationError("File too large. Size should not exceed 5 MB.")


class FileAsset(BaseModel):
    """
    A file asset.
    """

    class EntityTypeContext(models.TextChoices):
        ISSUE_ATTACHMENT = "ISSUE_ATTACHMENT"
        ISSUE_DESCRIPTION = "ISSUE_DESCRIPTION"
        COMMENT_DESCRIPTION = "COMMENT_DESCRIPTION"
        PAGE_DESCRIPTION = "PAGE_DESCRIPTION"
        USER_COVER = "USER_COVER"
        USER_AVATAR = "USER_AVATAR"
        WORKSPACE_LOGO = "WORKSPACE_LOGO"
        PROJECT_COVER = "PROJECT_COVER"
        DRAFT_ISSUE_ATTACHMENT = "DRAFT_ISSUE_ATTACHMENT"
        DRAFT_ISSUE_DESCRIPTION = "DRAFT_ISSUE_DESCRIPTION"
        # Kustomisasi Paradise: lampiran pesan Obrolan.
        # Tidak perlu migrasi: `entity_type` CharField biasa tanpa choices, dan
        # pasangan (entity_type, entity_identifier) sudah ter-indeks.
        CHAT_ATTACHMENT = "CHAT_ATTACHMENT"
        # Materi Wiki: SATU berkas yang berdiri sendiri di dalam sebuah Topik.
        #
        # Bedanya dengan PAGE_DESCRIPTION penting dan bukan soal rapi-rapian.
        # PAGE_DESCRIPTION adalah berkas yang TERTANAM di badan sebuah dokumen:
        # nama, ukuran, dan tipenya hidup di dalam binary Yjs, jadi tidak bisa
        # ditanyakan lewat query, dan untuk menaruhnya orang harus membuat
        # halaman dulu lalu mengetik di editor. WIKI_MATERIAL adalah berkasnya
        # SENDIRI yang jadi warga kelas satu: `page` menunjuk Topik tempat ia
        # berada, `attributes` menyimpan nama dan judulnya, `size` dan
        # `created_by` sudah kolom sungguhan. Jadi kartu bisa menyebut
        # "PDF, 4,2 MB, diunggah Budi" tanpa membuka apa pun, dan mengunggah
        # materi cukup satu langkah: pilih berkas.
        WIKI_MATERIAL = "WIKI_MATERIAL"
        # Hasil konversi otomatis sebuah WIKI_MATERIAL ke PDF, supaya berkas
        # Office bisa dibaca di peramban. Turunan, bukan unggahan orang: ia
        # tidak pernah muncul sebagai materi tersendiri.
        WIKI_MATERIAL_PREVIEW = "WIKI_MATERIAL_PREVIEW"

    attributes = models.JSONField(default=dict)
    asset = models.FileField(upload_to=get_upload_path, max_length=800)
    user = models.ForeignKey("db.User", on_delete=models.CASCADE, null=True, related_name="assets")
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, null=True, related_name="assets")
    draft_issue = models.ForeignKey("db.DraftIssue", on_delete=models.CASCADE, null=True, related_name="assets")
    project = models.ForeignKey("db.Project", on_delete=models.CASCADE, null=True, related_name="assets")
    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, null=True, related_name="assets")
    comment = models.ForeignKey("db.IssueComment", on_delete=models.CASCADE, null=True, related_name="assets")
    page = models.ForeignKey("db.Page", on_delete=models.CASCADE, null=True, related_name="assets")
    entity_type = models.CharField(max_length=255, null=True, blank=True)
    entity_identifier = models.CharField(max_length=255, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    external_source = models.CharField(max_length=255, null=True, blank=True)
    size = models.FloatField(default=0)
    is_uploaded = models.BooleanField(default=False)
    storage_metadata = models.JSONField(default=dict, null=True, blank=True)

    class Meta:
        verbose_name = "File Asset"
        verbose_name_plural = "File Assets"
        db_table = "file_assets"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["entity_type"], name="asset_entity_type_idx"),
            models.Index(fields=["entity_identifier"], name="asset_entity_identifier_idx"),
            models.Index(fields=["entity_type", "entity_identifier"], name="asset_entity_idx"),
            models.Index(fields=["asset"], name="asset_asset_idx"),
        ]

    def __str__(self):
        return str(self.asset)

    @property
    def asset_url(self):
        if (
            self.entity_type == self.EntityTypeContext.WORKSPACE_LOGO
            or self.entity_type == self.EntityTypeContext.USER_AVATAR
            or self.entity_type == self.EntityTypeContext.USER_COVER
            or self.entity_type == self.EntityTypeContext.PROJECT_COVER
        ):
            return f"/api/assets/v2/static/{self.id}/"

        if self.entity_type == self.EntityTypeContext.ISSUE_ATTACHMENT:
            return f"/api/assets/v2/workspaces/{self.workspace.slug}/projects/{self.project_id}/issues/{self.issue_id}/attachments/{self.id}/"  # noqa: E501

        if self.entity_type in [
            self.EntityTypeContext.ISSUE_DESCRIPTION,
            self.EntityTypeContext.COMMENT_DESCRIPTION,
            self.EntityTypeContext.PAGE_DESCRIPTION,
            self.EntityTypeContext.DRAFT_ISSUE_DESCRIPTION,
            self.EntityTypeContext.WIKI_MATERIAL,
            self.EntityTypeContext.WIKI_MATERIAL_PREVIEW,
        ]:
            return f"/api/assets/v2/workspaces/{self.workspace.slug}/projects/{self.project_id}/{self.id}/"

        return None
