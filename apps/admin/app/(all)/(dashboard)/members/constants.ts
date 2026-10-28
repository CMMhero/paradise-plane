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

/** Nilai `WorkspaceMember.role` di backend (`ROLE_CHOICES`).
 * Label tampil TIDAK dari sini — pakai kamus God Mode
 * (`s.members.role_admin / role_member / role_guest`) supaya mengikuti bahasa aktif. */
export const PERAN: Record<number, string> = { 20: "Admin", 15: "Member", 5: "Guest" };

/** Bahasa UI yang bisa dipilih per akun (nama asli bahasanya, tidak diterjemahkan).
 * Cermin `packages/i18n/src/constants/language.ts` dan `_BAHASA_SAH` di backend. */
export const BAHASA_PROFIL: { value: string; label: string }[] = [
  { value: "en", label: "English" },
  { value: "id", label: "Indonesian" },
  { value: "fr", label: "Français" },
  { value: "es", label: "Español" },
  { value: "ja", label: "日本語" },
  { value: "zh-CN", label: "简体中文" },
  { value: "zh-TW", label: "繁體中文" },
  { value: "ru", label: "Русский" },
  { value: "it", label: "Italian" },
  { value: "cs", label: "Čeština" },
  { value: "sk", label: "Slovenčina" },
  { value: "de", label: "Deutsch" },
  { value: "ua", label: "Українська" },
  { value: "pl", label: "Polski" },
  { value: "ko", label: "한국어" },
  { value: "pt-BR", label: "Português Brasil" },
  { value: "ro", label: "Română" },
  { value: "vi-VN", label: "Tiếng việt" },
  { value: "tr-TR", label: "Türkçe" },
];

/** Dipakai kalau akun belum jadi anggota workspace (`workspace_role: null`). */
export const PERAN_DEFAULT = 15;
