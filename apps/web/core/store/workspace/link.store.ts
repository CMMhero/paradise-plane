/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { set } from "lodash-es";
import { action, makeObservable, observable, runInAction } from "mobx";
// types
import type {
  TLink,
  TLinkIdMap,
  TLinkMap,
  TSharedQuickLink,
  TSharedQuickLinkPayload,
  TSharedQuickLinksResponse,
} from "@plane/types";

/** Paradise KEP-82: `link` stays set while the modal closes so its content does not flash empty. */
export type TSharedLinkModalState = { isOpen: boolean; link?: TSharedQuickLink };
// services
import { WorkspaceService } from "@/services/workspace.service";

export interface IWorkspaceLinkStoreActions {
  addLinks: (projectId: string, links: TLink[]) => void;
  fetchLinks: (workspaceSlug: string) => Promise<TLink[]>;
  createLink: (workspaceSlug: string, data: Partial<TLink>) => Promise<TLink>;
  updateLink: (workspaceSlug: string, linkId: string, data: Partial<TLink>) => Promise<TLink>;
  removeLink: (workspaceSlug: string, linkId: string) => Promise<void>;
  setLinkData: (link: TLink | undefined) => void;
  toggleLinkModal: (isOpen: boolean) => void;
  fetchSharedLinks: (workspaceSlug: string) => Promise<TSharedQuickLinksResponse>;
  createSharedLink: (workspaceSlug: string, data: TSharedQuickLinkPayload) => Promise<void>;
  updateSharedLink: (workspaceSlug: string, linkId: string, data: TSharedQuickLinkPayload) => Promise<void>;
  removeSharedLink: (workspaceSlug: string, linkId: string) => Promise<void>;
}

export interface IWorkspaceLinkStore extends IWorkspaceLinkStoreActions {
  // observables
  links: TLinkIdMap;
  linkMap: TLinkMap;
  linkData: TLink | undefined;
  isLinkModalOpen: boolean;
  sharedLinks: Record<string, TSharedQuickLinksResponse>;
  sharedLinkModal: TSharedLinkModalState;
  openSharedLinkModal: (link?: TSharedQuickLink) => void;
  closeSharedLinkModal: () => void;
  // helper methods
  getLinksByWorkspaceId: (projectId: string) => string[] | undefined;
  getLinkById: (linkId: string) => TLink | undefined;
  getSharedLinks: (workspaceSlug: string) => TSharedQuickLinksResponse | undefined;
}

export class WorkspaceLinkStore implements IWorkspaceLinkStore {
  // observables
  links: TLinkIdMap = {};
  linkMap: TLinkMap = {};
  linkData: TLink | undefined = undefined;
  isLinkModalOpen = false;
  sharedLinks: Record<string, TSharedQuickLinksResponse> = {};
  sharedLinkModal: TSharedLinkModalState = { isOpen: false };
  // services
  workspaceService: WorkspaceService;

  constructor() {
    makeObservable(this, {
      // observables
      links: observable,
      linkMap: observable,
      linkData: observable,
      isLinkModalOpen: observable,
      sharedLinks: observable,
      sharedLinkModal: observable.ref,
      // actions
      addLinks: action.bound,
      fetchLinks: action,
      createLink: action,
      updateLink: action,
      removeLink: action,
      setLinkData: action,
      toggleLinkModal: action,
    });
    // services
    this.workspaceService = new WorkspaceService();
  }

  // helper methods
  getLinksByWorkspaceId = (projectId: string) => {
    if (!projectId) return undefined;
    return this.links[projectId] ?? undefined;
  };

  getLinkById = (linkId: string) => {
    if (!linkId) return undefined;
    return this.linkMap[linkId] ?? undefined;
  };

  // actions
  setLinkData = (link: TLink | undefined) => {
    runInAction(() => {
      this.linkData = link;
    });
  };

  toggleLinkModal = (isOpen: boolean) => {
    runInAction(() => {
      this.isLinkModalOpen = isOpen;
    });
  };

  addLinks = (workspaceSlug: string, links: TLink[]) => {
    runInAction(() => {
      this.links[workspaceSlug] = links.map((link) => link.id);
      links.forEach((link) => set(this.linkMap, link.id, link));
    });
  };

  fetchLinks = async (workspaceSlug: string) => {
    const response = await this.workspaceService.fetchWorkspaceLinks(workspaceSlug);
    this.addLinks(workspaceSlug, response);
    return response;
  };

  createLink = async (workspaceSlug: string, data: Partial<TLink>) => {
    const response = await this.workspaceService.createWorkspaceLink(workspaceSlug, data);

    runInAction(() => {
      this.links[workspaceSlug] = [response.id, ...(this.links[workspaceSlug] ?? [])];
      set(this.linkMap, response.id, response);
    });
    return response;
  };

  updateLink = async (workspaceSlug: string, linkId: string, data: Partial<TLink>) => {
    runInAction(() => {
      Object.keys(data).forEach((key) => {
        set(this.linkMap, [linkId, key], data[key as keyof TLink]);
      });
    });

    const response = await this.workspaceService.updateWorkspaceLink(workspaceSlug, linkId, data);
    // Paradise KEP-82: the server refetches the site title/favicon, so keep its copy.
    runInAction(() => {
      set(this.linkMap, linkId, response);
    });
    return response;
  };

  // Paradise KEP-82: shared links. Every write refetches, because which links apply
  // to the caller is decided by the server from their division/department placement.
  fetchSharedLinks = async (workspaceSlug: string) => {
    const response = await this.workspaceService.fetchSharedQuickLinks(workspaceSlug);
    runInAction(() => {
      set(this.sharedLinks, workspaceSlug, response);
    });
    return response;
  };

  createSharedLink = async (workspaceSlug: string, data: TSharedQuickLinkPayload) => {
    await this.workspaceService.createSharedQuickLink(workspaceSlug, data);
    await this.fetchSharedLinks(workspaceSlug);
  };

  updateSharedLink = async (workspaceSlug: string, linkId: string, data: TSharedQuickLinkPayload) => {
    await this.workspaceService.updateSharedQuickLink(workspaceSlug, linkId, data);
    await this.fetchSharedLinks(workspaceSlug);
  };

  removeSharedLink = async (workspaceSlug: string, linkId: string) => {
    await this.workspaceService.deleteSharedQuickLink(workspaceSlug, linkId);
    await this.fetchSharedLinks(workspaceSlug);
  };

  getSharedLinks = (workspaceSlug: string) => this.sharedLinks[workspaceSlug];

  // One modal for adding/editing shared links, opened from the page header or a link's menu.
  openSharedLinkModal = (link?: TSharedQuickLink) => {
    runInAction(() => {
      this.sharedLinkModal = { isOpen: true, link };
    });
  };

  closeSharedLinkModal = () => {
    runInAction(() => {
      this.sharedLinkModal = { isOpen: false, link: this.sharedLinkModal.link };
    });
  };

  removeLink = async (workspaceSlug: string, linkId: string) => {
    // const issueLinkCount = this.getLinksByWorkspaceId(projectId)?.length ?? 0;
    await this.workspaceService.deleteWorkspaceLink(workspaceSlug, linkId);

    const linkIndex = this.links[workspaceSlug].findIndex((link) => link === linkId);
    if (linkIndex >= 0)
      runInAction(() => {
        this.links[workspaceSlug].splice(linkIndex, 1);
        delete this.linkMap[linkId];
      });
  };
}
