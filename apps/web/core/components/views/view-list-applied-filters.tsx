/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Chip filter aktif daftar view. Dipindah dari halaman Views departemen supaya
 * halaman Views workspace memakai bilah yang sama (Kustomisasi Paradise).
 */

import { useCallback } from "react";
import { observer } from "mobx-react";
// plane imports
import type { EViewAccess, TViewFilterProps } from "@plane/types";
import { Header, EHeaderVariant } from "@plane/ui";
import { calculateTotalFilters } from "@plane/utils";
// hooks
import { useProjectView } from "@/hooks/store/use-project-view";
// local imports
import { ViewAppliedFiltersList } from "./applied-filters";

export const ViewListAppliedFilters = observer(function ViewListAppliedFilters() {
  const { filters, updateFilters, clearAllFilters } = useProjectView();

  const handleRemoveFilter = useCallback(
    (key: keyof TViewFilterProps, value: string | EViewAccess | null) => {
      let newValues = filters.filters?.[key];

      if (key === "favorites") {
        newValues = !!value;
      }
      if (Array.isArray(newValues)) {
        if (!value) newValues = [];
        else newValues = newValues.filter((val) => val !== value) as string[];
      }

      updateFilters("filters", { [key]: newValues });
    },
    [filters.filters, updateFilters]
  );

  if (calculateTotalFilters(filters?.filters ?? {}) === 0) return null;

  return (
    <Header variant={EHeaderVariant.TERNARY}>
      <ViewAppliedFiltersList
        appliedFilters={filters.filters ?? {}}
        handleClearAllFilters={clearAllFilters}
        handleRemoveFilter={handleRemoveFilter}
        alwaysAllowEditing
      />
    </Header>
  );
});
