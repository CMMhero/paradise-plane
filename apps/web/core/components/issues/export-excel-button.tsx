/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { FileSpreadsheet, LoaderCircle } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { EIssuesStoreType } from "@plane/types";
import { cn } from "@plane/utils";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useUserPermissions } from "@/hooks/store/user";
// services
import type { TWorkItemExportError } from "@/services/work-item-export.service";
import { WorkItemExportService } from "@/services/work-item-export.service";

const workItemExportService = new WorkItemExportService();

/** The list to export. `entityId` is the id its filter store is keyed by. */
export type TWorkItemExportTarget =
  | {
      /** `entityId`: project id, workspace view id, or user id. */
      storeType: EIssuesStoreType.PROJECT | EIssuesStoreType.GLOBAL | EIssuesStoreType.PROFILE;
      entityId: string;
    }
  | {
      /** `entityId`: module id or department view id. */
      storeType: EIssuesStoreType.MODULE | EIssuesStoreType.PROJECT_VIEW;
      entityId: string;
      projectId: string;
    };

const getExportPath = (workspaceSlug: string, target: TWorkItemExportTarget): string => {
  const workspace = `/api/workspaces/${workspaceSlug}`;
  switch (target.storeType) {
    case EIssuesStoreType.PROJECT:
      return `${workspace}/projects/${target.entityId}/issues/export-xlsx/`;
    // Module and department view pages list through the department endpoint.
    case EIssuesStoreType.MODULE:
    case EIssuesStoreType.PROJECT_VIEW:
      return `${workspace}/projects/${target.projectId}/issues/export-xlsx/`;
    case EIssuesStoreType.GLOBAL:
      return `${workspace}/issues/export-xlsx/`;
    case EIssuesStoreType.PROFILE:
      return `${workspace}/user-issues/${target.entityId}/export-xlsx/`;
  }
};

const saveFile = (file: Blob, fileName: string) => {
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

type Props = {
  target: TWorkItemExportTarget;
  /** Title of the list, used as the start of the file name. */
  exportName: string | undefined;
  /** `header`: icon, with the label on wide headers. `icon`: icon only. `bar`: a cell of a mobile toolbar. */
  appearance?: "header" | "icon" | "bar";
};

export const ExportExcelButton = observer(function ExportExcelButton(props: Props) {
  const { target, exportName, appearance = "header" } = props;
  // router
  const { workspaceSlug } = useParams();
  // i18n
  const { t } = useTranslation();
  // store hooks
  const { allowPermissions } = useUserPermissions();
  const { issuesFilter } = useIssues(target.storeType);
  const { issues: profileIssues } = useIssues(EIssuesStoreType.PROFILE);
  // states
  const [isExporting, setIsExporting] = useState(false);

  // The server refuses workspace guests.
  const canExport = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE
  );
  if (!workspaceSlug || !canExport) return null;

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const listParams = issuesFilter.getFilterParams(
        { canGroup: false, perPageCount: 1 },
        target.entityId,
        undefined,
        undefined,
        undefined
      );
      const { file, fileName } = await workItemExportService.downloadXlsx(
        getExportPath(workspaceSlug.toString(), target),
        target.storeType === EIssuesStoreType.PROFILE
          ? profileIssues.getViewParams(listParams, target.entityId)
          : listParams,
        exportName ?? ""
      );
      saveFile(file, fileName);
    } catch (error) {
      const { code, limit } = error as TWorkItemExportError;
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("work_item_export.failed_title"),
        message:
          code === "EXPORT_TOO_LARGE"
            ? t("work_item_export.too_large", { limit })
            : t("work_item_export.failed_message"),
      });
    } finally {
      setIsExporting(false);
    }
  };

  const label = isExporting ? t("work_item_export.exporting") : t("work_item_export.button");
  // Before the saved filters load, an export would ignore them.
  const isDisabled = isExporting || !issuesFilter.issueFilters;
  const Icon = isExporting ? LoaderCircle : FileSpreadsheet;
  const iconClassName = cn("size-3.5 shrink-0", { "animate-spin": isExporting });

  if (appearance === "bar")
    return (
      <button
        type="button"
        onClick={handleExport}
        disabled={isDisabled}
        aria-busy={isExporting}
        aria-label={label}
        className="flex flex-grow items-center justify-center gap-1.5 border-l border-subtle text-13 text-secondary disabled:text-placeholder"
      >
        <Icon className={iconClassName} aria-hidden="true" />
        Excel
      </button>
    );

  return (
    <Button
      variant="secondary"
      size="lg"
      className="px-2"
      onClick={handleExport}
      disabled={isDisabled}
      aria-busy={isExporting}
      aria-label={label}
      title={label}
    >
      <Icon className={cn(iconClassName, { "@4xl:hidden": appearance === "header" })} aria-hidden="true" />
      {appearance === "header" && <span className="hidden @4xl:inline">{label}</span>}
    </Button>
  );
});
