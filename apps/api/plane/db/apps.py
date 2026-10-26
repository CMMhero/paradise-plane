# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.apps import AppConfig


class DbConfig(AppConfig):
    name = "plane.db"

    def ready(self):
        # Daftarkan model sensitif ke jejak audit setelah semua app dimuat.
        from plane.db.audit import register_audit_models

        register_audit_models()

        # Super Admin tersembunyi: impor modulnya mendaftarkan signal
        # yang memberi akses ke setiap project baru secara otomatis.
        from plane.db import superadmin  # noqa: F401

        # Direktur otomatis anggota semua divisi: user bilang
        # "by default, direktur can view all division in projects". Tanpa ini,
        # KEP-02 (project private) membuat direktur terkunci dari divisinya
        # sendiri, dan gerbang hierarki menolaknya sebagai "bukan anggota".
        from plane.db import direktur as _direktur_signal  # noqa: F401

        # Jangkauan hierarki (KEP-29): penempatan divisi/departemen menjadi
        # keanggotaan project otomatis, dan dicabut saat penempatannya berubah.
        from plane.db import jangkauan as _jangkauan_signal  # noqa: F401

        # Anggota workspace baru otomatis anggota Wiki (keputusan user 2026-10-26).
        from plane.db import wiki_default as _wiki_default_signal  # noqa: F401
