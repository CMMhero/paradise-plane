# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: topik aturan God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Topik (grup) yang dipakai layar God Mode > Work rules > All rules untuk
mengelompokkan aturan. Urutan di sini = urutan di layar.

Sengaja sudah lengkap untuk ketujuh area inventaris (A-G), supaya agen area tidak
perlu menyunting berkas bersama ini. Topik baru hanya kalau benar-benar tak ada
yang cocok, dan itu satu baris di sini (konflik merge-nya sepele).
"""

GRUP = {
    "visibility": ("What each level sees", "Menus, pages, and data that each level can see."),
    "assignment": ("Assigning and editing", "Who may assign, edit, comment on, and reopen work items."),
    "approvals": ("Approvals", "Who approves finished work and when approval is needed."),
    "projects": ("Departments and projects", "Who may create departments and what new ones start with."),
    "dates": ("Dates and lateness", "When a work item counts as late and how dates fill themselves in."),
    "display": ("Display defaults", "What new accounts see first. Each person can still change their own."),
    "notifications": ("Notifications and digests", "Who gets which email, report, and reminder."),
    "chat": ("Chat", "Limits and rights inside chat."),
    "wiki": ("Wiki and quick links", "Who may read, upload, and manage Wiki files and shared links."),
    "files": ("Files and invites", "Uploads, exports, and invitations."),
    "security": ("Sign-in and security", "Passwords, sign-in limits, and sessions."),
}
