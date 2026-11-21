# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area E, obrolan, wiki, quick link
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area E inventaris: obrolan, wiki, dan quick link."""

from plane.utils.aturan.jenis import INT, RENDAH, Rule

# Batas pesan tersemat per ruang (dulu `BATAS_SEMATAN = 20` di app/views/chat.py).
# Bilah sematan berguna selama isinya bisa dipindai sekilas.
CHAT_PINS_MAX = "CHAT_PINS_MAX"

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
)
