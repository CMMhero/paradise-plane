/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { orderBy, clone, set } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
// plane imports
import { isParadiseModuleActive } from "@plane/constants";
import type { THomeWidgetKeys, TParadiseModule, TWidgetEntityData } from "@plane/types";
// plane web services
import { WorkspaceService } from "@/services/workspace.service";
// store
import type { IWorkspaceLinkStore } from "./link.store";
import { WorkspaceLinkStore } from "./link.store";

/**
 * Widget Home milik modul God Mode: modulnya mati, widgetnya ikut hilang.
 * Stickies dan Quick links tampil di DUA tempat, widget Home dan menu
 * sidebar beserta halamannya, jadi satu saklar mengatur keduanya.
 */
const MODUL_PER_WIDGET: Partial<Record<THomeWidgetKeys, TParadiseModule>> = {
  my_stickies: "stickies",
  quick_links: "quick_links",
};

const isHomeWidgetAvailable = (key: THomeWidgetKeys): boolean => {
  const module = MODUL_PER_WIDGET[key];
  return module ? isParadiseModuleActive(module) : true;
};

export interface IHomeStore {
  // observables
  loading: boolean;
  showWidgetSettings: boolean;
  widgetsMap: Record<string, TWidgetEntityData>;
  widgets: THomeWidgetKeys[];
  // computed
  isAnyWidgetEnabled: boolean;
  orderedWidgets: THomeWidgetKeys[];
  //stores
  quickLinks: IWorkspaceLinkStore;
  // actions
  toggleWidgetSettings: (value?: boolean) => void;
  fetchWidgets: (workspaceSlug: string) => Promise<void>;
  reorderWidget: (
    workspaceSlug: string,
    widgetKey: string,
    destinationId: string,
    edge: string | undefined
  ) => Promise<void>;
  toggleWidget: (workspaceSlug: string, widgetKey: string, is_enabled: boolean) => void;
}

export class HomeStore implements IHomeStore {
  // observables
  showWidgetSettings = false;
  loading = false;
  widgetsMap: Record<string, TWidgetEntityData> = {};
  widgets: THomeWidgetKeys[] = [];
  // stores
  quickLinks: IWorkspaceLinkStore;
  // services
  workspaceService: WorkspaceService;

  constructor() {
    makeObservable(this, {
      // observables
      loading: observable,
      showWidgetSettings: observable,
      widgetsMap: observable,
      widgets: observable,
      // computed
      isAnyWidgetEnabled: computed,
      orderedWidgets: computed,
      // actions
      toggleWidgetSettings: action,
      fetchWidgets: action,
      reorderWidget: action,
      toggleWidget: action,
    });
    // services
    this.workspaceService = new WorkspaceService();

    // stores
    this.quickLinks = new WorkspaceLinkStore();
  }

  // Widget yang modulnya dimatikan di God Mode tidak tampil di Home maupun di
  // dialog kelola widget. Barisnya tetap tersimpan di backend.
  private get homeWidgets() {
    return Object.values(this.widgetsMap).filter((widget) => isHomeWidgetAvailable(widget.key));
  }

  get isAnyWidgetEnabled() {
    return this.homeWidgets.some((widget) => widget.is_enabled);
  }

  get orderedWidgets() {
    return orderBy(this.homeWidgets, "sort_order", "desc").map((widget) => widget.key);
  }

  toggleWidgetSettings = (value?: boolean) => {
    this.showWidgetSettings = value !== undefined ? value : !this.showWidgetSettings;
  };

  fetchWidgets = async (workspaceSlug: string) => {
    try {
      this.loading = true;
      const widgets = await this.workspaceService.fetchWorkspaceWidgets(workspaceSlug);
      runInAction(() => {
        this.widgets = orderBy(Object.values(widgets), "sort_order", "desc").map((widget) => widget.key);
        widgets.forEach((widget) => {
          this.widgetsMap[widget.key] = widget;
        });
        this.loading = false;
      });
    } catch (error) {
      console.error("Failed to fetch widgets");
      this.loading = false;
      throw error;
    }
  };

  toggleWidget = async (workspaceSlug: string, widgetKey: string, is_enabled: boolean) => {
    try {
      await this.workspaceService.updateWorkspaceWidget(workspaceSlug, widgetKey, {
        is_enabled,
      });
      runInAction(() => {
        this.widgetsMap[widgetKey].is_enabled = is_enabled;
      });
    } catch (error) {
      console.error("Failed to toggle widget");
      throw error;
    }
  };

  reorderWidget = async (workspaceSlug: string, widgetKey: string, destinationId: string, edge: string | undefined) => {
    const sortOrderBeforeUpdate = clone(this.widgetsMap[widgetKey]?.sort_order);
    try {
      let resultSequence = 10000;
      if (edge) {
        const sortedIds = orderBy(Object.values(this.widgetsMap), "sort_order", "desc").map((widget) => widget.key);
        const destinationSequence = this.widgetsMap[destinationId]?.sort_order || undefined;
        if (destinationSequence) {
          const destinationIndex = sortedIds.findIndex((id) => id === destinationId);
          if (edge === "reorder-above") {
            const prevSequence = this.widgetsMap[sortedIds[destinationIndex - 1]]?.sort_order || undefined;
            if (prevSequence) {
              resultSequence = (destinationSequence + prevSequence) / 2;
            } else {
              resultSequence = destinationSequence + resultSequence;
            }
          } else {
            resultSequence = destinationSequence - resultSequence;
          }
        }
      }
      runInAction(() => {
        set(this.widgetsMap, [widgetKey, "sort_order"], resultSequence);
      });
      await this.workspaceService.updateWorkspaceWidget(workspaceSlug, widgetKey, {
        sort_order: resultSequence,
      });
    } catch (error) {
      console.error("Failed to move widget");
      runInAction(() => {
        set(this.widgetsMap, [widgetKey, "sort_order"], sortOrderBeforeUpdate);
      });
      throw error;
    }
  };
}
