/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: modul yang dimatikan dari God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TParadiseModule } from "@plane/types";
import { useInstance } from "@/hooks/store/use-instance";
import { isNavKeyEnabled, isParadiseModuleEnabled } from "@/lib/paradise-modules";

/** Dipanggil dari komponen `observer` supaya ikut berubah saat config instance dimuat. */
export function useParadiseModules() {
  const { config } = useInstance();
  return {
    isModuleEnabled: (module: TParadiseModule) => isParadiseModuleEnabled(config, module),
    isNavKeyEnabled: (key: string) => isNavKeyEnabled(config, key),
  };
}
