/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: perintah Power K milik modul God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { PARADISE_REMOVED, isParadiseGateActive } from "@plane/constants";
import type { TParadiseGate } from "@plane/constants";

/**
 * Perintah Power K -> modul pemiliknya (atau `PARADISE_REMOVED` untuk fitur yang
 * dicabut, KEP-50). Modul mati = perintahnya hilang dari
 * palet, dari modal pintasan, dan pintasan kuncinya (mis. `gx`, `ga`) tak
 * jalan. Perintah cycle/module/page/view per project sudah membaca flag
 * `*_view` yang dipaksa false, tapi tetap didaftarkan di sini supaya modal
 * pintasan (yang tak punya konteks project) ikut bersih.
 */
const MODUL_PER_PERINTAH: Record<string, TParadiseGate> = {
  nav_inbox: "inbox",
  nav_your_work: "your_work",
  nav_all_workspace_work_items: "views",
  nav_assigned_workspace_work_items: "views",
  nav_created_workspace_work_items: "views",
  nav_subscribed_workspace_work_items: "views",
  nav_workspace_analytics: "analytics",
  nav_workspace_drafts: "drafts",
  nav_workspace_archives: "archives",
  nav_project_archives: "archives",
  nav_project_cycles: PARADISE_REMOVED,
  open_project_cycle: PARADISE_REMOVED,
  create_cycle: PARADISE_REMOVED,
  add_work_item_to_cycle: PARADISE_REMOVED,
  copy_cycle_url: PARADISE_REMOVED,
  toggle_cycle_favorite: PARADISE_REMOVED,
  nav_project_modules: "modules",
  open_project_module: "modules",
  create_module: "modules",
  add_work_item_to_modules: "modules",
  add_remove_module_members: "modules",
  change_module_status: "modules",
  copy_module_url: "modules",
  toggle_module_favorite: "modules",
  nav_project_views: "views",
  open_project_view: "views",
  create_view: "views",
  nav_project_pages: "pages",
  create_page: "pages",
  copy_page_url: "pages",
  toggle_page_access: "pages",
  toggle_page_archive: "pages",
  toggle_page_favorite: "pages",
  toggle_page_lock: "pages",
  nav_project_intake: "intake",
  change_work_item_estimate: "estimates",
  open_plane_documentation: "wiki",
};

export const isPowerKCommandModuleActive = (commandId: string): boolean =>
  !Object.hasOwn(MODUL_PER_PERINTAH, commandId) || isParadiseGateActive(MODUL_PER_PERINTAH[commandId]);
