/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TLogoProps } from "./common";
import type { TIssuePriorities } from "./issues";

export type TRecentActivityFilterKeys = "all item" | "issue" | "page" | "project" | "workspace_page";
export type THomeWidgetKeys =
  | "needs_attention"
  | "quick_links"
  | "recents"
  | "my_stickies"
  | "quick_tutorial"
  | "new_at_plane";

export type THomeWidgetProps = {
  workspaceSlug: string;
};

export type TPageEntityData = {
  id: string;
  name: string;
  logo_props: TLogoProps;
  project_id?: string;
  owned_by: string;
  project_identifier?: string;
};

export type TProjectEntityData = {
  id: string;
  name: string;
  logo_props: TLogoProps;
  project_members: string[];
  identifier: string;
};

export type TIssueEntityData = {
  id: string;
  name: string;
  state: string;
  priority: TIssuePriorities;
  assignees: string[];
  type: string | null;
  sequence_id: number;
  project_id: string;
  project_identifier: string;
  is_epic: boolean;
};

export type TActivityEntityData = {
  id: string;
  entity_name: "page" | "project" | "issue" | "workspace_page";
  entity_identifier: string;
  visited_at: string;
  entity_data: TPageEntityData | TProjectEntityData | TIssueEntityData;
};

export type TLinkEditableFields = {
  title: string;
  url: string;
  /** Paradise KEP-82: icon picked like a project icon. null = back to the site favicon. Write-only. */
  logo_props?: TLogoProps | null;
};

/** Paradise KEP-82: filled by the server. Manual title/icon never overwrite these. */
export type TQuickLinkMetadata = {
  title?: string | null;
  favicon?: string | null;
  favicon_url?: string | null;
  /** Page preview image (og:image or twitter:image) as a data URI. Null = the page has none. */
  og_image?: string | null;
  /** Icon or emoji picked by the user. Wins over the favicon. */
  logo_props?: TLogoProps | null;
  /** Icon set when the link was created (e.g. imported links). Used only when the site has no favicon. */
  logo_cadangan?: TLogoProps | null;
  diambil_pada?: string;
};

export type TLink = TLinkEditableFields & {
  created_by_id: string;
  id: string;
  metadata: TQuickLinkMetadata;
  workspace_slug: string;

  //need
  created_at: Date;
};

export type TLinkMap = {
  [workspace_slug: string]: TLink;
};

export type TLinkIdMap = {
  [workspace_slug: string]: string[];
};

export type TWidgetEntityData = {
  key: THomeWidgetKeys;
  name: string;
  is_enabled: boolean;
  sort_order: number;
};

// Paradise KEP-82: quick links an admin shares with everyone or with chosen divisions/departments.
export type TSharedQuickLinkAudience = "semua" | "organisasi";

export type TSharedQuickLink = {
  id: string;
  url: string;
  title: string | null;
  metadata: TQuickLinkMetadata;
  cakupan: TSharedQuickLinkAudience;
  departemen_ids: string[];
  divisi_ids: string[];
  sort_order: number;
  created_at: string;
};

export type TSharedQuickLinkDivision = {
  id: string;
  kode: string;
  nama: string;
  departemen: { id: string; kode: string; nama: string }[];
};

export type TSharedQuickLinksResponse = {
  boleh_kelola: boolean;
  /** Links that apply to the caller. */
  links: TSharedQuickLink[];
  /** Admins only: every shared link, including ones aimed at other units. */
  semua?: TSharedQuickLink[];
  /** Admins only: divisions and departments to aim a link at. */
  organisasi?: TSharedQuickLinkDivision[];
};

export type TSharedQuickLinkPayload = {
  url?: string;
  title?: string;
  logo_props?: TLogoProps | null;
  cakupan?: TSharedQuickLinkAudience;
  departemen_ids?: string[];
  divisi_ids?: string[];
};
