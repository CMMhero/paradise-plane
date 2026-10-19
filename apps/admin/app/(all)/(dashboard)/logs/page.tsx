/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: halaman jejak audit
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Fragment, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import {
  InstanceAuditLogService,
  type TAuditLogAction,
  type TAuditLogEntry,
  type TAuditLogFilter,
  type TAuditLogModel,
} from "@plane/services";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// types
import type { Route } from "./+types/page";

const auditLogService = new InstanceAuditLogService();

const MODELS: { value: TAuditLogModel | ""; label: string }[] = [
  { value: "", label: "Semua objek" },
  { value: "project", label: "Project" },
  { value: "projectmember", label: "Anggota project" },
  { value: "workspacemember", label: "Anggota workspace" },
  { value: "issue", label: "Work item" },
  { value: "page", label: "Halaman" },
];

const ACTIONS: { value: TAuditLogAction | ""; label: string }[] = [
  { value: "", label: "Semua aksi" },
  { value: "create", label: "Dibuat" },
  { value: "update", label: "Diubah" },
  { value: "delete", label: "Dihapus" },
];

const AKSI_WARNA: Record<string, string> = {
  Create: "bg-green-500/10 text-green-600",
  Update: "bg-amber-500/10 text-amber-600",
  Delete: "bg-red-500/10 text-red-600",
};

/** Kunci tetap untuk baris skeleton, index sebagai key ditolak lint. */
const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"];

const selectClass =
  "rounded border border-subtle bg-layer-1 px-2 py-1.5 text-body-sm-regular text-primary outline-none focus:border-accent-primary";

function formatWaktu(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Ubah {field: [lama, baru]} jadi baris yang bisa dibaca orang. */
function ringkasPerubahan(changes: TAuditLogEntry["changes"]) {
  if (!changes) return [];
  return Object.entries(changes).map(([field, nilai]) => {
    const [lama, baru] = Array.isArray(nilai) ? nilai : ["", String(nilai)];
    return { field, lama, baru };
  });
}

const LogsPage = function LogsPage(_props: Route.ComponentProps) {
  const [filter, setFilter] = useState<TAuditLogFilter>({ page: 1, per_page: 50 });
  const [dibuka, setDibuka] = useState<number | null>(null);

  const { data, isLoading, error } = useSWR(["INSTANCE_AUDIT_LOGS", filter], () => auditLogService.list(filter), {
    revalidateOnFocus: false,
  });

  const halaman = data?.page ?? 1;
  const totalHalaman = data?.total_pages ?? 1;

  // Mengubah filter WAJIB mengembalikan halaman ke 1. Kalau tidak, menyaring
  // dari halaman 7 bisa mendarat di hasil kosong padahal datanya ada.
  const ubahFilter = useMemo(
    () => (patch: Partial<TAuditLogFilter>) => {
      setDibuka(null);
      setFilter((f) => ({ ...f, ...patch, page: 1 }));
    },
    []
  );

  return (
    <PageWrapper
      size="lg"
      header={{
        title: "Jejak audit",
        description:
          "Siapa mengubah apa di seluruh instance. Hanya bisa dibaca dari sini, tidak tersedia di aplikasi utama.",
      }}
    >
      <div className="mx-4 flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={filter.search ?? ""}
          onChange={(e) => ubahFilter({ search: e.target.value })}
          placeholder="Cari objek atau email pelaku…"
          className={`${selectClass} min-w-[220px] flex-1`}
        />
        <select
          value={filter.model ?? ""}
          onChange={(e) => ubahFilter({ model: (e.target.value || undefined) as TAuditLogModel | undefined })}
          className={selectClass}
        >
          {MODELS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <select
          value={filter.action ?? ""}
          onChange={(e) => ubahFilter({ action: (e.target.value || undefined) as TAuditLogAction | undefined })}
          className={selectClass}
        >
          {ACTIONS.map((a) => (
            <option key={a.value} value={a.value}>
              {a.label}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={filter.date_from ?? ""}
          onChange={(e) => ubahFilter({ date_from: e.target.value || undefined })}
          className={selectClass}
          aria-label="Dari tanggal"
        />
        <input
          type="date"
          value={filter.date_to ?? ""}
          onChange={(e) => ubahFilter({ date_to: e.target.value || undefined })}
          className={selectClass}
          aria-label="Sampai tanggal"
        />
      </div>

      <div className="mx-4">
        {isLoading ? (
          <Loader className="space-y-2">
            {SKELETON_ROWS.map((k) => (
              <Loader.Item key={k} height="44px" />
            ))}
          </Loader>
        ) : error ? (
          <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
            Gagal memuat jejak audit.
          </div>
        ) : !data?.results.length ? (
          <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
            Tidak ada entri yang cocok dengan saringan ini.
          </div>
        ) : (
          <div className="overflow-x-auto rounded border border-subtle">
            <table className="w-full min-w-[820px] text-body-sm-regular">
              <thead className="bg-layer-1 text-secondary">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Waktu</th>
                  <th className="px-3 py-2 text-left font-medium">Pelaku</th>
                  <th className="px-3 py-2 text-left font-medium">Aksi</th>
                  <th className="px-3 py-2 text-left font-medium">Objek</th>
                  <th className="px-3 py-2 text-left font-medium">IP</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((e) => {
                  const perubahan = ringkasPerubahan(e.changes);
                  const terbuka = dibuka === e.id;
                  return (
                    // Fragment perlu key karena ini di dalam .map() dan tiap
                    // entri merender DUA baris; sintaks pendek <> tidak bisa
                    // membawa key.
                    <Fragment key={e.id}>
                      <tr
                        onClick={() => setDibuka(terbuka ? null : e.id)}
                        className="cursor-pointer border-t border-subtle hover:bg-layer-1"
                      >
                        <td className="px-3 py-2 whitespace-nowrap text-secondary">{formatWaktu(e.timestamp)}</td>
                        <td className="px-3 py-2">
                          {e.actor ? (
                            <span className="text-primary">{e.actor.display_name || e.actor.email}</span>
                          ) : (
                            // Entri tanpa aktor datang dari skrip shell, di situ
                            // memang tidak ada request, jadi bukan celah audit.
                            <span className="text-placeholder italic">skrip / sistem</span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`rounded px-2 py-0.5 text-11 ${AKSI_WARNA[e.action] ?? "bg-layer-1"}`}>
                            {e.action}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <span className="text-primary">{e.object_repr}</span>
                          <span className="ml-2 text-placeholder">{e.model}</span>
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap text-secondary">{e.remote_addr ?? "—"}</td>
                      </tr>
                      {terbuka && (
                        <tr className="border-t border-subtle bg-layer-1">
                          <td colSpan={5} className="px-3 py-3">
                            {perubahan.length === 0 ? (
                              <span className="text-secondary">Tidak ada rincian perubahan.</span>
                            ) : (
                              <div className="space-y-1">
                                {perubahan.map((p) => (
                                  <div key={p.field} className="flex flex-wrap gap-2">
                                    <span className="font-medium text-primary">{p.field}</span>
                                    <span className="text-red-600 line-through">{p.lama || "(kosong)"}</span>
                                    <span className="text-secondary">→</span>
                                    <span className="text-green-600">{p.baru || "(kosong)"}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data && data.count > 0 && (
        <div className="mx-4 flex items-center justify-between">
          <span className="text-body-sm-regular text-secondary">
            {data.count} entri · halaman {halaman} dari {totalHalaman}
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={halaman <= 1}
              onClick={() => setFilter((f) => ({ ...f, page: halaman - 1 }))}
            >
              <ChevronLeft className="size-4" /> Sebelumnya
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={halaman >= totalHalaman}
              onClick={() => setFilter((f) => ({ ...f, page: halaman + 1 }))}
            >
              Berikutnya <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      )}
    </PageWrapper>
  );
};

export default LogsPage;
