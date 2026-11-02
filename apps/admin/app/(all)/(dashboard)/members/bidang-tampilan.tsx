/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: navigasi sidebar & tata letak work item di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dipakai dua tempat dengan bentuk data yang sama, seperti bidang-profil.tsx:
 * preferensi satu member (preferensi.tsx) dan bawaan member baru
 * (bawaan-member/page.tsx).
 */

import { useState } from "react";
// plane imports
import type { TMemberNavigation, TNavItemKey, TProjectNavMode, TWorkItemLayout } from "@plane/services";
import { CustomSelect } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { Field } from "@/components/common/paradise-ui";
import { inputClass } from "@/components/common/paradise-styles";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { Saklar } from "./bidang-profil";

const TOMBOL_SELECT = "w-full rounded-md border-subtle bg-layer-2";

/** Urutan dan kelompok sama dengan dialog "Customize navigation" di apps/web. */
const NAV_PRIBADI: TNavItemKey[] = ["your_work", "stickies", "drafts", "quick_links"];
const NAV_WORKSPACE: TNavItemKey[] = [
  "views",
  "analytics",
  "dashboard_divisi",
  "initiatives",
  "chat",
  "wiki",
  "archives",
];
const MODE_PROJECT: TProjectNavMode[] = ["ACCORDION", "TABBED"];
export const TATA_LETAK: TWorkItemLayout[] = ["kanban", "list", "calendar", "spreadsheet"];
const BATAS_PROJECT_MAKS = 50;

type TNavProps = {
  nilai: TMemberNavigation;
  onUbah: (n: Partial<TMemberNavigation>) => void;
};

/** Angka batas project. Draf lokal supaya ketikan setengah jadi tidak langsung ditolak. */
function BatasProject({ nilai, onUbah }: { nilai: number; onUbah: (v: number) => void }) {
  const { s } = useGodmodeStrings();
  const [draf, setDraf] = useState(String(nilai));
  const [terakhir, setTerakhir] = useState(nilai);
  // Nilai luar berubah (reset ke pabrik, muat ulang) -> ikuti tanpa efek.
  if (nilai !== terakhir) {
    setTerakhir(nilai);
    setDraf(String(nilai));
  }
  const angka = Number(draf);
  const sah = /^\d+$/.test(draf.trim()) && angka <= BATAS_PROJECT_MAKS;

  return (
    <Field label={s.tampilan.project_limit} hint={s.tampilan.project_limit_hint}>
      <input
        type="number"
        inputMode="numeric"
        min={0}
        max={BATAS_PROJECT_MAKS}
        value={draf}
        aria-label={s.tampilan.project_limit}
        aria-invalid={!sah}
        onChange={(e) => {
          setDraf(e.target.value);
          const baru = Number(e.target.value);
          if (/^\d+$/.test(e.target.value.trim()) && baru <= BATAS_PROJECT_MAKS) {
            setTerakhir(baru);
            onUbah(baru);
          }
        }}
        className={cn(inputClass, "w-full", { "border-danger-strong": !sah })}
      />
    </Field>
  );
}

export function BidangNavigasi({ nilai, onUbah }: TNavProps) {
  const { s } = useGodmodeStrings();
  const t = s.tampilan;
  const labelMode: Record<TProjectNavMode, string> = {
    ACCORDION: t.project_mode_accordion,
    TABBED: t.project_mode_tabbed,
  };

  const kelompok = (judul: string, kunci: TNavItemKey[]) => (
    <div className="space-y-0.5">
      <span className="block text-11 font-medium text-tertiary">{judul}</span>
      {kunci.map((k) => (
        <Saklar
          key={k}
          label={t.items[k]}
          nilai={nilai.pinned[k]}
          onUbah={(v) => onUbah({ pinned: { ...nilai.pinned, [k]: v } })}
        />
      ))}
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <div>
          <span className="block text-12 font-medium text-secondary">{t.pinned}</span>
          <span className="block text-11 text-tertiary">{t.pinned_note}</span>
        </div>
        <div className="grid gap-x-8 gap-y-3 rounded-md border border-subtle px-3 py-2 sm:grid-cols-2">
          {kelompok(t.group_personal, NAV_PRIBADI)}
          {kelompok(t.group_workspace, NAV_WORKSPACE)}
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t.project_mode}>
          <CustomSelect
            value={nilai.project_mode}
            label={labelMode[nilai.project_mode]}
            onChange={(v: TProjectNavMode) => onUbah({ project_mode: v })}
            buttonClassName={TOMBOL_SELECT}
            className="w-full"
            input
          >
            {MODE_PROJECT.map((m) => (
              <CustomSelect.Option key={m} value={m}>
                {labelMode[m]}
              </CustomSelect.Option>
            ))}
          </CustomSelect>
        </Field>
        <BatasProject nilai={nilai.project_limit} onUbah={(v) => onUbah({ project_limit: v })} />
      </div>
    </div>
  );
}

type TLayoutProps = {
  nilai: TWorkItemLayout;
  onUbah: (v: TWorkItemLayout) => void;
  hint?: string;
};

export function BidangTataLetak({ nilai, onUbah, hint }: TLayoutProps) {
  const { s } = useGodmodeStrings();
  const t = s.tampilan;
  return (
    <Field label={t.layout} hint={hint}>
      <CustomSelect
        value={nilai}
        label={t.layouts[nilai]}
        onChange={(v: TWorkItemLayout) => onUbah(v)}
        buttonClassName={TOMBOL_SELECT}
        className="w-full sm:w-1/2"
        input
      >
        {TATA_LETAK.map((l) => (
          <CustomSelect.Option key={l} value={l}>
            {t.layouts[l]}
          </CustomSelect.Option>
        ))}
      </CustomSelect>
    </Field>
  );
}
