/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: filter status persetujuan (KEP-25)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TFilterProperty, TSupportedOperators } from "@plane/types";
import { COLLECTION_OPERATOR, EQUALITY_OPERATOR } from "@plane/types";
// local imports
import type { IFilterIconConfig, TCreateFilterConfig, TCreateFilterConfigParams } from "../../../rich-filters";
import { createFilterConfig, createOperatorConfigEntry, getMultiSelectConfig } from "../../../rich-filters";

// ------------ Approval status filter ------------

/**
 * Status values as stored by the API (`PersetujuanPenugasan.status`), plus the
 * filter-only value `tanpa` (work item that never needed approval).
 */
export type TApprovalStatusKey = "menunggu" | "disetujui" | "ditolak" | "tanpa";

export type TApprovalStatusOption = { key: TApprovalStatusKey; label: string };

/**
 * Approval status filter specific params. Labels come from the caller so they
 * can be translated; the keys are the API vocabulary.
 */
export type TCreateApprovalStatusFilterParams = TCreateFilterConfigParams &
  IFilterIconConfig<TApprovalStatusKey> & {
    label: string;
    options: TApprovalStatusOption[];
  };

export const getApprovalStatusMultiSelectConfig = (
  params: TCreateApprovalStatusFilterParams,
  singleValueOperator: TSupportedOperators
) =>
  getMultiSelectConfig<TApprovalStatusOption, TApprovalStatusKey, TApprovalStatusKey>(
    {
      items: params.options,
      getId: (option) => option.key,
      getLabel: (option) => option.label,
      getValue: (option) => option.key,
      getIconData: (option) => option.key,
    },
    {
      singleValueOperator,
      ...params,
    },
    {
      getOptionIcon: params.getOptionIcon,
    }
  );

export const getApprovalStatusFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateApprovalStatusFilterParams> =>
  (params: TCreateApprovalStatusFilterParams) =>
    createFilterConfig<P>({
      id: key,
      ...params,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(COLLECTION_OPERATOR.IN, params, (updatedParams) =>
          getApprovalStatusMultiSelectConfig(updatedParams, EQUALITY_OPERATOR.EXACT)
        ),
      ]),
    });
