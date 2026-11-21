/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: God Mode rule registry (All rules screen)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
import type { TRulesReset, TRulesResponse, TRulesUpdate } from "@plane/types";
// api service
import { APIService } from "../api.service";

/**
 * Typed access to `/api/instances/rules/`: every rule of the registry plus the
 * older settings, listed read-only. Errors are thrown as the response body:
 * `{ errors: { KEY: message } }` for invalid values or
 * `{ error: "confirm_required", keys }` when a high-risk rule changed without the phrase.
 */
export class InstanceRulesService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(): Promise<TRulesResponse> {
    return this.get("/api/instances/rules/")
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  /** All-or-nothing: any invalid value rejects the whole request. Returns the fresh list. */
  async update(payload: TRulesUpdate): Promise<TRulesResponse> {
    return this.patch("/api/instances/rules/", payload)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  /** Puts the given rules back to their defaults. Returns the fresh list. */
  async reset(payload: TRulesReset): Promise<TRulesResponse> {
    return this.post("/api/instances/rules/reset/", payload)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }
}
