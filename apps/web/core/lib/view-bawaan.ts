/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: view bawaan di tiap departemen
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * All work items, Assigned, Created, dan Subscribed tampil di halaman Views
 * workspace DAN di Views tiap departemen. Di departemen keempatnya bukan baris
 * database: id-nya kunci statis (`assigned`, dst.), view-nya dibangun di web, dan
 * syarat "milik saya" ditambahkan ke parameter API (sama dengan view workspace).
 */

import { DEFAULT_GLOBAL_VIEWS_LIST } from "@plane/constants";
import type { IProjectView, TStaticViewTypes } from "@plane/types";
import { EViewAccess, STATIC_VIEW_TYPES } from "@plane/types";

export type TViewBawaan = (typeof DEFAULT_GLOBAL_VIEWS_LIST)[number];

/** True untuk id view bawaan (`all-issues`, `assigned`, `created`, `subscribed`). */
export const isViewBawaan = (viewId: string | undefined | null): viewId is TStaticViewTypes =>
  !!viewId && STATIC_VIEW_TYPES.includes(viewId);

export const getViewBawaan = (viewId: string | undefined | null): TViewBawaan | undefined =>
  DEFAULT_GLOBAL_VIEWS_LIST.find((view) => view.key === viewId);

/** Tautan view bawaan: di departemen kalau ada `projectId`, selain itu di halaman Views workspace. */
export const getTautanViewBawaan = (workspaceSlug: string, key: TStaticViewTypes, projectId?: string): string =>
  projectId ? `/${workspaceSlug}/projects/${projectId}/views/${key}` : `/${workspaceSlug}/workspace-views/${key}`;

/**
 * View departemen tiruan untuk kunci statis. `name` sengaja kosong: tampilan
 * memakai label terjemahan (`getViewBawaan(id).i18n_label`), bukan nama ini.
 */
export const buatViewBawaanDepartemen = (key: TStaticViewTypes, projectId: string, workspaceId = ""): IProjectView => {
  const sekarang = new Date(0);
  return {
    id: key,
    name: "",
    description: "",
    access: EViewAccess.PUBLIC,
    created_at: sekarang,
    updated_at: sekarang,
    is_favorite: false,
    created_by: "",
    updated_by: "",
    owned_by: "",
    rich_filters: {},
    display_filters: {},
    display_properties: {},
    query: {},
    query_data: {},
    project: projectId,
    workspace: workspaceId,
    logo_props: undefined,
    is_locked: false,
  };
};
