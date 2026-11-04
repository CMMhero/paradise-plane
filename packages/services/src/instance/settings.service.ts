/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: settings registry of God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
import type {
  TInstanceSetting,
  TInstanceSettingKind,
  TInstanceSettingsResponse,
  TInstanceSettingsUpdate,
} from "@plane/types";
// api service
import { APIService } from "../api.service";

type TRawSetting = Partial<Record<keyof TInstanceSetting, unknown>> & { key: string; kind: TInstanceSettingKind };

const asText = (v: unknown): string => (v === null || v === undefined ? "" : String(v));
const asNumberOrNull = (v: unknown): number | null => (v === null || v === undefined || v === "" ? null : Number(v));

/** The server may send numbers for number kinds; the UI works with strings only. */
const normalize = (raw: TRawSetting): TInstanceSetting => ({
  key: raw.key,
  kind: raw.kind,
  default: asText(raw.default),
  value: asText(raw.value),
  min: asNumberOrNull(raw.min),
  max: asNumberOrNull(raw.max),
  choices: Array.isArray(raw.choices) ? (raw.choices as unknown[]).map(Number) : null,
  sensitive: Boolean(raw.sensitive),
});

const normalizeResponse = (data: { settings?: TRawSetting[] } | undefined): TInstanceSettingsResponse => ({
  settings: (data?.settings ?? []).map(normalize),
});

/**
 * Typed access to `/api/instances/settings/`, the single registry of Paradise
 * instance settings (defaults, ranges, choices, sensitivity). Errors are thrown
 * as the response body: `{ errors: { KEY: message } }` for invalid values or
 * `{ error: "confirm_required" }` when a sensitive key changed without the phrase.
 */
export class InstanceSettingsService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(): Promise<TInstanceSettingsResponse> {
    return this.get("/api/instances/settings/")
      .then((r) => normalizeResponse(r?.data))
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  /** All-or-nothing: any invalid value rejects the whole request. Returns the fresh registry. */
  async update(payload: TInstanceSettingsUpdate): Promise<TInstanceSettingsResponse> {
    return this.patch("/api/instances/settings/", payload)
      .then((r) => normalizeResponse(r?.data))
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }
}
