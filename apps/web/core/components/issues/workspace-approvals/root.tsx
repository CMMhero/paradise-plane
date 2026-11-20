/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: halaman Persetujuan workspace
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Keputusan user 2026-11-20: semua yang menunggu keputusan saya, dari semua
 * departemen yang saya awasi, dikelompokkan divisi lalu departemen. Saringan
 * jenis dan departemen hanya di klien: balasannya sudah kecil (hanya baris yang
 * boleh saya putuskan).
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { ArrowLeftRight } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Banner } from "@plane/propel/banner";
import { Button } from "@plane/propel/button";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { CustomSelect, EHeaderVariant, Header } from "@plane/ui";
// components
import { ListLayout } from "@/components/core/list";
import { ViewListLoader } from "@/components/ui/loader/view-list-loader";
// hooks
import { useAppRouter } from "@/hooks/use-app-router";
// services
import type { TBarisAntreanWorkspace } from "@/services/persetujuan.service";
// local imports
import { pesanGagalPersetujuan } from "../approval-actions";
import { WorkspaceApprovalRow } from "./row";
import { useAntreanWorkspace } from "./use-antrean-workspace";

type TSaringJenis = "semua" | TBarisAntreanWorkspace["jenis"];

const LABEL_JENIS: Record<TSaringJenis, string> = {
  semua: "persetujuan_p29.filter_all_types",
  selesai: "persetujuan_p29.type_completion",
  permintaan: "persetujuan_p29.type_request",
};

type TKelompok = { id: string; nama: string; baris: TBarisAntreanWorkspace[] };
type TKelompokDivisi = TKelompok & { departemen: TKelompok[] };

/** Urut nama; kelompok tanpa id (belum masuk struktur) paling akhir. */
const urut = (a: TKelompok, b: TKelompok) => Number(a.id === "") - Number(b.id === "") || a.nama.localeCompare(b.nama);

/** Divisi > departemen. */
const kelompokkan = (baris: TBarisAntreanWorkspace[]): TKelompokDivisi[] => {
  const divisi = new Map<string, TKelompokDivisi>();
  for (const b of baris) {
    const kunciDivisi = b.divisi?.id ?? "";
    const d = divisi.get(kunciDivisi) ?? { id: kunciDivisi, nama: b.divisi?.nama ?? "", baris: [], departemen: [] };
    divisi.set(kunciDivisi, d);
    d.baris.push(b);
    const kunciDepartemen = b.departemen?.id ?? b.project.id;
    let dep = d.departemen.find((x) => x.id === kunciDepartemen);
    if (!dep) {
      dep = { id: kunciDepartemen, nama: b.departemen?.nama ?? b.project.name, baris: [] };
      d.departemen.push(dep);
    }
    dep.baris.push(b);
  }
  const hasil = [...divisi.values()];
  for (const d of hasil) {
    // oxlint-disable-next-line unicorn/no-array-sort -- apps/web lib is ES2022 (no toSorted); local array
    d.departemen.sort(urut);
  }
  // oxlint-disable-next-line unicorn/no-array-sort -- apps/web lib is ES2022 (no toSorted); fresh array
  return hasil.sort(urut);
};

export const AntreanPersetujuanWorkspace = observer(function AntreanPersetujuanWorkspace(props: {
  workspaceSlug: string;
}) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  const router = useAppRouter();
  const { data, error, mutate } = useAntreanWorkspace(workspaceSlug);
  const [jenis, setJenis] = useState<TSaringJenis>("semua");
  const [departemen, setDepartemen] = useState("");

  const semua = data?.hasil ?? [];
  const pilihanDepartemen = kelompokkan(semua).flatMap((d) => d.departemen);
  const tersaring = semua.filter(
    (b) =>
      (jenis === "semua" || b.jenis === jenis) && (!departemen || (b.departemen?.id ?? b.project.id) === departemen)
  );
  const namaDepartemen = pilihanDepartemen.find((d) => d.id === departemen)?.nama;

  const isi = () => {
    if (error)
      return (
        <div className="px-page-x py-4">
          <Banner
            variant="error"
            title={pesanGagalPersetujuan(error, t("persetujuan_p29.load_failed"))}
            action={
              <Button variant="secondary" size="base" onClick={() => void mutate()}>
                {t("issue.approval.actions.retry")}
              </Button>
            }
          />
        </div>
      );
    if (!data) return <ViewListLoader />;
    if (tersaring.length === 0)
      return (
        <div className="grid h-full w-full place-items-center">
          <EmptyStateCompact
            assetKey="intake"
            title={semua.length === 0 ? t("persetujuan_p29.empty_title") : t("persetujuan_p29.empty_filtered")}
            description={semua.length === 0 ? t("persetujuan_p29.empty_description") : undefined}
          />
        </div>
      );
    return (
      <div className="h-full overflow-y-auto">
        {kelompokkan(tersaring).map((d) => (
          <section key={d.id || "tanpa-divisi"} aria-label={d.nama || t("persetujuan_p29.no_division")}>
            <h2 className="flex items-center gap-2 border-b border-subtle bg-layer-1 px-page-x py-2 text-13 font-semibold text-primary">
              {d.nama || t("persetujuan_p29.no_division")}
              <span className="rounded-control bg-layer-3 px-1.5 text-11 text-secondary">{d.baris.length}</span>
            </h2>
            {d.departemen.map((dep) => (
              <div key={dep.id}>
                <h3 className="flex items-center gap-2 px-page-x pt-3 pb-1 text-12 font-medium text-secondary">
                  {dep.nama}
                  <span className="text-tertiary">{dep.baris.length}</span>
                </h3>
                <ListLayout>
                  {dep.baris.map((b) => (
                    <WorkspaceApprovalRow key={`${b.jenis}-${b.id}`} workspaceSlug={workspaceSlug} baris={b} />
                  ))}
                </ListLayout>
              </div>
            ))}
          </section>
        ))}
      </div>
    );
  };

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden">
      <Header variant={EHeaderVariant.SECONDARY}>
        <Header.LeftItem>
          <div className="flex flex-wrap items-center gap-2">
            <CustomSelect
              value={jenis}
              onChange={(v: TSaringJenis) => setJenis(v)}
              label={t(LABEL_JENIS[jenis])}
              buttonClassName="text-13"
            >
              {(Object.keys(LABEL_JENIS) as TSaringJenis[]).map((k) => (
                <CustomSelect.Option key={k} value={k}>
                  {t(LABEL_JENIS[k])}
                </CustomSelect.Option>
              ))}
            </CustomSelect>
            <CustomSelect
              value={departemen}
              onChange={(v: string) => setDepartemen(v)}
              label={namaDepartemen ?? t("persetujuan_p29.filter_all_departments")}
              buttonClassName="text-13"
            >
              <CustomSelect.Option value="">{t("persetujuan_p29.filter_all_departments")}</CustomSelect.Option>
              {pilihanDepartemen.map((d) => (
                <CustomSelect.Option key={d.id} value={d.id}>
                  {d.nama}
                </CustomSelect.Option>
              ))}
            </CustomSelect>
          </div>
        </Header.LeftItem>
        <Header.RightItem>
          <Button
            variant="secondary"
            size="base"
            prependIcon={<ArrowLeftRight className="size-3.5" aria-hidden />}
            onClick={() => router.push(`/${workspaceSlug}/tugas-lintas-divisi/`)}
          >
            {t("persetujuan_p29.request_work")}
          </Button>
        </Header.RightItem>
      </Header>
      <div className="relative h-full w-full overflow-hidden">{isi()}</div>
    </div>
  );
});
