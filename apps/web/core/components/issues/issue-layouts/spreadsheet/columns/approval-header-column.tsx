/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dropdown filter di header kolom Approval
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Kolom lain (State, Priority) punya dropdown urutan di header. Approval tidak
 * punya urutan di server, jadi dropdown-nya menyaring: Menunggu / Disetujui /
 * Ditolak / Tanpa. Ia membaca dan menulis kondisi `approval_status` pada filter
 * instance yang sama dengan baris filter di atas tabel, jadi chip filter,
 * parameter API (`approval_status__in`), dan dropdown ini selalu sepakat.
 */

import { CheckIcon, ChevronDownIcon, Stamp } from "lucide-react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { COLLECTION_OPERATOR, LOGICAL_OPERATOR } from "@plane/types";
import { CustomMenu, Row } from "@plane/ui";
// hooks
import { useWorkItemFilterInstance } from "@/hooks/store/work-item-filters/use-work-item-filter-instance";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";

const PROPERTY = "approval_status";

const OPSI = [
  { key: "menunggu", labelKey: "issue.approval.badge.pending" },
  { key: "disetujui", labelKey: "issue.approval.badge.approved" },
  { key: "ditolak", labelKey: "issue.approval.badge.rejected" },
  { key: "tanpa", labelKey: "common.none" },
] as const;

type TProps = { title: string; onClose: () => void };

export const ApprovalHeaderColumn = observer(function ApprovalHeaderColumn({ title, onClose }: TProps) {
  const { t } = useTranslation();
  const { projectId, cycleId, moduleId, viewId } = useParams();
  const storeType = useIssueStoreType();
  // Cycle, module, dan view menyimpan filternya di bawah id masing-masing; project di bawah project id.
  const entityId = (viewId ?? cycleId ?? moduleId ?? projectId)?.toString();
  const filter = useWorkItemFilterInstance(storeType, entityId);

  const kondisi = filter?.findFirstConditionByPropertyAndOperator(PROPERTY, COLLECTION_OPERATOR.IN);
  const dipilih = Array.isArray(kondisi?.value) ? (kondisi.value as string[]) : [];

  const handleToggle = (key: string) => {
    if (!filter) return;
    const berikut = dipilih.includes(key) ? dipilih.filter((k) => k !== key) : [...dipilih, key];
    if (kondisi) {
      // Daftar kosong menghapus kondisinya (perilaku `updateConditionValue`).
      filter.updateConditionValue(kondisi.id, berikut);
    } else if (berikut.length > 0) {
      filter.addCondition(
        LOGICAL_OPERATOR.AND,
        { property: PROPERTY, operator: COLLECTION_OPERATOR.IN, value: berikut },
        false
      );
    }
  };

  const judul = (
    <div className="flex items-center gap-1.5">
      <Stamp className="h-4 w-4 text-placeholder" aria-hidden />
      {title}
    </div>
  );

  // Tanpa filter instance (mis. halaman yang tidak memakai filter kaya): judul biasa.
  if (!filter) return <Row className="flex w-full items-center gap-1.5 py-2 text-13 text-secondary">{judul}</Row>;

  return (
    <CustomMenu
      customButtonClassName="clickable !w-full"
      customButtonTabIndex={-1}
      className="!w-full"
      customButton={
        <Row className="flex w-full cursor-pointer items-center justify-between gap-1.5 py-2 text-13 text-secondary hover:text-primary">
          {judul}
          <div className="ml-3 flex items-center gap-1">
            {dipilih.length > 0 && (
              <span className="rounded-control bg-layer-3 px-1.5 text-11 text-secondary">{dipilih.length}</span>
            )}
            <ChevronDownIcon className="h-3 w-3" aria-hidden="true" />
          </div>
        </Row>
      }
      onMenuClose={onClose}
      placement="bottom-start"
    >
      {OPSI.map((opsi) => {
        const aktif = dipilih.includes(opsi.key);
        return (
          <CustomMenu.MenuItem key={opsi.key} onClick={() => handleToggle(opsi.key)}>
            <div
              className={`flex items-center justify-between gap-3 px-1 ${aktif ? "text-primary" : "text-secondary hover:text-primary"}`}
            >
              <span>{t(opsi.labelKey)}</span>
              {aktif && <CheckIcon className="h-3 w-3" />}
            </div>
          </CustomMenu.MenuItem>
        );
      })}
    </CustomMenu>
  );
});
