/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise: icon from an image URL. The user pastes an https link; the server downloads it
// and stores a copy, so other people's browsers never call that link. The preview below loads
// the link in this browser only to show the author what they are about to save.
import { useState } from "react";
import { useTranslation } from "@plane/i18n";
import type { TQuickLinkLogoProps } from "@plane/types";
import { Input } from "@plane/ui";

type TStatus = "idle" | "loading" | "loaded" | "error";

type Props = {
  value: TQuickLinkLogoProps | null;
  onChange: (next: TQuickLinkLogoProps | null) => void;
};

const isHttps = (url: string) => /^https:\/\/\S+$/i.test(url);

export function QuickLinkImageField({ value, onChange }: Props) {
  const { t } = useTranslation();
  const image = value?.in_use === "image" ? value.image : undefined;
  const url = image?.url ?? "";
  // The preview is keyed by the url it loaded, so editing the field resets it without an effect.
  const [loaded, setLoaded] = useState<{ url: string; status: "loaded" | "error" } | null>(null);
  const previewSrc = image?.data ?? (isHttps(url) ? url : null);
  const status: TStatus = !previewSrc ? "idle" : loaded?.url === previewSrc ? loaded.status : "loading";
  const showNotHttps = url.length > 0 && !isHttps(url);

  return (
    <div className="space-y-1.5">
      <label htmlFor="quick-link-image-url" className="text-14 font-medium text-secondary">
        {t("quick_links_ui.image_label")}
      </label>
      <div className="flex items-center gap-2">
        <span
          className="grid size-9 flex-shrink-0 place-items-center overflow-hidden rounded-md border-[0.5px] border-subtle bg-layer-2"
          aria-live="polite"
        >
          {previewSrc && status !== "error" ? (
            <img
              key={previewSrc}
              src={previewSrc}
              alt={t("quick_links_ui.image_preview_alt")}
              referrerPolicy="no-referrer"
              onLoad={() => setLoaded({ url: previewSrc, status: "loaded" })}
              onError={() => setLoaded({ url: previewSrc, status: "error" })}
              className={`size-6 object-contain ${status === "loaded" ? "" : "opacity-40"}`}
            />
          ) : null}
        </span>
        <Input
          id="quick-link-image-url"
          type="url"
          inputMode="url"
          value={url}
          onChange={(e) => {
            const next = e.target.value.trim();
            // Dropping `data` makes the server download the new address.
            onChange(next ? { in_use: "image", image: { url: next } } : { in_use: "image", image: {} });
          }}
          hasError={status === "error" || showNotHttps}
          placeholder={t("quick_links_ui.image_placeholder")}
          className="w-full"
        />
      </div>
      <p className="text-11 text-tertiary" role={status === "error" || showNotHttps ? "alert" : undefined}>
        {showNotHttps
          ? t("quick_links_ui.image_not_https")
          : status === "loading"
            ? t("quick_links_ui.image_loading")
            : status === "error"
              ? t("quick_links_ui.image_error")
              : t("quick_links_ui.image_hint")}
      </p>
    </div>
  );
}
