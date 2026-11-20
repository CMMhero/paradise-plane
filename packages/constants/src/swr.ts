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

export const WEB_SWR_CONFIG = {
  refreshWhenHidden: false,
  revalidateIfStale: true,
  // Pindah tab/jendela tidak boleh menarik ulang apa pun. Data hidup lewat sinyal
  // server (`core/lib/data-live.ts`); `revalidateIfStale` tetap menyegarkan data
  // lama saat layar dipasang, yaitu saat orang berpindah halaman, bukan fokus.
  revalidateOnFocus: false,
  revalidateOnMount: true,
  errorRetryCount: 3,
};
