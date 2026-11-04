/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { computed, makeObservable } from "mobx";
import { computedFn } from "mobx-utils";
// constants
import { EPageAccess, EUserPermissions } from "@plane/constants";
import type { TPage } from "@plane/types";
// lib
import { bacaIzinSumber, nilaiIzinIsi } from "@/lib/izin-sumber";
import { isWikiProject } from "@/lib/wiki-project";
// plane web store
import type { RootStore } from "@/plane-web/store/root.store";
// services
import { ProjectPageService } from "@/services/page";
const projectPageService = new ProjectPageService();
// store
import { BasePage } from "./base-page";
import type { TPageInstance } from "./base-page";

export type TProjectPage = TPageInstance;

export class ProjectPage extends BasePage implements TProjectPage {
  constructor(store: RootStore, page: TPage) {
    // required fields for API calls
    const { workspaceSlug } = store.router;
    const projectId = page.project_ids?.[0];
    // initialize base instance
    super(store, page, {
      update: async (payload) => {
        if (!workspaceSlug || !projectId || !page.id) throw new Error("Missing required fields.");
        return await projectPageService.update(workspaceSlug, projectId, page.id, payload);
      },
      updateDescription: async (document) => {
        if (!workspaceSlug || !projectId || !page.id) throw new Error("Missing required fields.");
        await projectPageService.updateDescription(workspaceSlug, projectId, page.id, document);
      },
      updateAccess: async (payload) => {
        if (!workspaceSlug || !projectId || !page.id) throw new Error("Missing required fields.");
        await projectPageService.updateAccess(workspaceSlug, projectId, page.id, payload);
      },
      lock: async () => {
        if (!workspaceSlug || !projectId || !page.id) throw new Error("Missing required fields.");
        await projectPageService.lock(workspaceSlug, projectId, page.id);
      },
      unlock: async () => {
        if (!workspaceSlug || !projectId || !page.id) throw new Error("Missing required fields.");
        await projectPageService.unlock(workspaceSlug, projectId, page.id);
      },
      archive: async () => {
        if (!workspaceSlug || !projectId || !page.id) throw new Error("Missing required fields.");
        return await projectPageService.archive(workspaceSlug, projectId, page.id);
      },
      restore: async () => {
        if (!workspaceSlug || !projectId || !page.id) throw new Error("Missing required fields.");
        await projectPageService.restore(workspaceSlug, projectId, page.id);
      },
      duplicate: async () => {
        if (!workspaceSlug || !projectId || !page.id) throw new Error("Missing required fields.");
        return await projectPageService.duplicate(workspaceSlug, projectId, page.id);
      },
    });
    makeObservable(this, {
      // computed
      canCurrentUserAccessPage: computed,
      canCurrentUserEditPage: computed,
      canCurrentUserDuplicatePage: computed,
      canCurrentUserLockPage: computed,
      canCurrentUserChangeAccess: computed,
      canCurrentUserArchivePage: computed,
      canCurrentUserDeletePage: computed,
      canCurrentUserFavoritePage: computed,
      canCurrentUserMovePage: computed,
      isContentEditable: computed,
    });
  }

  private getHighestRoleAcrossProjects = computedFn((): EUserPermissions | undefined => {
    const { workspaceSlug } = this.rootStore.router;
    if (!workspaceSlug || !this.project_ids?.length) return;
    let highestRole: EUserPermissions | undefined = undefined;
    this.project_ids.map((projectId) => {
      const currentUserProjectRole = this.rootStore.user.permission.getProjectRoleByWorkspaceSlugAndProjectId(
        workspaceSlug?.toString() || "",
        projectId?.toString() || ""
      );
      if (currentUserProjectRole) {
        if (!highestRole) highestRole = currentUserProjectRole;
        else if (currentUserProjectRole > highestRole) highestRole = currentUserProjectRole;
      }
    });
    return highestRole;
  });

  /**
   * Kustomisasi Paradise (KEP-85): hak atas page mengikuti aturan God Mode
   * (pemilik + atasan / pemilik saja / semua anggota), bukan role admin project.
   * Data izin dibaca dari salinan reaktif `izin-saya/` yang diisi `useIzinSumber`
   * (dipasang di layout project); belum dimuat = pemilik saja.
   *
   * Page di project Wiki tetap aturan lama: hanya admin project.
   */
  private bolehMenurutIzin = computedFn(
    (kunci: "PERM_PAGE_EDIT" | "PERM_PAGE_ARCHIVE" | "PERM_PAGE_DELETE"): boolean => {
      const projectId = this.project_ids?.[0];
      const project = this.rootStore.projectRoot.project.getProjectById(projectId);
      if (isWikiProject(project)) return this.getHighestRoleAcrossProjects() === EUserPermissions.ADMIN;
      const highestRole = this.getHighestRoleAcrossProjects();
      if (!highestRole || highestRole < EUserPermissions.MEMBER) return false;
      const izin = bacaIzinSumber(this.rootStore.router.workspaceSlug, projectId);
      return nilaiIzinIsi(izin, kunci, { pemilikId: this.owned_by }, this.rootStore.user.data?.id, !!projectId);
    }
  );

  /**
   * @description returns true if the current logged in user can access the page
   */
  get canCurrentUserAccessPage() {
    const isPagePublic = this.access === EPageAccess.PUBLIC;
    return isPagePublic || this.isCurrentUserOwner;
  }

  /**
   * @description returns true if the current logged in user can edit the page
   * Kustomisasi Paradise: lihat `bolehMenurutIzin` (KEP-85; Wiki tetap admin project).
   */
  get canCurrentUserEditPage() {
    return this.bolehMenurutIzin("PERM_PAGE_EDIT");
  }

  /**
   * @description returns true if the current logged in user can create a duplicate the page
   */
  get canCurrentUserDuplicatePage() {
    const highestRole = this.getHighestRoleAcrossProjects();
    return !!highestRole && highestRole >= EUserPermissions.MEMBER;
  }

  /**
   * @description returns true if the current logged in user can lock the page
   */
  get canCurrentUserLockPage() {
    return this.bolehMenurutIzin("PERM_PAGE_EDIT");
  }

  /**
   * @description returns true if the current logged in user can change the access of the page
   */
  get canCurrentUserChangeAccess() {
    // Paradise KEP-85: publik/privat hanya pemiliknya.
    const project = this.rootStore.projectRoot.project.getProjectById(this.project_ids?.[0]);
    if (isWikiProject(project)) return this.getHighestRoleAcrossProjects() === EUserPermissions.ADMIN;
    return this.isCurrentUserOwner;
  }

  /**
   * @description returns true if the current logged in user can archive the page
   */
  get canCurrentUserArchivePage() {
    return this.bolehMenurutIzin("PERM_PAGE_ARCHIVE");
  }

  /**
   * @description returns true if the current logged in user can delete the page
   */
  get canCurrentUserDeletePage() {
    return this.bolehMenurutIzin("PERM_PAGE_DELETE");
  }

  /**
   * @description returns true if the current logged in user can favorite the page
   */
  get canCurrentUserFavoritePage() {
    const highestRole = this.getHighestRoleAcrossProjects();
    return !!highestRole && highestRole >= EUserPermissions.MEMBER;
  }

  /**
   * @description returns true if the current logged in user can move the page
   */
  get canCurrentUserMovePage() {
    const highestRole = this.getHighestRoleAcrossProjects();
    return highestRole === EUserPermissions.ADMIN;
  }

  /**
   * @description returns true if the page can be edited
   */
  get isContentEditable() {
    const isArchived = this.archived_at;
    const isLocked = this.is_locked;

    return !isArchived && !isLocked && this.canCurrentUserEditPage;
  }

  getRedirectionLink = computedFn(() => {
    const { workspaceSlug } = this.rootStore.router;
    return `/${workspaceSlug}/projects/${this.project_ids?.[0]}/pages/${this.id}`;
  });
}
