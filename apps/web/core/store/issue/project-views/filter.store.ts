/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isEmpty, set } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
// base class
import { computedFn } from "mobx-utils";
import type { TSupportedFilterTypeForUpdate } from "@plane/constants";
import { EIssueFilterType } from "@plane/constants";
import type {
  IIssueDisplayFilterOptions,
  IIssueDisplayProperties,
  TIssueKanbanFilters,
  IIssueFilters,
  TIssueParams,
  IssuePaginationOptions,
  IProjectView,
  TWorkItemFilterExpression,
  TSupportedFilterForUpdate,
} from "@plane/types";
import { EIssuesStoreType } from "@plane/types";
import { handleIssueQueryParamsByLayout } from "@plane/utils";
// lib
import { isViewBawaan } from "@/lib/view-bawaan";
// services
import { ViewService } from "@/services/view.service";
import type { IBaseIssueFilterStore } from "../helpers/issue-filter-helper.store";
import { IssueFilterHelperStore } from "../helpers/issue-filter-helper.store";
// helpers
// types
import type { IIssueRootStore } from "../root.store";
// constants

export interface IProjectViewIssuesFilter extends IBaseIssueFilterStore {
  //helper actions
  getFilterParams: (
    options: IssuePaginationOptions,
    viewId: string,
    cursor: string | undefined,
    groupId: string | undefined,
    subGroupId: string | undefined
  ) => Partial<Record<TIssueParams, string | boolean>>;
  getIssueFilters(viewId: string): IIssueFilters | undefined;
  // helper actions
  mutateFilters: (workspaceSlug: string, viewId: string, viewDetails: IProjectView) => void;
  // action
  fetchFilters: (workspaceSlug: string, projectId: string, viewId: string) => Promise<void>;
  updateFilterExpression: (
    workspaceSlug: string,
    projectId: string,
    viewId: string,
    filters: TWorkItemFilterExpression
  ) => Promise<void>;
  updateFilters: (
    workspaceSlug: string,
    projectId: string,
    filterType: TSupportedFilterTypeForUpdate,
    filters: TSupportedFilterForUpdate,
    viewId: string
  ) => Promise<void>;
  resetFilters: (workspaceSlug: string, viewId: string) => void;
}

export class ProjectViewIssuesFilter extends IssueFilterHelperStore implements IProjectViewIssuesFilter {
  // observables
  filters: { [viewId: string]: IIssueFilters } = {};
  // root store
  rootIssueStore;
  // services
  issueFilterService;

  constructor(_rootStore: IIssueRootStore) {
    super();
    makeObservable(this, {
      // observables
      filters: observable,
      // computed
      issueFilters: computed,
      appliedFilters: computed,
      // actions
      fetchFilters: action,
      updateFilters: action,
      resetFilters: action,
    });
    // root store
    this.rootIssueStore = _rootStore;
    // services
    this.issueFilterService = new ViewService();
  }

  get issueFilters() {
    const viewId = this.rootIssueStore.viewId;
    if (!viewId) return undefined;

    return this.getIssueFilters(viewId);
  }

  get appliedFilters() {
    const viewId = this.rootIssueStore.viewId;
    if (!viewId) return undefined;

    return this.getAppliedFilters(viewId);
  }

  getIssueFilters(viewId: string) {
    const displayFilters = this.filters[viewId] || undefined;
    if (isEmpty(displayFilters)) return undefined;

    const currentFilters: IIssueFilters = this.computedIssueFilters(displayFilters);

    return currentFilters;
  }

  getAppliedFilters(viewId: string) {
    const userFilters = this.getIssueFilters(viewId);
    if (!userFilters) return undefined;

    const filteredParams = handleIssueQueryParamsByLayout(userFilters?.displayFilters?.layout, "issues");
    if (!filteredParams) return undefined;

    const filteredRouteParams: Partial<Record<TIssueParams, string | boolean>> = this.computedFilteredParams(
      userFilters?.richFilters,
      userFilters?.displayFilters,
      filteredParams
    );

    return filteredRouteParams;
  }

  getFilterParams = computedFn(
    (
      options: IssuePaginationOptions,
      viewId: string,
      cursor: string | undefined,
      groupId: string | undefined,
      subGroupId: string | undefined
    ) => {
      let filterParams = this.getAppliedFilters(viewId);

      // Kustomisasi Paradise: view bawaan departemen (Assigned/Created/Subscribed) = syarat
      // "milik saya" yang sama dengan view bawaan workspace, dikirim sebagai parameter API.
      if (isViewBawaan(viewId)) {
        const syarat = this.getFilterConditionBasedOnViews(this.rootIssueStore.currentUserId, viewId);
        if (syarat) filterParams = { ...filterParams, ...syarat };
      }

      const paginationParams = this.getPaginationParams(filterParams, options, cursor, groupId, subGroupId);
      return paginationParams;
    }
  );

  mutateFilters: IProjectViewIssuesFilter["mutateFilters"] = action((workspaceSlug, viewId, viewDetails) => {
    const richFilters: TWorkItemFilterExpression = viewDetails?.rich_filters;
    const displayFilters: IIssueDisplayFilterOptions = this.computedDisplayFilters(viewDetails?.display_filters);
    const displayProperties: IIssueDisplayProperties = this.computedDisplayProperties(viewDetails?.display_properties);

    // fetching the kanban toggle helpers in the local storage
    const kanbanFilters = {
      group_by: [],
      sub_group_by: [],
    };
    const currentUserId = this.rootIssueStore.currentUserId;
    if (currentUserId) {
      const storedKanbanFilters = this.handleIssuesLocalFilters.get(
        EIssuesStoreType.PROJECT_VIEW,
        workspaceSlug,
        viewId,
        currentUserId
      );
      kanbanFilters.group_by = storedKanbanFilters?.kanban_filters?.group_by || [];
      kanbanFilters.sub_group_by = storedKanbanFilters?.kanban_filters?.sub_group_by || [];
    }

    runInAction(() => {
      set(this.filters, [viewId, "richFilters"], richFilters);
      set(this.filters, [viewId, "displayFilters"], displayFilters);
      set(this.filters, [viewId, "displayProperties"], displayProperties);
      set(this.filters, [viewId, "kanbanFilters"], kanbanFilters);
    });
  });

  /** Kunci penyimpanan lokal tampilan view bawaan: per departemen, per orang. */
  private kunciLokalBawaan = (projectId: string, viewId: string) => `${projectId}:${viewId}`;

  fetchFilters = async (workspaceSlug: string, projectId: string, viewId: string) => {
    try {
      if (isViewBawaan(viewId)) {
        // View bawaan tidak punya baris di server: tampilannya (layout, properti) disimpan lokal.
        const viewBawaan = await this.rootIssueStore.rootStore.projectView.fetchViewDetails(
          workspaceSlug,
          projectId,
          viewId
        );
        const tersimpan = this.handleIssuesLocalFilters.get(
          EIssuesStoreType.PROJECT_VIEW,
          workspaceSlug,
          this.kunciLokalBawaan(projectId, viewId),
          this.rootIssueStore.currentUserId
        );
        this.mutateFilters(workspaceSlug, viewId, {
          ...viewBawaan,
          display_filters: tersimpan?.display_filters ?? viewBawaan.display_filters,
          display_properties: tersimpan?.display_properties ?? viewBawaan.display_properties,
        });
        return;
      }
      const viewDetails = await this.issueFilterService.getViewDetails(workspaceSlug, projectId, viewId);
      this.mutateFilters(workspaceSlug, viewId, viewDetails);
    } catch (error) {
      console.log("error while fetching project view filters", error);
      throw error;
    }
  };

  /**
   * NOTE: This method is designed as a fallback function for the work item filter store.
   * Only use this method directly when initializing filter instances.
   * For regular filter updates, use this method as a fallback function for the work item filter store methods instead.
   */
  updateFilterExpression: IProjectViewIssuesFilter["updateFilterExpression"] = async (
    workspaceSlug,
    projectId,
    viewId,
    filters
  ) => {
    try {
      runInAction(() => {
        set(this.filters, [viewId, "richFilters"], filters);
      });

      this.rootIssueStore.projectViewIssues.fetchIssuesWithExistingPagination(
        workspaceSlug,
        projectId,
        viewId,
        "mutation"
      );
    } catch (error) {
      console.log("error while updating rich filters", error);
      throw error;
    }
  };

  updateFilters: IProjectViewIssuesFilter["updateFilters"] = async (
    workspaceSlug,
    projectId,
    type,
    filters,
    viewId
  ) => {
    try {
      if (isEmpty(this.filters) || isEmpty(this.filters[viewId])) return;

      const currentFilters = {
        richFilters: this.filters[viewId].richFilters,
        displayFilters: this.filters[viewId].displayFilters as IIssueDisplayFilterOptions,
        displayProperties: this.filters[viewId].displayProperties as IIssueDisplayProperties,
        kanbanFilters: this.filters[viewId].kanbanFilters as TIssueKanbanFilters,
      };

      switch (type) {
        case EIssueFilterType.DISPLAY_FILTERS: {
          const updatedDisplayFilters = filters as IIssueDisplayFilterOptions;
          currentFilters.displayFilters = { ...currentFilters.displayFilters, ...updatedDisplayFilters };

          // set sub_group_by to null if group_by is set to null
          if (currentFilters.displayFilters.group_by === null) {
            currentFilters.displayFilters.sub_group_by = null;
            updatedDisplayFilters.sub_group_by = null;
          }
          // set sub_group_by to null if layout is switched to kanban group_by and sub_group_by are same
          if (
            currentFilters.displayFilters.layout === "kanban" &&
            currentFilters.displayFilters.group_by === currentFilters.displayFilters.sub_group_by
          ) {
            currentFilters.displayFilters.sub_group_by = null;
            updatedDisplayFilters.sub_group_by = null;
          }
          // set group_by to state if layout is switched to kanban and group_by is null
          if (currentFilters.displayFilters.layout === "kanban" && currentFilters.displayFilters.group_by === null) {
            currentFilters.displayFilters.group_by = "state";
            updatedDisplayFilters.group_by = "state";
          }

          runInAction(() => {
            Object.keys(updatedDisplayFilters).forEach((_key) => {
              set(
                this.filters,
                [viewId, "displayFilters", _key],
                updatedDisplayFilters[_key as keyof IIssueDisplayFilterOptions]
              );
            });
          });

          if (isViewBawaan(viewId))
            this.handleIssuesLocalFilters.set(
              EIssuesStoreType.PROJECT_VIEW,
              type,
              workspaceSlug,
              this.kunciLokalBawaan(projectId, viewId),
              this.rootIssueStore.currentUserId,
              { display_filters: currentFilters.displayFilters }
            );

          if (this.getShouldClearIssues(updatedDisplayFilters)) {
            this.rootIssueStore.projectIssues.clear(true); // clear issues for local store when some filters like layout changes
          }

          if (this.getShouldReFetchIssues(updatedDisplayFilters)) {
            this.rootIssueStore.projectViewIssues.fetchIssuesWithExistingPagination(
              workspaceSlug,
              projectId,
              viewId,
              "mutation"
            );
          }

          break;
        }
        case EIssueFilterType.DISPLAY_PROPERTIES: {
          const updatedDisplayProperties = filters as IIssueDisplayProperties;
          currentFilters.displayProperties = { ...currentFilters.displayProperties, ...updatedDisplayProperties };

          runInAction(() => {
            Object.keys(updatedDisplayProperties).forEach((_key) => {
              set(
                this.filters,
                [viewId, "displayProperties", _key],
                updatedDisplayProperties[_key as keyof IIssueDisplayProperties]
              );
            });
          });

          if (isViewBawaan(viewId))
            this.handleIssuesLocalFilters.set(
              EIssuesStoreType.PROJECT_VIEW,
              type,
              workspaceSlug,
              this.kunciLokalBawaan(projectId, viewId),
              this.rootIssueStore.currentUserId,
              { display_properties: currentFilters.displayProperties }
            );

          break;
        }
        case EIssueFilterType.KANBAN_FILTERS: {
          const updatedKanbanFilters = filters as TIssueKanbanFilters;
          currentFilters.kanbanFilters = { ...currentFilters.kanbanFilters, ...updatedKanbanFilters };

          const currentUserId = this.rootIssueStore.currentUserId;
          if (currentUserId)
            this.handleIssuesLocalFilters.set(
              EIssuesStoreType.PROJECT_VIEW,
              type,
              workspaceSlug,
              viewId,
              currentUserId,
              {
                kanban_filters: currentFilters.kanbanFilters,
              }
            );

          runInAction(() => {
            Object.keys(updatedKanbanFilters).forEach((_key) => {
              set(
                this.filters,
                [viewId, "kanbanFilters", _key],
                updatedKanbanFilters[_key as keyof TIssueKanbanFilters]
              );
            });
          });

          break;
        }
        default:
          break;
      }
    } catch (error) {
      if (viewId) this.fetchFilters(workspaceSlug, projectId, viewId);
      throw error;
    }
  };

  /**
   * @description resets the filters for a project view
   * @param workspaceSlug
   * @param viewId
   */
  resetFilters: IProjectViewIssuesFilter["resetFilters"] = action((workspaceSlug, viewId) => {
    const viewDetails = this.rootIssueStore.rootStore.projectView.getViewById(viewId);
    if (!viewDetails) return;
    this.mutateFilters(workspaceSlug, viewId, viewDetails);
  });
}
