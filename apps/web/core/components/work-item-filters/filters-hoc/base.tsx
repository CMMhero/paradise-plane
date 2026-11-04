/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useMemo } from "react";
import { observer } from "mobx-react";
import { v4 as uuidv4 } from "uuid";
// plane imports
import type { TSaveViewOptions, TUpdateViewOptions } from "@plane/constants";
import type { IWorkItemFilterInstance } from "@plane/shared-state";
import type { IIssueFilters, TWorkItemFilterExpression } from "@plane/types";
// store hooks
import { useWorkItemFilters } from "@/hooks/store/work-item-filters/use-work-item-filters";
// plane web imports
import type { TWorkItemFiltersEntityProps } from "@/hooks/work-item-filters/use-work-item-filters-config";
import { useWorkItemFiltersConfig } from "@/hooks/work-item-filters/use-work-item-filters-config";
// local imports
import type { TSharedWorkItemFiltersHOCProps, TSharedWorkItemFiltersProps } from "./shared";

type TAdditionalWorkItemFiltersProps = {
  saveViewOptions?: TSaveViewOptions<TWorkItemFilterExpression>;
  updateViewOptions?: TUpdateViewOptions<TWorkItemFilterExpression>;
} & TWorkItemFiltersEntityProps;

type TWorkItemFiltersHOCProps = TSharedWorkItemFiltersHOCProps & TAdditionalWorkItemFiltersProps;

export const WorkItemFiltersHOC = observer(function WorkItemFiltersHOC(props: TWorkItemFiltersHOCProps) {
  const { children, initialWorkItemFilters } = props;

  // Only initialize filter instance when initial work item filters are defined
  if (!initialWorkItemFilters)
    return <>{typeof children === "function" ? children({ filter: undefined }) : children}</>;

  return (
    <WorkItemFilterRoot {...props} initialWorkItemFilters={initialWorkItemFilters}>
      {children}
    </WorkItemFilterRoot>
  );
});

/** Jumlah WorkItemFilterRoot yang sedang memakai instance filter per kunci. */
const jumlahPemakaiFilter = new Map<string, number>();

type TWorkItemFilterProps = TSharedWorkItemFiltersProps &
  TAdditionalWorkItemFiltersProps & {
    initialWorkItemFilters: IIssueFilters;
    children: React.ReactNode | ((props: { filter: IWorkItemFilterInstance }) => React.ReactNode);
  };

const WorkItemFilterRoot = observer(function WorkItemFilterRoot(props: TWorkItemFilterProps) {
  const {
    children,
    entityType,
    entityId,
    filtersToShowByLayout,
    initialWorkItemFilters,
    isTemporary,
    saveViewOptions,
    updateFilters,
    updateViewOptions,
    showOnMount,
    ...entityConfigProps
  } = props;
  // store hooks
  const { getOrCreateFilter, deleteFilter } = useWorkItemFilters();
  // derived values
  const workItemEntityID = useMemo(
    () => (isTemporary ? `TEMP-${entityId ?? uuidv4()}` : entityId),
    [isTemporary, entityId]
  );
  // memoize initial values to prevent re-computations when reference changes
  const initialUserFilters = useMemo(() => initialWorkItemFilters.richFilters, [initialWorkItemFilters]);
  const workItemFiltersConfig = useWorkItemFiltersConfig({
    allowedFilters: filtersToShowByLayout ? filtersToShowByLayout : [],
    ...entityConfigProps,
  });
  // get or create filter instance
  const workItemLayoutFilter = useMemo(
    () =>
      getOrCreateFilter({
        entityType,
        entityId: workItemEntityID,
        initialExpression: initialUserFilters,
        onExpressionChange: updateFilters,
        expressionOptions: {
          saveViewOptions,
          updateViewOptions,
        },
        showOnMount,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [entityType, workItemEntityID, saveViewOptions, updateViewOptions, updateFilters]
  );

  // Hapus instance filter saat komponen terakhir yang memakainya dilepas.
  // Dihitung per kunci dan penghapusannya ditunda satu tick: StrictMode (dev)
  // menjalankan cleanup lalu mount ulang tanpa membuat ulang useMemo, dan induk
  // bisa me-remount dengan kunci yang sama. Penghapusan langsung membuat instance
  // yang baru diambil komponen berikutnya ikut hilang dari store.
  useEffect(() => {
    const key = `${entityType}-${workItemEntityID}`;
    jumlahPemakaiFilter.set(key, (jumlahPemakaiFilter.get(key) ?? 0) + 1);
    return () => {
      jumlahPemakaiFilter.set(key, (jumlahPemakaiFilter.get(key) ?? 1) - 1);
      setTimeout(() => {
        if ((jumlahPemakaiFilter.get(key) ?? 0) > 0) return;
        jumlahPemakaiFilter.delete(key);
        deleteFilter(entityType, workItemEntityID);
      }, 0);
    };
  }, [deleteFilter, entityType, workItemEntityID]);

  useEffect(() => {
    workItemLayoutFilter.configManager.setAreConfigsReady(workItemFiltersConfig.areAllConfigsInitialized);
    workItemLayoutFilter.configManager.registerAll(workItemFiltersConfig.configs);
  }, [
    workItemFiltersConfig.areAllConfigsInitialized,
    workItemFiltersConfig.configs,
    workItemLayoutFilter.configManager,
  ]);

  return <>{typeof children === "function" ? children({ filter: workItemLayoutFilter }) : children}</>;
});
