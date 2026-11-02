# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

# Module imports
from .base import BaseModel


class Notification(BaseModel):
    workspace = models.ForeignKey("db.Workspace", related_name="notifications", on_delete=models.CASCADE)
    project = models.ForeignKey("db.Project", related_name="notifications", on_delete=models.CASCADE, null=True)
    data = models.JSONField(null=True)
    entity_identifier = models.UUIDField(null=True)
    entity_name = models.CharField(max_length=255)
    title = models.TextField()
    message = models.JSONField(null=True)
    message_html = models.TextField(blank=True, default="<p></p>")
    message_stripped = models.TextField(blank=True, null=True)
    sender = models.CharField(max_length=255)
    triggered_by = models.ForeignKey(
        "db.User",
        related_name="triggered_notifications",
        on_delete=models.SET_NULL,
        null=True,
    )
    receiver = models.ForeignKey("db.User", related_name="received_notifications", on_delete=models.CASCADE)
    read_at = models.DateTimeField(null=True)
    snoozed_till = models.DateTimeField(null=True)
    archived_at = models.DateTimeField(null=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        db_table = "notifications"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["entity_identifier"], name="notif_entity_identifier_idx"),
            models.Index(fields=["entity_name"], name="notif_entity_name_idx"),
            models.Index(fields=["read_at"], name="notif_read_at_idx"),
            models.Index(fields=["receiver", "read_at"], name="notif_entity_idx"),
            models.Index(
                fields=["receiver", "workspace", "read_at", "created_at"],
                name="notif_receiver_status_idx",
            ),
            models.Index(
                fields=["receiver", "workspace", "entity_name", "read_at"],
                name="notif_receiver_entity_idx",
            ),
            models.Index(
                fields=["receiver", "workspace", "snoozed_till", "archived_at"],
                name="notif_receiver_state_idx",
            ),
            models.Index(
                fields=["receiver", "workspace", "sender"],
                name="notif_receiver_sender_idx",
            ),
            models.Index(
                fields=["workspace", "entity_identifier", "entity_name"],
                name="notif_entity_lookup_idx",
            ),
        ]

    def __str__(self):
        """Return name of the notifications"""
        return f"{self.receiver.email} <{self.workspace.name}>"


def get_default_preference():
    return {
        "property_change": {"email": True},
        "state": {"email": True},
        "comment": {"email": True},
        "mentions": {"email": True},
        "approval": {"email": True},
    }


class UserNotificationPreference(BaseModel):
    # user it is related to
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    # workspace if it is applicable
    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="workspace_notification_preferences",
        null=True,
    )
    # project
    project = models.ForeignKey(
        "db.Project",
        on_delete=models.CASCADE,
        related_name="project_notification_preferences",
        null=True,
    )

    # preference fields
    # Bawaan: email MATI kecuali yang penting (disetujui = approval, selesai =
    # issue_completed). Orang menyalakan sisanya sendiri di Profil -> Notifikasi.
    property_change = models.BooleanField(default=False)
    state_change = models.BooleanField(default=False)
    comment = models.BooleanField(default=False)
    mention = models.BooleanField(default=False)
    issue_completed = models.BooleanField(default=True)
    # Kustomisasi Paradise: persetujuan penugasan (diajukan/diputuskan).
    # Saklar ini mengatur EMAIL-nya; inbox diatur `inbox_approval`.
    approval = models.BooleanField(default=True)
    # Kustomisasi Paradise: ringkasan tugas harian lewat email (hari ini, 7 hari
    # ke depan, terlambat). MATI secara bawaan; orang menyalakannya sendiri dari
    # Profil -> Notifikasi (keputusan user 2026-10-26).
    daily_digest = models.BooleanField(default=False)
    # Kustomisasi Paradise: edisi sore ringkasan harian, 17.30 WIB (keputusan user
    # 2026-11-02). Yang selesai hari ini + yang tenggatnya hari kerja berikutnya.
    daily_digest_sore = models.BooleanField(default=False)
    # Kustomisasi Paradise: pengingat tenggat H-7..H+7 (deadline_reminder_task).
    deadline_reminder = models.BooleanField(default=False)
    # Kustomisasi Paradise: email "tugas baru untuk Anda" saat seseorang
    # ditambahkan sebagai penanggung jawab (penugasan_email.py).
    assigned = models.BooleanField(default=True)
    # Kustomisasi Paradise: email pesan obrolan yang belum dibaca (chat_notification_task).
    chat = models.BooleanField(default=True)
    # Kustomisasi Paradise: saklar INBOX per jenis kabar (keputusan user 2026-11-02).
    # Hidup semua = perilaku lama (inbox selalu ditulis).
    inbox_assigned = models.BooleanField(default=True)
    inbox_mention = models.BooleanField(default=True)
    inbox_comment = models.BooleanField(default=True)
    inbox_approval = models.BooleanField(default=True)
    inbox_deadline = models.BooleanField(default=True)
    inbox_issue_completed = models.BooleanField(default=True)
    inbox_state_change = models.BooleanField(default=True)
    inbox_property_change = models.BooleanField(default=True)
    inbox_chat = models.BooleanField(default=True)
    # Kustomisasi Paradise: bagian yang dimuat ringkasan harian (daily_digest_email).
    digest_terlambat = models.BooleanField(default=True)
    digest_hari_ini = models.BooleanField(default=True)
    digest_depan = models.BooleanField(default=True)
    digest_diberikan = models.BooleanField(default=True)
    digest_tim = models.BooleanField(default=True)
    # Hidup = saklar di atas DIABAIKAN; yang berlaku bawaan menurut jabatan,
    # dihitung saat dibaca (plane/utils/preferensi_email.py). Mati begitu orangnya
    # mengubah satu saklar (keputusan user 2026-10-30).
    ikut_bawaan_jabatan = models.BooleanField(default=True)
    # Tabel bawaan jabatan ({"staf": {...}, "pimpinan": {...}}) yang dipotret dari
    # God Mode saat baris lahir. Mengubah bawaan di God Mode hanya mengenai akun
    # baru; orang lama tetap ikut jabatannya, tapi dengan tabel miliknya sendiri.
    bawaan_email = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "UserNotificationPreference"
        verbose_name_plural = "UserNotificationPreferences"
        db_table = "user_notification_preferences"
        ordering = ("-created_at",)

    def __str__(self):
        """Return the user"""
        return f"<{self.user}>"


@receiver(pre_save, sender=UserNotificationPreference)
def potret_bawaan_email(sender, instance, **kwargs):
    # Kustomisasi Paradise: semua jalur pembuatan (signal user, get_or_create di
    # view) lewat sini, jadi tak ada baris yang lahir tanpa tabelnya sendiri.
    if instance._state.adding and instance.bawaan_email is None:
        from plane.utils.bawaan_member import baca_bawaan

        instance.bawaan_email = baca_bawaan()["email"]


class EmailNotificationLog(BaseModel):
    # receiver
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_notifications",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="triggered_emails",
    )
    # entity - can be issues, pages, etc.
    entity_identifier = models.UUIDField(null=True)
    entity_name = models.CharField(max_length=255)
    # data
    data = models.JSONField(null=True)
    # sent at
    processed_at = models.DateTimeField(null=True)
    sent_at = models.DateTimeField(null=True)
    entity = models.CharField(max_length=200)
    old_value = models.CharField(max_length=300, blank=True, null=True)
    new_value = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        verbose_name = "Email Notification Log"
        verbose_name_plural = "Email Notification Logs"
        db_table = "email_notification_logs"
        ordering = ("-created_at",)
