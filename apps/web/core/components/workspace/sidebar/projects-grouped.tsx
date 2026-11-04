/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sidebar project per divisi (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
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

/**
 * Satu label grup saja: nama divisi. Project sudah khusus per departemen, jadi
 * label departemen di atasnya hanya mengulang nama project.
 */
type TGrup = {
  id: string;
  nama: string;
  projectIds: string[];
};

/** Gabungkan struktur dengan project yang benar-benar ada di store; sisanya ke "Lainnya". */
function susunGrup(struktur: TStrukturOrganisasi, joinedProjectIds: string[], namaLainnya: string): TGrup[] {
  const terpakai = new Set<string>();
  const grup: TGrup[] = struktur.divisi
    .map((divisi) => {
      const milikDivisi = new Set(divisi.departemen.flatMap((dep) => dep.project_ids));
      const projectIds = joinedProjectIds.filter((pid) => milikDivisi.has(pid) && !terpakai.has(pid));
      projectIds.forEach((pid) => terpakai.add(pid));
      return { id: divisi.id, nama: divisi.nama, projectIds };
    })
    .filter((divisi) => divisi.projectIds.length > 0);

  const sisa = joinedProjectIds.filter((pid) => !terpakai.has(pid));
  if (sisa.length > 0) grup.push({ id: "lainnya", nama: namaLainnya, projectIds: sisa });
  return grup;
}

export const SidebarProjectsGrouped = observer(function SidebarProjectsGrouped({
  struktur,
  joinedProjectIds,
  handleCopyText,
}: Props) {
  const { t } = useTranslation();
  const [tertutup, setTertutup] = useState<Set<string>>(new Set());
  const grup = susunGrup(struktur, joinedProjectIds, t("other"));

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
              className="flex w-full items-center gap-1 rounded-item px-2 py-1.5 text-left text-caption-md-medium text-tertiary hover:bg-layer-transparent-hover sentuh:py-2.5"
            >
              <ChevronRightIcon className={cn("size-3 flex-shrink-0 transition-transform", { "rotate-90": terbuka })} />
              <span className="truncate">{divisi.nama}</span>
            </button>
            {terbuka && (
              <div className="flex flex-col gap-0.5 pl-2">
                {/* Seret-urut dimatikan: urutan lintas grup tidak punya arti di sini. */}
                {divisi.projectIds.map((projectId, index) => (
                  <SidebarProjectsListItem
                    key={projectId}
                    projectId={projectId}
                    handleCopyText={() => handleCopyText(projectId)}
                    projectListType="JOINED"
                    disableDrag
                    disableDrop
                    isLastChild={index === divisi.projectIds.length - 1}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
});
