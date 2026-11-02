/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kolom profil di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bahasa, zona waktu, tema, awal pekan, tampilan notifikasi, kursor, rel aplikasi.
 * Dipakai dua tempat dengan bentuk data yang sama: preferensi satu member
 * (preferensi.tsx) dan bawaan member baru (bawaan-member/page.tsx).
 */

import { useEffect, useState } from "react";
// plane imports
import { InstanceMemberService, type TMemberPreferences, type TMemberTheme, type TZonaWaktu } from "@plane/services";
import { CustomSearchSelect, CustomSelect, ToggleSwitch } from "@plane/ui";
// components
import { Field } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BAHASA_PROFIL } from "./constants";

const TOMBOL_SELECT = "w-full rounded-md border-subtle bg-layer-2";

const memberService = new InstanceMemberService();

export type TProfil = TMemberPreferences["profile"];

/** Tema yang bisa dipilih admin. "custom" tidak: paletnya disusun orangnya sendiri. */
const TEMA_PILIHAN: Exclude<TMemberTheme, "custom">[] = ["system", "light", "dark", "light-contrast", "dark-contrast"];

/** Daftar zona waktu dimuat sekali per halaman, dipakai semua panel. */
let zonaWaktuCache: Promise<TZonaWaktu[]> | null = null;
const muatZonaWaktu = () => {
  zonaWaktuCache ??= memberService.daftarZonaWaktu().catch((err) => {
    zonaWaktuCache = null;
    throw err;
  });
  return zonaWaktuCache;
};

export function useZonaWaktu(): TZonaWaktu[] {
  const [daftar, setDaftar] = useState<TZonaWaktu[]>([]);
  useEffect(() => {
    let hidup = true;
    muatZonaWaktu()
      .then((z) => {
        if (hidup) setDaftar(z);
        return null;
      })
      // Gagal muat = pilihan hanya berisi nilai sekarang; bagian lain tetap jalan.
      .catch(() => {});
    return () => {
      hidup = false;
    };
  }, []);
  return daftar;
}

type Props = {
  profile: TProfil;
  onProfil: (p: Partial<TProfil>) => void;
};

export function BidangProfil({ profile, onProfil }: Props) {
  const { s } = useGodmodeStrings();
  const t = s.editor.prefs;
  const zonaWaktu = useZonaWaktu();

  const labelTema: Record<TMemberTheme, string> = {
    system: t.theme_system,
    light: t.theme_light,
    dark: t.theme_dark,
    "light-contrast": t.theme_light_contrast,
    "dark-contrast": t.theme_dark_contrast,
    custom: t.theme_custom,
  };
  // Nilai tersimpan bisa di luar daftar (mis. "UTC" atau gagal muat): tetap tampil.
  const zonaAdaDiDaftar = zonaWaktu.some((z) => z.value === profile.timezone);
  const opsiZona = [
    ...(zonaAdaDiDaftar ? [] : [{ value: profile.timezone, label: profile.timezone, utc_offset: "" }]),
    ...zonaWaktu,
  ];
  const zonaTerpilih = opsiZona.find((z) => z.value === profile.timezone);
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field label={t.timezone}>
        <CustomSearchSelect
          value={profile.timezone}
          label={zonaTerpilih ? zonaTerpilih.label : profile.timezone}
          onChange={(v: string) => onProfil({ timezone: v })}
          buttonClassName={TOMBOL_SELECT}
          className="w-full"
          input
          maxHeight="lg"
          options={opsiZona.map((z) => ({
            value: z.value,
            query: `${z.label} ${z.value} ${z.utc_offset}`,
            content: (
              <span className="flex w-full items-center justify-between gap-2">
                <span className="truncate">{z.label}</span>
                {z.utc_offset && <span className="shrink-0 text-11 text-tertiary">{z.utc_offset}</span>}
              </span>
            ),
          }))}
        />
      </Field>
      <Field label={t.theme}>
        <CustomSelect
          value={profile.theme}
          label={labelTema[profile.theme]}
          onChange={(v: TMemberTheme) => onProfil({ theme: v })}
          buttonClassName={TOMBOL_SELECT}
          className="w-full"
          input
        >
          {TEMA_PILIHAN.map((v) => (
            <CustomSelect.Option key={v} value={v}>
              {labelTema[v]}
            </CustomSelect.Option>
          ))}
        </CustomSelect>
      </Field>
      <Field label={t.language}>
        <CustomSelect
          value={profile.language}
          label={BAHASA_PROFIL.find((b) => b.value === profile.language)?.label ?? profile.language}
          onChange={(v: string) => onProfil({ language: v })}
          buttonClassName={TOMBOL_SELECT}
          className="w-full"
          maxHeight="lg"
          input
        >
          {BAHASA_PROFIL.map((b) => (
            <CustomSelect.Option key={b.value} value={b.value}>
              {b.label}
            </CustomSelect.Option>
          ))}
        </CustomSelect>
      </Field>
      <Field label={t.week_start}>
        <CustomSelect
          value={profile.start_of_the_week}
          label={t.days[profile.start_of_the_week] ?? t.days[0]}
          onChange={(v: number) => onProfil({ start_of_the_week: Number(v) })}
          buttonClassName={TOMBOL_SELECT}
          className="w-full"
          input
        >
          {t.days.map((hari, i) => (
            <CustomSelect.Option key={hari} value={i}>
              {hari}
            </CustomSelect.Option>
          ))}
        </CustomSelect>
      </Field>
    </div>
  );
}

/** Satu saklar email: label di kiri, ToggleSwitch upstream di kanan. Dipakai preferensi & bawaan. */
export function Saklar({
  label,
  nilai,
  onUbah,
  disabled,
}: {
  label: string;
  nilai: boolean;
  onUbah: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-12 text-primary">{label}</span>
      <ToggleSwitch value={nilai} label={label} onChange={() => onUbah(!nilai)} disabled={disabled} />
    </div>
  );
}
