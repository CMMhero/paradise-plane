/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { omit } from "lodash-es";
// plane imports
import { API_BASE_URL } from "@plane/constants";
import type { TIssueParams } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export type TWorkItemListParams = Partial<Record<TIssueParams, string | boolean | undefined>>;

export type TWorkItemExportError = {
  code?: "EXPORT_TOO_LARGE";
  limit?: number;
};

/** Params that page, group, or draw a list. The file holds the whole list, ungrouped. */
const LIST_ONLY_PARAMS: TIssueParams[] = [
  "cursor",
  "per_page",
  "group_by",
  "sub_group_by",
  "layout",
  "expand",
  "show_empty_groups",
];

/** With `responseType: "blob"`, the JSON body of an error also arrives as a blob. */
const readExportError = async (body: unknown): Promise<TWorkItemExportError> => {
  if (!(body instanceof Blob)) return {};
  try {
    return JSON.parse(await body.text()) as TWorkItemExportError;
  } catch {
    return {};
  }
};

export class WorkItemExportService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /**
   * Download a work item list as .xlsx. Rejects with a `TWorkItemExportError`.
   * @param path export route of the list
   * @param listParams the filter and order params the list itself sends
   * @param exportName prefix of the file name
   */
  async downloadXlsx(
    path: string,
    listParams: TWorkItemListParams,
    exportName: string
  ): Promise<{ file: Blob; fileName: string }> {
    return this.get(
      path,
      { params: { ...omit(listParams, LIST_ONLY_PARAMS), export_name: exportName } },
      { responseType: "blob" }
    )
      .then((response) => ({
        file: response.data as Blob,
        fileName: /filename="([^"]+)"/.exec(response.headers["content-disposition"] ?? "")?.[1] ?? "work-items.xlsx",
      }))
      .catch(async (error) => {
        throw await readExportError(error?.response?.data);
      });
  }
}
