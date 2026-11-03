/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: preferensi tampilan (KEP-64)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Skema warna, font, dan animasi. Disimpan ke
 * `profile.theme` lewat `updateUserTheme`, sama seperti pilihan tema di
 * atasnya, jadi ikut tersimpan per akun dan terbawa ke perangkat lain.
 * Bawaan untuk akun baru diatur di God Mode > Members > Defaults.
 */

import type { CSSProperties, ReactNode } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import type { TTampilanFont, TTampilanSkema } from "@plane/types";
import { CustomSelect } from "@plane/ui";
// components
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useUserProfile } from "@/hooks/store/user";
// lib
import { bacaTampilan, TAMPILAN_SAH, type TTampilan } from "@/lib/tampilan";

/**
 * Contoh warna tiap skema untuk pratinjau di daftar pilihan: latar terang,
 * latar gelap, aksen utama, aksen kedua. SENGAJA nilai tetap, bukan token: token selalu
 * mencerminkan skema yang SEDANG aktif, padahal di sini setiap baris harus
 * memperlihatkan skemanya sendiri. Cermin kenop di paradise-tampilan.css.
 */
const CONTOH_SKEMA: Record<TTampilanSkema, [string, string, string, string]> = {
  bara: ["oklch(0.954 0.011 62)", "oklch(0.238 0.015 38)", "oklch(0.58 0.2335 27.24)", "oklch(0.74 0.15 65)"],
  senja: ["oklch(0.954 0.009 285)", "oklch(0.238 0.024 285)", "oklch(0.55 0.19 300)", "oklch(0.64 0.17 345)"],
  sumi: ["oklch(0.954 0.009 95)", "oklch(0.238 0.024 245)", "oklch(0.53 0.16 258)", "oklch(0.62 0.1 190)"],
  hutan: ["oklch(0.954 0.01 140)", "oklch(0.238 0.02 160)", "oklch(0.5 0.15 152)", "oklch(0.72 0.13 85)"],
  netral: ["oklch(0.954 0.001 230)", "oklch(0.238 0.003 230)", "oklch(0.53 0.17 250)", "oklch(0.74 0.15 65)"],
};

/** Keluarga font tiap pilihan, supaya labelnya ditulis dengan font itu sendiri. */
const KELUARGA_FONT: Record<TTampilanFont, string> = {
  jakarta: "'Plus Jakarta Sans Variable'",
  inter: "'Inter Variable'",
  geist: "'Geist Variable'",
  figtree: "'Figtree Variable'",
  bricolage: "'Bricolage Grotesque Variable'",
  archivo: "'Archivo Variable'",
  sora: "'Sora Variable'",
  shantell: "'Shantell Sans Variable'",
  jetbrains: "'JetBrains Mono Variable'",
  serif: "'Source Serif 4 Variable'",
  sistem: "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
};

const NAMA_FONT: Record<Exclude<TTampilanFont, "sistem">, string> = {
  jakarta: "Plus Jakarta Sans",
  inter: "Inter",
  geist: "Geist",
  figtree: "Figtree",
  bricolage: "Bricolage Grotesque",
  archivo: "Archivo",
  sora: "Sora",
  shantell: "Shantell Sans",
  jetbrains: "JetBrains Mono",
  serif: "Source Serif 4",
};

function ContohSkema({ skema }: { skema: TTampilanSkema }) {
  const [terang, gelap, aksen, aksenKedua] = CONTOH_SKEMA[skema];
  return (
    <span aria-hidden className="flex shrink-0 overflow-hidden rounded-control border border-subtle-1">
      <span className="size-3.5" style={{ background: terang }} />
      <span className="size-3.5" style={{ background: gelap }} />
      <span className="size-3.5" style={{ background: aksen }} />
      <span className="size-3.5" style={{ background: aksenKedua }} />
    </span>
  );
}

type TBaris = { judul: string; uraian: string; label: (nilai: string) => ReactNode };

export const PreferensiTampilan = observer(function PreferensiTampilan() {
  const { t } = useTranslation();
  const { data: userProfile, updateUserTheme } = useUserProfile();

  if (!userProfile) return null;
  const sekarang = bacaTampilan(userProfile.theme);

  const ubah = async <K extends keyof TTampilan>(kunci: K, nilai: TTampilan[K]) => {
    if (sekarang[kunci] === nilai) return;
    try {
      await updateUserTheme({ [kunci]: nilai });
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("appearance_ui.saved") });
    } catch {
      // Store sudah mengembalikan nilai lama; cukup beri tahu orangnya.
      setToast({ type: TOAST_TYPE.ERROR, title: t("appearance_ui.failed") });
    }
  };

  const labelFont = (nilai: string) => {
    const font = nilai as TTampilanFont;
    const gaya: CSSProperties = { fontFamily: KELUARGA_FONT[font] };
    return <span style={gaya}>{font === "sistem" ? t("appearance_ui.font_system") : NAMA_FONT[font]}</span>;
  };

  const BARIS: Record<keyof TTampilan, TBaris> = {
    skema: {
      judul: "appearance_ui.scheme",
      uraian: "appearance_ui.scheme_desc",
      label: (nilai) => (
        <span className="flex items-center gap-2">
          <ContohSkema skema={nilai as TTampilanSkema} />
          {t(`appearance_ui.scheme_${nilai}`)}
        </span>
      ),
    },
    font: { judul: "appearance_ui.font", uraian: "appearance_ui.font_desc", label: labelFont },
    gerak: {
      judul: "appearance_ui.motion",
      uraian: "appearance_ui.motion_desc",
      label: (nilai) => t(nilai === "halus" ? "appearance_ui.motion_smooth" : "appearance_ui.motion_reduce"),
    },
  };

  return (
    <>
      {(Object.keys(BARIS) as (keyof TTampilan)[]).map((kunci) => {
        const baris = BARIS[kunci];
        return (
          <SettingsControlItem
            key={kunci}
            title={t(baris.judul)}
            description={t(baris.uraian)}
            control={
              <CustomSelect
                value={sekarang[kunci]}
                label={baris.label(sekarang[kunci])}
                onChange={(v: TTampilan[typeof kunci]) => void ubah(kunci, v)}
                buttonClassName="border border-subtle-1"
                placement="bottom-end"
                input
              >
                {TAMPILAN_SAH[kunci].map((nilai) => (
                  <CustomSelect.Option key={nilai} value={nilai}>
                    {baris.label(nilai)}
                  </CustomSelect.Option>
                ))}
              </CustomSelect>
            }
          />
        );
      })}
    </>
  );
});
