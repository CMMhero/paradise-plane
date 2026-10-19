/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Nomaden: bidang kendali SaaS
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
// api service
import { APIService } from "../api.service";

export type TCompanyStatus = "TRIAL" | "ACTIVE" | "PAST_DUE" | "SUSPENDED" | "CHURNED";

export type TTier = "FREE" | "PRO" | "EXPERT" | "ENTERPRISE";

export type TInstanceUsage = {
  taken_at: string;
  workspaces: number;
  members: number;
  storage_bytes: number;
};

export type TTenantInstance = {
  subdomain: string;
  is_active: boolean;
  version: string;
  /** null berarti instance ini BELUM PERNAH berdenyut sama sekali. */
  last_seen_at: string | null;
  /** null berarti sudah berdenyut tapi belum pernah melaporkan pemakaian. */
  usage: TInstanceUsage | null;
};

export type TCompany = {
  slug: string;
  name: string;
  contact_email: string;
  status: TCompanyStatus;
  tier: TTier;
  subscribed_since: string | null;
  instances: TTenantInstance[];
};

export type TInvoiceStatus = "PENDING" | "PAID" | "EXPIRED" | "VOID";

export type TInvoice = {
  external_id: string;
  tier: string;
  amount: number;
  currency: string;
  status: TInvoiceStatus;
  invoice_url: string;
  period_start: string;
  period_end: string;
  due_at: string;
  paid_at: string | null;
};

/**
 * Bidang kendali SaaS. HANYA ada di deployment pemilik produk, dan hanya bisa
 * disentuh instance admin.
 *
 * Di deployment mana pun yang `ENABLE_CONTROL_PLANE` tidak menyala, rutenya
 * bahkan tidak terdaftar sehingga tiap panggilan di sini menjawab 404. Itu
 * disengaja, dan halaman yang memakainya harus menanganinya sebagai "fitur ini
 * tidak ada di sini", bukan sebagai galat.
 */
export class ControlPlaneService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /**
   * Seluruh pelanggan dalam SATU permintaan, sudah membawa tingkatan, jejak
   * hidup, dan pemakaian terakhir. Sengaja bukan tiga panggilan terpisah:
   * sepuluh pelanggan akan berarti tiga puluh permintaan.
   */
  async companies(): Promise<{ companies: TCompany[] }> {
    return this.get("/control/companies/")
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  async updateCompany(slug: string, payload: { status?: TCompanyStatus; tier?: TTier }) {
    return this.patch(`/control/companies/${slug}/`, payload)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  async invoices(slug: string): Promise<{ invoices: TInvoice[] }> {
    return this.get(`/control/companies/${slug}/invoices/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  async createInvoice(slug: string, tier?: TTier) {
    return this.post(`/control/companies/${slug}/invoices/`, tier ? { tier } : {})
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }
}
