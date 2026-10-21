/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Tautan mailto:support@plane.so dibuang, dukungan vendor tidak melayani
// instalasi ini. Pesannya juga diarahkan ke orang yang benar-benar bisa
// menolong: tim IT internal yang memegang servernya.
export function MaintenanceMessage() {
  return (
    <div className="flex flex-col gap-2.5">
      <h1 className="text-left text-18 font-semibold text-primary">&#x1F6A7; Sebagian layanan gagal dijalankan</h1>
      <span className="text-left text-14 font-medium text-secondary">
        Periksa log container untuk menemukan layanan mana yang gagal. Kalau butuh bantuan, hubungi tim IT internal yang
        mengelola server Paradise Task Tracker.
      </span>
    </div>
  );
}
