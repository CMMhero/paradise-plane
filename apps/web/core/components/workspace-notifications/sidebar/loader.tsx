/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { range } from "lodash-es";

// Paradise: cermin baris ringkas di notification-card/item.tsx (foto 32px, tiga lapis teks).
export function NotificationsLoader({ rows = 8 }: { rows?: number }) {
  return (
    <div className="animate-pulse divide-y divide-subtle overflow-hidden">
      {range(rows).map((i) => (
        <div key={i} className="flex w-full items-start gap-2.5 py-2.5 pr-3 pl-5">
          <span className="size-8 shrink-0 rounded-full bg-layer-1" />
          <div className="flex w-full flex-col gap-1.5">
            <span className="h-3.5 w-4/5 rounded-xs bg-layer-1" />
            <span className="h-3 w-3/5 rounded-xs bg-layer-1" />
            <span className="h-3 w-24 rounded-xs bg-layer-1" />
          </div>
        </div>
      ))}
    </div>
  );
}
