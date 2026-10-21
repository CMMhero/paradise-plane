/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// ui
import { Tooltip } from "@plane/propel/tooltip";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
import packageJson from "package.json";

// Dulu tombol "Community" yang membuka PaidPlanUpgradeModal, ajakan berlangganan
// tier berbayar upstream. Tidak relevan untuk alat internal kantor, jadi modalnya
// dibuang. Nomor versinya DIPERTAHANKAN: berguna waktu ada yang melapor masalah
// dan kita perlu tahu dia memakai rilis yang mana. Sekarang sekadar label, bukan
// tombol, tidak ada lagi yang bisa diklik.
export const WorkspaceEditionBadge = observer(function WorkspaceEditionBadge() {
  // platform
  const { isMobile } = usePlatformOS();

  return (
    <Tooltip tooltipContent={`Versi v${packageJson.version}`} isMobile={isMobile}>
      <span className="rounded-sm bg-layer-2 px-2 py-1 text-11 font-medium text-secondary">v{packageJson.version}</span>
    </Tooltip>
  );
});
