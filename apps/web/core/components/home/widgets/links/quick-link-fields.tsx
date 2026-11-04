/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise KEP-82: URL, title and icon fields of the quick link modal.
// The icon is picked from the same emoji/icon set as a project icon; without one the site favicon shows.
// Title and icon each have their own clear button that brings back the site's default.
import { useState } from "react";
import type { Control, FieldErrors } from "react-hook-form";
import { Controller } from "react-hook-form";
import { useTranslation } from "@plane/i18n";
import { EmojiIconPickerTypes, EmojiPicker, Logo } from "@plane/propel/emoji-icon-picker";
import { CloseIcon, LinkIcon } from "@plane/propel/icons";
import type { TLogoProps } from "@plane/types";
import { Input } from "@plane/ui";

export type TQuickLinkFormValues = {
  url: string;
  title: string;
  logo_props: TLogoProps | null;
};

export const EMPTY_QUICK_LINK_FORM: TQuickLinkFormValues = { url: "", title: "", logo_props: null };

type TPickerValue = { type: "emoji" | "icon"; value: unknown };

/** Same shape the project form builds from the picker. */
const toLogoProps = (picked: TPickerValue): TLogoProps =>
  picked.type === "emoji"
    ? { in_use: "emoji", emoji: { value: picked.value as string } }
    : { in_use: "icon", icon: picked.value as TLogoProps["icon"] };

type ClearButtonProps = { label: string; onClick: () => void; className: string };

function ClearButton({ label, onClick, className }: ClearButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className={`grid place-items-center rounded-full text-tertiary hover:bg-layer-transparent-hover hover:text-primary focus-visible:outline-accent-strong ${className}`}
    >
      <CloseIcon className="size-3" />
    </button>
  );
}

type Props = {
  control: Control<TQuickLinkFormValues>;
  errors: FieldErrors<TQuickLinkFormValues>;
  /** Title fetched from the site, shown as the placeholder so users see the default. */
  siteTitle?: string | null;
};

export function QuickLinkFields({ control, errors, siteTitle }: Props) {
  const { t } = useTranslation();
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  return (
    <div className="mt-2 space-y-3">
      <div>
        <label htmlFor="quick-link-url" className="mb-2 text-14 font-medium text-secondary">
          {t("link.modal.url.text")}
          <span className="block text-10">{t("required")}</span>
        </label>
        <Controller
          control={control}
          name="url"
          rules={{ required: t("link.modal.url.required") }}
          render={({ field: { value, onChange, ref } }) => (
            <Input
              id="quick-link-url"
              type="text"
              value={value}
              onChange={onChange}
              ref={ref}
              hasError={Boolean(errors.url)}
              placeholder={t("link.modal.url.placeholder")}
              className="w-full"
            />
          )}
        />
        {errors.url && <span className="text-11 text-danger-primary">{t("link.modal.url.required")}</span>}
      </div>
      <div>
        <label htmlFor="quick-link-title" className="mb-2 text-14 font-medium text-secondary">
          {t("link.modal.title.text")}
          <span className="block text-10">{t("quick_links_ui.title_hint")}</span>
        </label>
        <div className="flex items-center gap-2">
          <Controller
            control={control}
            name="logo_props"
            render={({ field: { value, onChange } }) => (
              <span className="relative flex-shrink-0">
                <EmojiPicker
                  iconType="material"
                  isOpen={isPickerOpen}
                  handleToggle={setIsPickerOpen}
                  className="flex items-center justify-center"
                  buttonClassName="flex items-center justify-center"
                  label={
                    <span
                      className="grid size-9 place-items-center rounded-md border-[0.5px] border-subtle bg-layer-2"
                      title={t("quick_links_ui.icon_label")}
                      aria-label={t("quick_links_ui.icon_label")}
                    >
                      {value ? <Logo logo={value} size={18} /> : <LinkIcon className="size-4 text-tertiary" />}
                    </span>
                  }
                  onChange={(picked: TPickerValue) => {
                    onChange(toLogoProps(picked));
                    setIsPickerOpen(false);
                  }}
                  defaultIconColor={value?.in_use === "icon" ? value.icon?.color : undefined}
                  defaultOpen={value?.in_use === "emoji" ? EmojiIconPickerTypes.EMOJI : EmojiIconPickerTypes.ICON}
                />
                {value && (
                  // Sibling, not inside the picker: a button cannot sit inside the picker's own button.
                  <ClearButton
                    label={t("quick_links_ui.reset_icon")}
                    onClick={() => onChange(null)}
                    className="absolute -top-1.5 -right-1.5 size-4 border-[0.5px] border-subtle bg-surface-1"
                  />
                )}
              </span>
            )}
          />
          <Controller
            control={control}
            name="title"
            render={({ field: { value, onChange, ref } }) => (
              <div className="relative flex-1">
                <Input
                  id="quick-link-title"
                  type="text"
                  value={value}
                  onChange={onChange}
                  ref={ref}
                  placeholder={siteTitle || t("link.modal.title.placeholder")}
                  className={value ? "w-full pr-8" : "w-full"}
                />
                {value && (
                  <ClearButton
                    label={t("quick_links_ui.reset_title")}
                    onClick={() => onChange("")}
                    className="absolute top-1/2 right-2 size-5 -translate-y-1/2"
                  />
                )}
              </div>
            )}
          />
        </div>
        <span className="mt-1 block text-11 text-tertiary">{t("quick_links_ui.icon_hint")}</span>
      </div>
    </div>
  );
}
