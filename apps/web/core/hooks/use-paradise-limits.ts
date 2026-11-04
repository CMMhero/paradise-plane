/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TParadiseLimits } from "@plane/types";
// hooks
import { useInstance } from "@/hooks/store/use-instance";

/**
 * Batas yang diatur Super Admin di God Mode, dibaca dari `config.paradise_limits`
 * (GET /api/instances/). Server lama tanpa blok ini: semua nilai jatuh ke bawaan di bawah.
 */
export type { TParadiseLimits };

export const DEFAULT_CHAT_ATTACHMENTS_MAX = 5;
export const DEFAULT_CHAT_MESSAGE_MAX_LENGTH = 5000;

export const useParadiseLimits = (): TParadiseLimits => {
  const { config } = useInstance();
  return config?.paradise_limits ?? {};
};
