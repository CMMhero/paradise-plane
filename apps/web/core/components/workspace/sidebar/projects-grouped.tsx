/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sidebar project per divisi -> departemen (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { ChevronRightIcon } from "@plane/propel/icons";
import { cn } from "@plane/utils";
// services
import type { TStrukturOrganisasi } from "@/services/organisasi.service";
// local imports
import { SidebarProjectsListItem } from "./projects-list-item";

type Props = {
  struktur: TStrukturOrganisasi;
  /** Urutan project yang sudah diikuti (sumbernya store project, bukan endpoint struktur). */
  joinedProjectIds: string[];
  handleCopyText: (projectId: string) => void;
};

type TGrup = { id: string; nama: string; departemen: { id: string; nama: string; projectIds: string[] }[] };

/** Gabungkan struktur dengan project yang benar-benar ada di store; sisanya ke "Lainnya". */
function susunGrup(struktur: TStrukturOrganisasi, joinedProjectIds: string[]): TGrup[] {
  const terpakai = new Set<string>();
  const grup: TGrup[] = struktur.divisi
    .map((divisi) => ({
      id: divisi.id,
      nama: divisi.nama,
      departemen: divisi.departemen
        .map((dep) => {
          const projectIds = joinedProjectIds.filter((pid) => dep.project_ids.includes(pid));
          projectIds.forEach((pid) => terpakai.add(pid));
          return { id: dep.id, nama: dep.nama, projectIds };
        })
        .filter((dep) => dep.projectIds.length > 0),
    }))
    .filter((divisi) => divisi.departemen.length > 0);

  const sisa = joinedProjectIds.filter((pid) => !terpakai.has(pid));
  if (sisa.length > 0)
    grup.push({ id: "lainnya", nama: "Lainnya", departemen: [{ id: "lainnya", nama: "", projectIds: sisa }] });
  return grup;
}

export const SidebarProjectsGrouped = observer(function SidebarProjectsGrouped({
  struktur,
  joinedProjectIds,
  handleCopyText,
}: Props) {
  const [tertutup, setTertutup] = useState<Set<string>>(new Set());
  const grup = susunGrup(struktur, joinedProjectIds);

  const toggle = (id: string) =>
    setTertutup((lama) => {
      const baru = new Set(lama);
      if (baru.has(id)) baru.delete(id);
      else baru.add(id);
      return baru;
    });

  return (
    <div className="flex flex-col gap-1">
      {grup.map((divisi) => {
        const terbuka = !tertutup.has(divisi.id);
        return (
          <div key={divisi.id} className="flex flex-col">
            <button
              type="button"
              onClick={() => toggle(divisi.id)}
              aria-expanded={terbuka}
              className="flex w-full items-center gap-1 rounded-sm px-2 py-1 text-left text-11 font-semibold tracking-wide text-placeholder uppercase hover:bg-layer-transparent-hover"
            >
              <ChevronRightIcon className={cn("size-3 flex-shrink-0 transition-transform", { "rotate-90": terbuka })} />
              <span className="truncate">{divisi.nama}</span>
            </button>
            {terbuka &&
              divisi.departemen.map((dep) => (
                <div key={dep.id} className="flex flex-col gap-0.5 pl-2">
                  {dep.nama && <span className="truncate px-2 pt-1 text-11 font-medium text-tertiary">{dep.nama}</span>}
                  {/* Seret-urut dimatikan: urutan lintas grup tidak punya arti di sini. */}
                  {dep.projectIds.map((projectId, index) => (
                    <SidebarProjectsListItem
                      key={projectId}
                      projectId={projectId}
                      handleCopyText={() => handleCopyText(projectId)}
                      projectListType="JOINED"
                      disableDrag
                      disableDrop
                      isLastChild={index === dep.projectIds.length - 1}
                    />
                  ))}
                </div>
              ))}
          </div>
        );
      })}
    </div>
  );
});
