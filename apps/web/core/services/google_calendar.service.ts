/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sambungan Google Calendar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TGoogleCalendarStatus = {
  /** false kalau instance ini belum diberi kredensial OAuth di God Mode. */
  tersedia: boolean;
  tersambung: boolean;
  terakhir_sinkron: string | null;
  galat_terakhir: string;
};

export class GoogleCalendarService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async status(): Promise<TGoogleCalendarStatus> {
    return this.get("/api/google-calendar/")
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Membalas URL persetujuan Google, bukan mengalihkan sendiri.
   *
   * Alihan dari dalam permintaan XHR tidak memindahkan peramban ke mana pun;
   * ia hanya diikuti oleh fetch dan hasilnya dibuang. Jadi pemanggilnya yang
   * harus menyetel `window.location.href`.
   */
  async urlSambung(): Promise<string> {
    return this.get("/api/google-calendar/connect/")
      .then((response) => response?.data?.url)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async putus(): Promise<void> {
    return this.delete("/api/google-calendar/")
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
