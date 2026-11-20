/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: urutan linimasa aktivitas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { E_SORT_ORDER } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { CustomSelect } from "@plane/ui";
// components
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useUrutanAktivitas } from "@/hooks/use-urutan-aktivitas";

const PILIHAN = [E_SORT_ORDER.DESC, E_SORT_ORDER.ASC] as const;

export const PreferensiUrutanAktivitas = observer(function PreferensiUrutanAktivitas() {
  const { t } = useTranslation();
  const { urutan, setUrutan } = useUrutanAktivitas();
  const label = (nilai: E_SORT_ORDER) => t(`ui_fixes.activity_order_${nilai}`);

  return (
    <SettingsControlItem
      title={t("ui_fixes.activity_order")}
      description={t("ui_fixes.activity_order_help")}
      control={
        <CustomSelect
          value={urutan}
          label={label(urutan)}
          onChange={(v: E_SORT_ORDER) => void setUrutan(v)}
          buttonClassName="border border-subtle-1"
          placement="bottom-end"
          input
        >
          {PILIHAN.map((nilai) => (
            <CustomSelect.Option key={nilai} value={nilai}>
              {label(nilai)}
            </CustomSelect.Option>
          ))}
        </CustomSelect>
      }
    />
  );
});
