# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area E, obrolan, wiki, quick link
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area E inventaris: obrolan, wiki, dan quick link.

Aturan "siapa boleh" memakai SATU kosakata pilihan bernama, bukan matriks per
jenjang. Admin workspace dan Super Admin selalu lolos, kecuali pilihannya
`nobody`; pembacanya `plane.utils.jenjang_aturan.lolos_jenjang`.
"""

from plane.utils.aturan.jenis import BOOL, CHOICE, INT, NEXT_RUN, RENDAH, SEDANG, TINGGI, Rule

# Pilihan "siapa boleh", dari yang paling longgar ke yang paling ketat.
SEMUA = "members"
SUPERVISOR = "supervisor"
MANAGER = "manager"
DIREKTUR = "director"
ADMIN = "admins"
TIDAK_ADA = "nobody"

_L_SEMUA = (SEMUA, "Any member")
_L_SUPERVISOR = (SUPERVISOR, "Supervisors and above")
_L_MANAGER = (MANAGER, "Managers and above")
_L_DIREKTUR = (DIREKTUR, "Directors and secretaries")
_L_ADMIN = (ADMIN, "Workspace admins only")

# Batas pesan tersemat per ruang (dulu `BATAS_SEMATAN = 20` di app/views/chat.py).
# Bilah sematan berguna selama isinya bisa dipindai sekilas.
CHAT_PINS_MAX = "CHAT_PINS_MAX"
# E1: siapa selain admin dan daftar penulis kanal yang boleh menulis di Announcements.
CHAT_ANNOUNCE_POSTERS = "CHAT_ANNOUNCE_POSTERS"
# E2: siapa yang boleh membuat kanal chat baru.
CHAT_CHANNEL_CREATORS = "CHAT_CHANNEL_CREATORS"
# E4: berapa orang boleh disebut dalam satu pesan, dan siapa yang boleh memakai @all.
CHAT_MENTIONS_MAX = "CHAT_MENTIONS_MAX"
CHAT_ALL_MENTION_WHO = "CHAT_ALL_MENTION_WHO"
# E6: panjang nama kanal. Kolom `Ruang.nama` 80 karakter, jadi hanya bisa diturunkan.
CHAT_CHANNEL_NAME_MAX = "CHAT_CHANNEL_NAME_MAX"
# E7: siapa yang boleh memulai panggilan.
CHAT_CALLS_WHO = "CHAT_CALLS_WHO"
# E8: Direktur dan Sekretaris ikut kanal cabang, divisi, dan departemen.
CHAT_LEADERS_JOIN_UNIT_CHANNELS = "CHAT_LEADERS_JOIN_UNIT_CHANNELS"
# E10: hak unggah Wiki dan kuasa Direktur atas folder unit.
WIKI_GENERAL_UPLOAD = "WIKI_GENERAL_UPLOAD"
WIKI_UNIT_UPLOAD = "WIKI_UNIT_UPLOAD"
WIKI_DIRECTORS_MANAGE_ALL = "WIKI_DIRECTORS_MANAGE_ALL"
# E11: siapa yang menjadi admin Wiki.
WIKI_ADMIN_WHO = "WIKI_ADMIN_WHO"
# E12, E13: quick link bersama dan pribadi.
QUICK_LINK_SHARED_MANAGERS = "QUICK_LINK_SHARED_MANAGERS"
QUICK_LINK_PERSONAL_MAX = "QUICK_LINK_PERSONAL_MAX"

# Pilihan "wiki admin": bawaannya admin workspace ikut.
WIKI_ADMIN_WORKSPACE = "workspace_admins"
WIKI_ADMIN_SUPER = "super_admin"
# Pilihan hak unggah folder unit.
UNGGAH_ANGGOTA_UNIT = "unit_members"
UNGGAH_PENGELOLA = "managers"

ATURAN = (
    Rule(
        key=CHAT_PINS_MAX,
        kind=INT,
        default=20,
        min=1,
        max=100,
        group="chat",
        label="Pinned messages per conversation",
        help=(
            "How many messages a channel or direct message can pin at once. At the limit, someone has to unpin "
            "a message before pinning another. Lowering it shows only the newest pins."
        ),
        risk=RENDAH,
    ),
    Rule(
        key=CHAT_ANNOUNCE_POSTERS,
        kind=CHOICE,
        default=ADMIN,
        choices=(
            (ADMIN, "Workspace admins only"),
            _L_SUPERVISOR,
            _L_MANAGER,
            _L_DIREKTUR,
        ),
        group="chat",
        label="Who can post in Announcements",
        help=(
            "Workspace admins, Super Admins, and the people or departments on the channel's writer list can always "
            "post. This adds everyone at the chosen level or above. Pins in Announcements follow the same people. "
            "Changelog stays system-only."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=CHAT_CHANNEL_CREATORS,
        kind=CHOICE,
        default=SEMUA,
        choices=(_L_SEMUA, _L_SUPERVISOR, _L_MANAGER, _L_DIREKTUR, _L_ADMIN),
        group="chat",
        label="Who can create channels",
        help=(
            "Who may start a new public or private channel. Workspace admins can always create one. Existing "
            "channels, and who can join them, do not change."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=CHAT_MENTIONS_MAX,
        kind=INT,
        default=20,
        min=1,
        max=100,
        group="chat",
        label="People you can mention in one message",
        help=(
            "Mentions past the limit are ignored, and the message still sends. Past mentions on old messages "
            "stay as they are."
        ),
        risk=RENDAH,
    ),
    Rule(
        key=CHAT_ALL_MENTION_WHO,
        kind=CHOICE,
        default=SEMUA,
        choices=(_L_SEMUA, _L_SUPERVISOR, _L_MANAGER, _L_DIREKTUR, _L_ADMIN),
        group="chat",
        label="Who can use @all in a channel",
        help=(
            "@all notifies every member of the channel. A message that uses it from someone below this level is "
            "refused. Direct messages are not affected."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=CHAT_CHANNEL_NAME_MAX,
        kind=INT,
        default=80,
        min=20,
        max=80,
        web=True,
        group="chat",
        label="Longest channel name",
        help=(
            "Characters allowed in a channel name when it is created or renamed. It cannot go above 80. "
            "Existing longer names stay until someone renames them."
        ),
        risk=RENDAH,
    ),
    Rule(
        key=CHAT_CALLS_WHO,
        kind=CHOICE,
        default=SEMUA,
        choices=(_L_SEMUA, _L_SUPERVISOR, _L_MANAGER, _L_DIREKTUR, _L_ADMIN, (TIDAK_ADA, "Nobody (calls off)")),
        group="chat",
        label="Who can start calls",
        help=(
            "Anyone who can read a conversation can join a call that someone allowed has started. Workspace "
            "admins can always start one. Choosing Nobody turns calls off for everyone, admins included."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=CHAT_LEADERS_JOIN_UNIT_CHANNELS,
        kind=BOOL,
        default=False,
        group="chat",
        label="Add Directors and Secretaries to every unit channel",
        help=(
            "When on, Directors and Secretaries are added to every branch, division, and department channel and "
            "can read them. Everyone else keeps following the organization chart. It takes effect the next time "
            "the chart is synced, which happens on any placement change."
        ),
        risk=TINGGI,
        applies=NEXT_RUN,
    ),
    Rule(
        key=WIKI_GENERAL_UPLOAD,
        kind=CHOICE,
        default=SEMUA,
        choices=((SEMUA, "Any member"), (ADMIN, "Wiki admins only")),
        group="wiki",
        label="Who can upload to the General folder",
        help=(
            "Members here means workspace members, guests excluded. Folders with a restricted editor list keep "
            "their own rule. Reading does not change."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=WIKI_UNIT_UPLOAD,
        kind=CHOICE,
        default=UNGGAH_ANGGOTA_UNIT,
        choices=(
            (UNGGAH_ANGGOTA_UNIT, "People placed in the unit, plus its managers"),
            (UNGGAH_PENGELOLA, "Folder managers and Wiki admins only"),
        ),
        group="wiki",
        label="Who can upload to division and department folders",
        help=(
            "Managers of a division, supervisors of a department, Directors, and Wiki admins can always upload "
            "to the folders they manage. This decides whether the other people placed in the unit can too. "
            "Reading does not change."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=WIKI_DIRECTORS_MANAGE_ALL,
        kind=BOOL,
        default=True,
        group="wiki",
        label="Directors and Secretaries manage every unit folder",
        help=(
            "When on, they can add subfolders, edit, archive, and delete in every division and department folder, "
            "and edit anyone's material there. When off, they only manage what their own placement covers. "
            "Private project pages are not affected."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=WIKI_ADMIN_WHO,
        kind=CHOICE,
        default=WIKI_ADMIN_WORKSPACE,
        choices=((WIKI_ADMIN_WORKSPACE, "Workspace admins and Super Admins"), (WIKI_ADMIN_SUPER, "Super Admins only")),
        group="wiki",
        label="Who counts as a Wiki admin",
        help=(
            "Wiki admins manage top-level folders and every other folder, and edit any material. The Wiki "
            "project admin role never counts. Choosing Super Admins only takes this away from workspace admins."
        ),
        risk=TINGGI,
        kep="KEP-51",
    ),
    Rule(
        key=QUICK_LINK_SHARED_MANAGERS,
        kind=CHOICE,
        default=ADMIN,
        choices=((ADMIN, "Workspace admins only"), _L_SUPERVISOR, _L_MANAGER, _L_DIREKTUR),
        group="wiki",
        label="Who can manage shared quick links",
        help=(
            "Shared quick links appear for everyone, or for the divisions and departments they target. Workspace "
            "admins can always add, change, and remove them. Personal quick links are not affected."
        ),
        risk=TINGGI,
        kep="KEP-82",
    ),
    Rule(
        key=QUICK_LINK_PERSONAL_MAX,
        kind=INT,
        default=0,
        min=0,
        max=500,
        group="wiki",
        label="Personal quick links per person",
        help=(
            "0 means no limit. At the limit, a person has to remove a link before adding another. Links they "
            "already have stay."
        ),
        risk=SEDANG,
    ),
)
