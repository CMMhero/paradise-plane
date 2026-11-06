/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Pemilih ikon/emoji view. Dulu hanya ada di formulir view departemen; kini dipakai
 * kedua formulir supaya view workspace juga bisa punya ikon (kolom `logo_props`
 * memang ada di IssueView).
 */

import { useState } from "react";
import { useTranslation } from "@plane/i18n";
import { EmojiPicker, EmojiIconPickerTypes, Logo } from "@plane/propel/emoji-icon-picker";
import { ViewsIcon } from "@plane/propel/icons";
import type { TLogoProps } from "@plane/types";

type Props = {
  value: TLogoProps | undefined;
  onChange: (logo: TLogoProps) => void;
};

export function ViewLogoPicker({ value, onChange }: Props) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <EmojiPicker
      iconType="lucide"
      isOpen={isOpen}
      handleToggle={(val: boolean) => setIsOpen(val)}
      className="flex flex-shrink-0 items-center justify-center"
      buttonClassName="flex items-center justify-center"
      label={
        <span
          className="grid h-9 w-9 place-items-center rounded-item border border-subtle bg-layer-2"
          aria-label={t("views_ui.icon_label")}
        >
          {value?.in_use ? (
            <Logo logo={value} size={18} type="lucide" />
          ) : (
            <ViewsIcon className="h-4 w-4 text-tertiary" />
          )}
        </span>
      }
      // TODO: fix types (bentuk nilai EmojiPicker belum diketik di propel)
      onChange={(val: any) => {
        let logoValue = {};
        if (val?.type === "emoji") logoValue = { value: val.value };
        else if (val?.type === "icon") logoValue = val.value;

        onChange({ in_use: val?.type, [val?.type]: logoValue } as TLogoProps);
        setIsOpen(false);
      }}
      defaultIconColor={value?.in_use === "icon" ? value?.icon?.color : undefined}
      defaultOpen={value?.in_use === "emoji" ? EmojiIconPickerTypes.EMOJI : EmojiIconPickerTypes.ICON}
    />
  );
}
