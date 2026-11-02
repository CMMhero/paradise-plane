/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isGroupByAvailable, isOrderByAvailable } from "@plane/constants";
import type { IIssueDisplayFilterOptions } from "@plane/types";

/**
 * Kustomisasi Paradise: group/sub-group/order by milik modul yang dimatikan di
 * God Mode (mis. Cycle, Module, Estimate) diganti bawaan. Tanpa ini filter yang
 * tersimpan sebelum modulnya dimatikan tetap mengelompokkan per cycle.
 */
export const getEnabledDisplayFilters = (displayFilters: IIssueDisplayFilterOptions): IIssueDisplayFilterOptions => {
  const groupByOk = isGroupByAvailable(displayFilters.group_by);
  const subGroupByOk = isGroupByAvailable(displayFilters.sub_group_by);
  const orderByOk = isOrderByAvailable(displayFilters.order_by);
  if (groupByOk && subGroupByOk && orderByOk) return displayFilters;
  return {
    ...displayFilters,
    ...(groupByOk ? {} : { group_by: "state" }),
    ...(subGroupByOk && groupByOk ? {} : { sub_group_by: null }),
    ...(orderByOk ? {} : { order_by: "-created_at" }),
  };
};
