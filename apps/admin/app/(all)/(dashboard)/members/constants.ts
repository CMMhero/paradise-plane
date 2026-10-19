/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kelola member di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* Konstanta sengaja dipisah dari berkas komponen: satu berkas yang mengekspor
   komponen DAN nilai biasa mematikan Fast Refresh untuk berkas itu, setiap
   sunting jadi reload halaman penuh, bukan hot swap. */

export const inputClass =
  "rounded border border-subtle bg-layer-1 px-2 py-1.5 text-body-sm-regular text-primary outline-none focus:border-accent-primary";

/** Nilai `WorkspaceMember.role` di backend (`ROLE_CHOICES`). */
export const PERAN: Record<number, string> = { 20: "Admin", 15: "Member", 5: "Guest" };

/** Dipakai kalau akun belum jadi anggota workspace (`workspace_role: null`). */
export const PERAN_DEFAULT = 15;
