/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TCoreCustomComponentsMetaData = {
  file_assets: {
    id: string;
    name: string;
    url: string;
  }[];
  user_mentions: {
    id: string;
    display_name: string;
    url: string;
  }[];
  /** Paradise (KEP-91): #kanal dan #work item yang labelnya diketahui (tanpa `#`). */
  reference_mentions?: {
    id: string;
    label: string;
    url: string;
  }[];
};

export type TExtendedCustomComponentsMetaData = unknown;

export type TCustomComponentsMetaData = TCoreCustomComponentsMetaData & TExtendedCustomComponentsMetaData;
