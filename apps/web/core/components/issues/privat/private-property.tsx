/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: saklar tugas privat di sidebar detail dan peek (P29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { LockIcon } from "@plane/propel/icons";
import { ToggleSwitch } from "@plane/ui";
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";

type TPrivatePropertyProps = {
  value: boolean;
  onChange: (isPrivate: boolean) => void;
  disabled: boolean;
};

export function PrivateProperty({ value, onChange, disabled }: TPrivatePropertyProps) {
  const { t } = useTranslation();
  return (
    <SidebarPropertyListItem icon={LockIcon} label={t("privat.label")}>
      <div className="flex h-7.5 items-center gap-2 px-2" title={t("privat.description")}>
        <ToggleSwitch value={value} onChange={onChange} disabled={disabled} label={t("privat.label")} />
        <span className="text-body-xs-regular text-tertiary">{value ? t("privat.on") : t("privat.off")}</span>
      </div>
    </SidebarPropertyListItem>
  );
}
