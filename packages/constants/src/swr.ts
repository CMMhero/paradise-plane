/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export const DEFAULT_SWR_CONFIG = {
  refreshWhenHidden: false,
  revalidateIfStale: false,
  revalidateOnFocus: false,
  revalidateOnMount: true,
  refreshInterval: 600000,
  errorRetryCount: 3,
};

/**
 * Jendela dianggap "terlihat" hanya saat tab tampak DAN jendelanya berfokus.
 * SWR memakai ini untuk menunda `refreshInterval`, jadi polling berhenti saat
 * orang beralih ke aplikasi lain, bukan hanya saat tab tersembunyi.
 */
const isWindowActive = () =>
  typeof document === "undefined" || (document.visibilityState !== "hidden" && document.hasFocus());

export const WEB_SWR_CONFIG = {
  refreshWhenHidden: false,
  isVisible: isWindowActive,
  revalidateIfStale: true,
  // Pindah tab/jendela tidak boleh menarik ulang apa pun. Data hidup lewat sinyal
  // server (`core/lib/data-live.ts`); `revalidateIfStale` tetap menyegarkan data
  // lama saat layar dipasang, yaitu saat orang berpindah halaman, bukan fokus.
  revalidateOnFocus: false,
  revalidateOnMount: true,
  errorRetryCount: 3,
};
