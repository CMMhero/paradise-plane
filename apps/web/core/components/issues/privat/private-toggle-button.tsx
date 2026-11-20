/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pilihan tugas privat di modal buat (P29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { LockIcon } from "@plane/propel/icons";
import { Tooltip } from "@plane/propel/tooltip";
import { cn } from "@plane/utils";
import { usePlatformOS } from "@/hooks/use-platform-os";

type TPrivateToggleButtonProps = {
  value: boolean;
  onChange: (isPrivate: boolean) => void;
  tabIndex?: number;
};

export function PrivateToggleButton({ value, onChange, tabIndex }: TPrivateToggleButtonProps) {
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  return (
    <Tooltip tooltipContent={t("privat.description")} isMobile={isMobile}>
      <button
        type="button"
        aria-pressed={value}
        tabIndex={tabIndex}
        onClick={() => onChange(!value)}
        className={cn(
          "flex h-full cursor-pointer items-center gap-1 rounded-sm border-[0.5px] border-strong px-2 py-0.5 text-caption-sm-regular hover:bg-layer-1",
          value ? "bg-layer-2 text-primary" : "text-tertiary"
        )}
      >
        <LockIcon className="size-3 shrink-0" aria-hidden />
        <span className="whitespace-nowrap">{t("privat.label")}</span>
      </button>
    </Tooltip>
  );
}
