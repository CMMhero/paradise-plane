/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: settings registry hook for God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useMemo } from "react";
import useSWR from "swr";
import { InstanceSettingsService } from "@plane/services";
import type { TInstanceSetting, TInstanceSettingsUpdate } from "@plane/types";

const service = new InstanceSettingsService();

export const INSTANCE_SETTINGS_KEY = "INSTANCE_SETTINGS";

/**
 * Loads the registry once (SWR dedupes across every settings tab) and exposes it
 * by key. `update` writes through the API and replaces the cache with the answer,
 * so every tab sees the saved values without another request.
 */
export function useInstanceSettings() {
  const { data, error, mutate, isLoading } = useSWR(INSTANCE_SETTINGS_KEY, () => service.list(), {
    revalidateOnFocus: false,
  });

  const byKey = useMemo(() => {
    if (!data) return undefined;
    return Object.fromEntries(data.settings.map((setting) => [setting.key, setting])) as Record<
      string,
      TInstanceSetting | undefined
    >;
  }, [data]);

  const update = useCallback(
    async (payload: TInstanceSettingsUpdate) => {
      const fresh = await service.update(payload);
      await mutate(fresh, { revalidate: false });
      return fresh;
    },
    [mutate]
  );

  return { settings: byKey, error, isLoading, update, reload: () => mutate() };
}
