/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bawaan project baru di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Setelan yang diterima project baru. Server: plane/utils/bawaan_project.py.
 * Formulir "Create project" di apps/web terisi nilai ini (pembuat masih bisa
 * mengubahnya); server mengisi kolom yang tidak dikirim pemanggil lain.
 */

import { useState } from "react";
import type { ReactNode } from "react";
import useSWR from "swr";
import { Button } from "@plane/propel/button";
import { setPromiseToast } from "@plane/propel/toast";
import { InstanceMemberService, type TProjectDefaults } from "@plane/services";
import { CustomSearchSelect, CustomSelect, Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { Field } from "@/components/common/paradise-ui";
import { UnsavedBar } from "@/components/common/unsaved-changes";
import { WorkspacesTabs } from "@/components/common/section-tabs";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { Saklar, useZonaWaktu } from "../members/bidang-profil";
import type { Route } from "./+types/page";

const memberService = new InstanceMemberService();

const BULAN = Array.from({ length: 13 }, (_, i) => i);

const sama = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

function Bagian({ title, note, children }: { title: string; note: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <div className="space-y-0.5">
        <h3 className="text-11 font-medium tracking-wide text-secondary uppercase">{title}</h3>
        <p className="text-12 text-tertiary">{note}</p>
      </div>
      <div className="space-y-3 rounded-card border border-subtle px-4 py-3">{children}</div>
    </section>
  );
}

function PilihBulan({ label, nilai, onUbah }: { label: string; nilai: number; onUbah: (v: number) => void }) {
  const { s, fill } = useGodmodeStrings();
  const teks = (n: number) => (n === 0 ? s.bawaan_project.off : fill(s.bawaan_project.months, { count: n }));
  return (
    <Field label={label}>
      <CustomSelect
        value={nilai}
        label={teks(nilai)}
        onChange={(v: number) => onUbah(Number(v))}
        buttonClassName="w-full"
        className="w-full"
        maxHeight="lg"
        input
      >
        {BULAN.map((n) => (
          <CustomSelect.Option key={n} value={n}>
            {teks(n)}
          </CustomSelect.Option>
        ))}
      </CustomSelect>
    </Field>
  );
}

function BawaanProjectPage(_props: Route.ComponentProps) {
  const { s } = useGodmodeStrings();
  const t = s.bawaan_project;
  const zonaWaktu = useZonaWaktu();
  const { data, error, mutate } = useSWR("INSTANCE_PROJECT_DEFAULTS", () => memberService.bawaanProject());
  // null = belum disentuh, tampilkan nilai server apa adanya.
  const [draf, setDraf] = useState<TProjectDefaults | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const tersimpan: TProjectDefaults | null = data
    ? {
        network: data.network,
        timezone: data.timezone,
        archive_in: data.archive_in,
        close_in: data.close_in,
        guest_view_all_features: data.guest_view_all_features,
      }
    : null;
  const nilai = draf ?? tersimpan;
  const isDirty = Boolean(draf && tersimpan && !sama(draf, tersimpan));

  const ubah = (p: Partial<TProjectDefaults>) => {
    if (!tersimpan) return;
    setDraf((d) => ({ ...(d ?? tersimpan), ...p }));
  };

  const simpan = async () => {
    if (!draf) return;
    setIsSaving(true);
    const janji = memberService.ubahBawaanProject(draf);
    setPromiseToast(janji, {
      loading: t.saving,
      success: { title: t.saved, message: () => t.title },
      error: { title: t.save_failed, message: (e) => (e as { error?: string })?.error ?? t.save_failed },
    });
    try {
      await mutate(await janji, { revalidate: false });
      setDraf(null);
    } catch {
      // Toast sudah memberi tahu; draf dibiarkan supaya tidak hilang.
    } finally {
      setIsSaving(false);
    }
  };

  const labelVisibilitas = (n: 0 | 2) => (n === 0 ? t.network_private : t.network_public);
  // Nilai tersimpan bisa di luar daftar (mis. "UTC" atau gagal muat): tetap tampil.
  const opsiZona = nilai
    ? [
        ...(zonaWaktu.some((z) => z.value === nilai.timezone)
          ? []
          : [{ value: nilai.timezone, label: nilai.timezone, utc_offset: "" }]),
        ...zonaWaktu,
      ]
    : [];

  return (
    <PageWrapper header={{ title: "Workspaces on this instance", description: t.description }}>
      <WorkspacesTabs />
      <UnsavedBar isDirty={isDirty} isSaving={isSaving} onSave={simpan} onDiscard={() => setDraf(null)} />
      {error && <p className="text-13 text-danger-primary">{t.load_failed}</p>}
      {!error && !nilai && (
        <Loader className="space-y-4">
          <Loader.Item height="120px" />
          <Loader.Item height="120px" />
        </Loader>
      )}
      {nilai && data && (
        <div className="space-y-8">
          <Bagian title={t.group_access} note={t.access_note}>
            <Field label={t.network}>
              <CustomSelect
                value={nilai.network}
                label={labelVisibilitas(nilai.network)}
                onChange={(v: 0 | 2) => ubah({ network: Number(v) as 0 | 2 })}
                buttonClassName="w-full"
                className="w-full"
                input
              >
                <CustomSelect.Option value={2}>{t.network_public}</CustomSelect.Option>
                <CustomSelect.Option value={0}>{t.network_private}</CustomSelect.Option>
              </CustomSelect>
            </Field>
            <div>
              <Saklar
                label={t.guest_all}
                nilai={nilai.guest_view_all_features}
                onUbah={(v) => ubah({ guest_view_all_features: v })}
              />
              <p className="text-11 text-tertiary">{t.guest_all_note}</p>
            </div>
          </Bagian>

          <Bagian title={t.group_automation} note={t.automation_note}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t.timezone}>
                <CustomSearchSelect
                  value={nilai.timezone}
                  label={opsiZona.find((z) => z.value === nilai.timezone)?.label ?? nilai.timezone}
                  onChange={(v: string) => ubah({ timezone: v })}
                  buttonClassName="w-full"
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
              <div />
              <PilihBulan label={t.archive_in} nilai={nilai.archive_in} onUbah={(v) => ubah({ archive_in: v })} />
              <PilihBulan label={t.close_in} nilai={nilai.close_in} onUbah={(v) => ubah({ close_in: v })} />
            </div>
          </Bagian>

          <div className="flex flex-wrap items-center gap-3 border-t border-subtle pt-4">
            <Button variant="primary" size="base" disabled={!isDirty || isSaving} onClick={() => void simpan()}>
              {t.save}
            </Button>
            <Button
              variant="secondary"
              size="base"
              disabled={isSaving || sama(nilai, data.pabrik)}
              onClick={() => setDraf(data.pabrik)}
            >
              {t.reset}
            </Button>
            {isDirty && <span className="text-11 text-warning-primary">{t.unsaved}</span>}
          </div>
          <p className="text-11 text-tertiary">{t.existing_note}</p>
        </div>
      )}
    </PageWrapper>
  );
}

export const meta: Route.MetaFunction = () => [{ title: "New project defaults - God Mode" }];

export default BawaanProjectPage;
