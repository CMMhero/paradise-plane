/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: urutan + filter di header kolom Approval
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bagian atas menu mengurutkan menurut status persetujuan TERBARU (server:
 * `order_issue_queryset`, kunci `approval_status`): menunggu, ditolak, disetujui,
 * tanpa persetujuan selalu di akhir. Bagian bawah menyaring: Menunggu / Disetujui /
 * Ditolak / Tanpa. Filter membaca dan menulis kondisi `approval_status` pada filter
 * instance yang sama dengan baris filter di atas tabel, jadi chip filter, parameter
 * API (`approval_status__in`), dan dropdown ini selalu sepakat.
 */

import {
  ArrowDownWideNarrow,
  ArrowUpNarrowWide,
  CheckIcon,
  ChevronDownIcon,
  Eraser,
  MoveRight,
  Stamp,
} from "lucide-react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TIssueOrderByOptions } from "@plane/types";
import { COLLECTION_OPERATOR, LOGICAL_OPERATOR } from "@plane/types";
import { CustomMenu, Row } from "@plane/ui";
import { cn } from "@plane/utils";
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

const URUT_NAIK: TIssueOrderByOptions = "approval_status";
const URUT_TURUN: TIssueOrderByOptions = "-approval_status";

const itemKelas = (aktif: boolean) =>
  cn("flex items-center justify-between gap-3 px-1", aktif ? "text-primary" : "text-secondary hover:text-primary");

type TProps = {
  title: string;
  onClose: () => void;
  orderBy: TIssueOrderByOptions | undefined;
  onOrderBy: (order: TIssueOrderByOptions) => void;
};

export const ApprovalHeaderColumn = observer(function ApprovalHeaderColumn({
  title,
  onClose,
  orderBy,
  onOrderBy,
}: TProps) {
  const { t } = useTranslation();
  const { projectId, cycleId, moduleId, viewId, globalViewId } = useParams();
  const storeType = useIssueStoreType();
  // Cycle, module, dan view menyimpan filternya di bawah id masing-masing; project di
  // bawah project id; halaman Views workspace di bawah globalViewId.
  const entityId = (viewId ?? globalViewId ?? cycleId ?? moduleId ?? projectId)?.toString();
  const filter = useWorkItemFilterInstance(storeType, entityId);

  const kondisi = filter?.findFirstConditionByPropertyAndOperator(PROPERTY, COLLECTION_OPERATOR.IN);
  const dipilih = Array.isArray(kondisi?.value) ? (kondisi.value as string[]) : [];
  const urutAktif = orderBy === URUT_NAIK || orderBy === URUT_TURUN;
  const labelMenunggu = t("issue.approval.badge.pending");
  const labelDisetujui = t("issue.approval.badge.approved");

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

  return (
    <CustomMenu
      customButtonClassName="clickable !w-full"
      customButtonTabIndex={-1}
      className="!w-full"
      customButton={
        <Row className="flex w-full cursor-pointer items-center justify-between gap-1.5 py-2 text-13 text-secondary hover:text-primary">
          <div className="flex items-center gap-1.5">
            <Stamp className="h-4 w-4 text-placeholder" aria-hidden />
            {title}
          </div>
          <div className="ml-3 flex items-center gap-1">
            {urutAktif &&
              (orderBy === URUT_NAIK ? (
                <ArrowDownWideNarrow className="h-3 w-3" aria-hidden />
              ) : (
                <ArrowUpNarrowWide className="h-3 w-3" aria-hidden />
              ))}
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
      <CustomMenu.MenuItem onClick={() => onOrderBy(URUT_NAIK)}>
        <div className={itemKelas(orderBy === URUT_NAIK)}>
          <div className="flex items-center gap-2">
            <ArrowDownWideNarrow className="h-3 w-3 stroke-[1.5]" />
            <span>{labelMenunggu}</span>
            <MoveRight className="h-3 w-3" />
            <span>{labelDisetujui}</span>
          </div>
          {orderBy === URUT_NAIK && <CheckIcon className="h-3 w-3" />}
        </div>
      </CustomMenu.MenuItem>
      <CustomMenu.MenuItem onClick={() => onOrderBy(URUT_TURUN)}>
        <div className={itemKelas(orderBy === URUT_TURUN)}>
          <div className="flex items-center gap-2">
            <ArrowUpNarrowWide className="h-3 w-3 stroke-[1.5]" />
            <span>{labelDisetujui}</span>
            <MoveRight className="h-3 w-3" />
            <span>{labelMenunggu}</span>
          </div>
          {orderBy === URUT_TURUN && <CheckIcon className="h-3 w-3" />}
        </div>
      </CustomMenu.MenuItem>
      {urutAktif && (
        <CustomMenu.MenuItem onClick={() => onOrderBy("-created_at")}>
          <div className="flex items-center gap-2 px-1 text-secondary hover:text-primary">
            <Eraser className="h-3 w-3" />
            <span>{t("common.actions.clear_sorting")}</span>
          </div>
        </CustomMenu.MenuItem>
      )}
      {/* Tanpa filter instance (mis. halaman yang tidak memakai filter kaya): urutan saja. */}
      {filter && (
        <>
          <hr className="my-1 border-subtle" />
          {OPSI.map((opsi) => {
            const aktif = dipilih.includes(opsi.key);
            return (
              <CustomMenu.MenuItem key={opsi.key} onClick={() => handleToggle(opsi.key)}>
                <div className={itemKelas(aktif)}>
                  <span>{t(opsi.labelKey)}</span>
                  {aktif && <CheckIcon className="h-3 w-3" />}
                </div>
              </CustomMenu.MenuItem>
            );
          })}
        </>
      )}
    </CustomMenu>
  );
});
