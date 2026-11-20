/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tanda tugas privat (P29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { Badge } from "@plane/propel/badge";
import { LockIcon } from "@plane/propel/icons";
import { Tooltip } from "@plane/propel/tooltip";
import { usePlatformOS } from "@/hooks/use-platform-os";

type TPrivateBadgeProps = {
  isPrivate: boolean | undefined;
  /** `badge` = ikon + "Private" (list, kanban, detail); `icon` = gembok saja untuk baris padat. */
  variant?: "badge" | "icon";
};

export function PrivateBadge({ isPrivate, variant = "badge" }: TPrivateBadgeProps) {
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  if (!isPrivate) return null;

  const label = t("privat.label");
  return (
    <Tooltip tooltipContent={t("privat.tooltip")} isMobile={isMobile}>
      {variant === "icon" ? (
        <span className="flex shrink-0 items-center text-tertiary" aria-label={label}>
          <LockIcon className="size-3" aria-hidden />
        </span>
      ) : (
        <span className="flex w-fit shrink-0">
          <Badge prependIcon={<LockIcon aria-hidden />}>{label}</Badge>
        </span>
      )}
    </Tooltip>
  );
}
