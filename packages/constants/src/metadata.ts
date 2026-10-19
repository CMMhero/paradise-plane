/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: debranding metadata
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Nama pendek aplikasi. Dipakai `apple-mobile-web-app-title` di apps/web,
// yaitu label yang muncul di bawah ikon kalau karyawan menekan "Add to Home
// Screen" di iPhone. Default upstream memakai kalimat pemasaran Plane yang
// panjang, dan iOS memotongnya jadi potongan tak terbaca. Nama pendek menang di
// sini, bukan kalimat.
export const SITE_NAME = "Paradise Task Tracker";

// Dipakai meta `description` di apps/web. Ditulis untuk pemakaian internal,
// bukan untuk mesin pencari: instance ini tidak diindeks siapa pun.
export const SITE_DESCRIPTION = "Manajemen proyek & issue internal PT Paradise Perkasa.";

// DIBUANG dari berkas ini, `SITE_TITLE`, `SITE_KEYWORDS`, `SITE_URL`,
// `TWITTER_USER_NAME`, dan lima konstanta `SPACE_SITE_*`. Semuanya berisi merek
// dan domain vendor (`plane.so`, `@planepowers`, "Plane Publish"), dan setelah
// diperiksa ke seluruh `apps/` + `packages/` **tidak ada satu pun pemakainya**.
// Mendebranding kode mati hanya menyisakan kalimat yang harus dirawat tanpa
// pernah tampil; menghapusnya sekalian menutup jalan agar tidak terpakai lagi
// tanpa sengaja.
