/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// `createInstance` diimpor bernama, bukan lewat default `i18n`. i18next
// mengekspor keduanya, dan memanggilnya sebagai anggota default membuat
// bundler kehilangan jejak ekspor bernamanya.
import { createInstance } from "i18next";
import { initReactI18next } from "react-i18next";
import ICU from "i18next-icu";
import resourcesToBackend from "i18next-resources-to-backend";
import { SUPPORTED_LANGUAGES, FALLBACK_LANGUAGE, LANGUAGE_STORAGE_KEY } from "../constants/language";
import { NAMESPACES, DEFAULT_NAMESPACE } from "../constants/namespaces";

import type { i18n as I18nInstance } from "i18next";

export const i18nInstance: I18nInstance = createInstance();

i18nInstance
  .use(ICU)
  .use(initReactI18next)
  .use(resourcesToBackend((language: string, namespace: string) => import(`../locales/${language}/${namespace}.json`)));

const bahasaTersimpan = typeof window !== "undefined" ? localStorage.getItem(LANGUAGE_STORAGE_KEY) : null;

// Nilai dari localStorage DIPERIKSA dulu, tidak dipakai mentah. Isinya bisa apa
// saja: sisa versi lama, atau hasil orang menyuntingnya sendiri. i18next memang
// sudah dijaga `supportedLngs`, tapi atribut `lang` di bawah tidak punya jaring
// pengaman seperti itu, jadi pemeriksaannya dikerjakan di sini sekalian.
const initialLng: string =
  bahasaTersimpan && SUPPORTED_LANGUAGES.some((l) => l.value === bahasaTersimpan) ? bahasaTersimpan : FALLBACK_LANGUAGE;

// `<html lang>` disetel DI SINI, bukan hanya saat orang mengganti bahasa.
//
// MASALAHNYA. Dua tempat yang menyetel atribut ini (`setLanguage` dan
// `changeLanguage`) sama-sama hanya jalan saat bahasa DIGANTI. Tidak ada yang
// menyetelnya saat halaman dimuat. Akibatnya orang yang sudah memilih bahasa
// Indonesia tetap mendapat `<html lang="en">` di setiap muat ulang berikutnya,
// karena i18next memang membaca pilihannya dari localStorage, tapi atribut di
// dokumennya tertinggal di nilai statis dari `root.tsx`.
//
// KENAPA PENTING, bukan sekadar rapi: pembaca layar memilih mesin pengucapan
// dari atribut ini. Teks Indonesia yang dibacakan dengan pelafalan Inggris
// nyaris tidak bisa dimengerti. Ini WCAG 3.1.1, tingkat A.
//
// Ditaruh di modul ini, bukan di `root.tsx`, karena di sinilah bahasa awal
// ditentukan. Menyetelnya di tempat lain berarti logika yang sama ditulis dua
// kali dan bisa berbeda diam-diam.
if (typeof window !== "undefined") {
  document.documentElement.lang = initialLng;
}

export const initPromise = i18nInstance
  .init({
    lng: initialLng,
    fallbackLng: FALLBACK_LANGUAGE,
    supportedLngs: SUPPORTED_LANGUAGES.map((l) => l.value),
    ns: NAMESPACES,
    defaultNS: DEFAULT_NAMESPACE,
    // fallbackNS ensures all namespaces are searched for any key, so components
    // don't need to pass NAMESPACES to useTranslation (which triggers re-render cascades).
    fallbackNS: NAMESPACES.filter((ns) => ns !== DEFAULT_NAMESPACE),
    partialBundledLanguages: true,
    keySeparator: ".",
    nsSeparator: false,
    interpolation: { escapeValue: false },
    returnNull: false,
    returnEmptyString: false,
    // Pinned explicitly even though it's the default, i18next-icu intercepts the
    // format pipeline and returns raw objects regardless of this flag, so the runtime
    // guard in useTranslation is what actually prevents React crashes. Documenting
    // intent here so this isn't accidentally flipped.
    returnObjects: false,
    react: { useSuspense: false },
  })
  // Eagerly pre-load all namespaces for the initial language so they're cached
  // before any component renders. This prevents the re-render cascade that occurs
  // when react-i18next triggers concurrent async loads for unloaded namespaces.
  .then(() => i18nInstance.loadNamespaces(NAMESPACES));
