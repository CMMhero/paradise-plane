/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: TPA (Tempat Pembuangan Akhir)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { RotateCcw, Trash2 } from "lucide-react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { InstanceTrashService, type TTrashItem, type TTrashType } from "@plane/services";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// types
import type { Route } from "./+types/page";

const trashService = new InstanceTrashService();

const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5", "s6"];

const JENIS: { value: TTrashType | ""; label: string }[] = [
  { value: "", label: "Semua jenis" },
  { value: "issue", label: "Work item" },
  { value: "page", label: "Halaman" },
  { value: "cycle", label: "Cycle" },
  { value: "module", label: "Module" },
];

const toastError = (err: unknown, fallback: string) => {
  const message = (err as { error?: string })?.error ?? fallback;
  setToast({ type: TOAST_TYPE.ERROR, title: "Gagal", message });
};

function formatWaktu(iso: string) {
  return new Date(iso).toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const TrashPage = function TrashPage(_props: Route.ComponentProps) {
  const [jenis, setJenis] = useState<TTrashType | "">("");
  const [sibuk, setSibuk] = useState<string | null>(null);

  const { data, isLoading, error, mutate } = useSWR(
    ["INSTANCE_TRASH", jenis],
    () => trashService.list(jenis || undefined),
    { revalidateOnFocus: false }
  );

  const handlePulihkan = async (item: TTrashItem) => {
    setSibuk(item.id);
    try {
      const hasil = await trashService.restore(item.type, item.id);
      await mutate();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Dipulihkan",
        message: `"${item.name}" kembali beserta ${Math.max((hasil?.restored_count ?? 1) - 1, 0)} objek terkait.`,
      });
    } catch (err) {
      toastError(err, "Tidak bisa memulihkan.");
    } finally {
      setSibuk(null);
    }
  };

  const handleBuang = async (item: TTrashItem) => {
    // Satu-satunya aksi tak terbalikkan di halaman ini, dan tombolnya
    // bersebelahan dengan "Pulihkan", konfirmasi wajib.
    const yakin = window.confirm(
      `Buang "${item.name}" secara permanen?\n\nTidak bisa dibatalkan, barang ini tidak akan bisa dipulihkan lagi, bahkan oleh Super Admin.`
    );
    if (!yakin) return;
    setSibuk(item.id);
    try {
      await trashService.purge(item.type, item.id);
      await mutate();
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Dibuang permanen", message: `"${item.name}" sudah tidak ada.` });
    } catch (err) {
      toastError(err, "Tidak bisa membuang permanen.");
    } finally {
      setSibuk(null);
    }
  };

  return (
    <PageWrapper
      size="lg"
      header={{
        title: "TPA, Tempat Pembuangan Akhir",
        description: `Semua barang terhapus dari seluruh project${
          data?.retention_days ? `, disimpan ${data.retention_days} hari` : ""
        }. Bisa dipulihkan atau dibuang permanen.`,
      }}
    >
      <div className="mx-4 flex items-center justify-between">
        <select
          value={jenis}
          onChange={(e) => setJenis(e.target.value as TTrashType | "")}
          className="focus:border-accent-primary rounded border border-subtle bg-layer-1 px-2 py-1.5 text-body-sm-regular text-primary outline-none"
        >
          {JENIS.map((j) => (
            <option key={j.value} value={j.value}>
              {j.label}
            </option>
          ))}
        </select>
        {data && <span className="text-body-sm-regular text-secondary">{data.results.length} barang</span>}
      </div>

      <div className="mx-4">
        {isLoading ? (
          <Loader className="space-y-2">
            {SKELETON_ROWS.map((k) => (
              <Loader.Item key={k} height="52px" />
            ))}
          </Loader>
        ) : error ? (
          <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
            Gagal memuat isi TPA.
          </div>
        ) : !data?.results.length ? (
          <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
            TPA kosong.
          </div>
        ) : (
          <div className="divide-y divide-subtle rounded border border-subtle">
            {data.results.map((item) => (
              <div key={`${item.type}-${item.id}`} className="flex items-center justify-between gap-4 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-body-sm-medium text-primary">{item.name}</p>
                  <p className="mt-0.5 text-11 text-secondary">
                    {item.type_label} · dibuang {formatWaktu(item.deleted_at)}
                    {item.deleted_by ? ` oleh ${item.deleted_by.display_name || item.deleted_by.email}` : ""}
                    {" · "}
                    <span className={item.days_left <= 3 ? "text-red-600 font-medium" : ""}>
                      sisa {item.days_left} hari
                    </span>
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={sibuk === item.id}
                    onClick={() => handlePulihkan(item)}
                  >
                    <RotateCcw className="size-3.5" /> Pulihkan
                  </Button>
                  <Button
                    variant="error-outline"
                    size="sm"
                    disabled={sibuk === item.id}
                    onClick={() => handleBuang(item)}
                  >
                    <Trash2 className="size-3.5" /> Buang permanen
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageWrapper>
  );
};

export default TrashPage;
