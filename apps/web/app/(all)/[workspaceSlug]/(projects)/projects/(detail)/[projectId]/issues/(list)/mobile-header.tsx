/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { EIssueFilterType, ISSUE_DISPLAY_FILTERS_BY_PAGE } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { ChartNoAxesColumn, SlidersHorizontal } from "lucide-react";
import { Button } from "@plane/propel/button";
import type { IIssueDisplayFilterOptions, IIssueDisplayProperties } from "@plane/types";
import { EIssuesStoreType, EIssueLayoutTypes } from "@plane/types";
// components
import { WorkItemsModal } from "@/components/analytics/work-items/modal";
import { WorkItemFiltersToggle } from "@/components/work-item-filters/filters-toggle";
import {
  DisplayFiltersSelection,
  FiltersDropdown,
  MobileLayoutSelection,
} from "@/components/issues/issue-layouts/filters";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useProject } from "@/hooks/store/use-project";
import { useParadiseModules } from "@/hooks/use-paradise-module";

export const ProjectIssuesMobileHeader = observer(function ProjectIssuesMobileHeader() {
  // i18n
  const { t } = useTranslation();
  const [analyticsModal, setAnalyticsModal] = useState(false);
  const { workspaceSlug, projectId } = useParams();
  const { currentProjectDetails } = useProject();
  const { isModuleEnabled } = useParadiseModules();

  // store hooks
  const {
    issuesFilter: { issueFilters, updateFilters },
  } = useIssues(EIssuesStoreType.PROJECT);
  const activeLayout = issueFilters?.displayFilters?.layout;

  const handleLayoutChange = useCallback(
    (layout: EIssueLayoutTypes) => {
      if (!workspaceSlug || !projectId) return;
      updateFilters(workspaceSlug, projectId, EIssueFilterType.DISPLAY_FILTERS, { layout: layout });
    },
    [workspaceSlug, projectId, updateFilters]
  );

  const handleDisplayFilters = useCallback(
    (updatedDisplayFilter: Partial<IIssueDisplayFilterOptions>) => {
      if (!workspaceSlug || !projectId) return;
      updateFilters(workspaceSlug, projectId, EIssueFilterType.DISPLAY_FILTERS, updatedDisplayFilter);
    },
    [workspaceSlug, projectId, updateFilters]
  );

  const handleDisplayProperties = useCallback(
    (property: Partial<IIssueDisplayProperties>) => {
      if (!workspaceSlug || !projectId) return;
      updateFilters(workspaceSlug, projectId, EIssueFilterType.DISPLAY_PROPERTIES, property);
    },
    [workspaceSlug, projectId, updateFilters]
  );

  return (
    <>
      <WorkItemsModal
        isOpen={analyticsModal}
        onClose={() => setAnalyticsModal(false)}
        projectDetails={currentProjectDetails ?? undefined}
      />
      {/* Paradise: alat HP (tata letak, filter, tampilan, analitik) sekarang menumpang di
          baris header yang sama dengan tombol tambah (lihat IssuesHeader `mobileToolbar`),
          bukan baris ketiga sendiri. Barisnya tetap bisa digeser, jadi tak ada tombol
          yang terpotong di layar 320px. */}
      <div className="scrollbar-hide flex h-full min-w-0 items-center gap-2 overflow-x-auto md:hidden [&>*]:shrink-0">
        <MobileLayoutSelection
          layouts={[EIssueLayoutTypes.LIST, EIssueLayoutTypes.KANBAN, EIssueLayoutTypes.CALENDAR]}
          onChange={handleLayoutChange}
          activeLayout={activeLayout}
        />
        {/* Paradise: di layar sempit header desktop (yang memuat tombol filter) disembunyikan, jadi tombol filter dipasang di sini. */}
        <WorkItemFiltersToggle entityType={EIssuesStoreType.PROJECT} entityId={projectId?.toString() ?? ""} />
        <FiltersDropdown
          miniIcon={<SlidersHorizontal className="size-3.5" />}
          title={t("common.display")}
          placement="bottom-end"
        >
          <DisplayFiltersSelection
            layoutDisplayFiltersOptions={
              activeLayout ? ISSUE_DISPLAY_FILTERS_BY_PAGE.issues.layoutOptions[activeLayout] : undefined
            }
            displayFilters={issueFilters?.displayFilters ?? {}}
            handleDisplayFiltersUpdate={handleDisplayFilters}
            displayProperties={issueFilters?.displayProperties ?? {}}
            handleDisplayPropertiesUpdate={handleDisplayProperties}
            cycleViewDisabled={!currentProjectDetails?.cycle_view}
            moduleViewDisabled={!currentProjectDetails?.module_view}
          />
        </FiltersDropdown>

        {isModuleEnabled("analytics") && (
          <Button
            variant="secondary"
            size="lg"
            className="px-2"
            onClick={() => setAnalyticsModal(true)}
            aria-label={t("common.analytics")}
            title={t("common.analytics")}
          >
            <ChartNoAxesColumn className="size-3.5" aria-hidden="true" />
          </Button>
        )}
      </div>
    </>
  );
});
