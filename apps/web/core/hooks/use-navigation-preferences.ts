/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import type {
  TPersonalNavigationItemKey,
  TPersonalNavigationPreferences,
  TProjectNavigationPreferences,
  TProjectNavigationMode,
  TWorkspaceNavigationPreferences,
  TWorkspaceNavigationItemState,
  TAppRailPreferences,
  TAppRailDisplayMode,
} from "@plane/types";
import {
  DEFAULT_PERSONAL_PREFERENCES,
  DEFAULT_PROJECT_PREFERENCES,
  DEFAULT_WORKSPACE_PREFERENCES,
  DEFAULT_APP_RAIL_PREFERENCES,
} from "@plane/types";
import { isParadiseModuleEnabled } from "@/lib/paradise-modules";
import { useInstance } from "./store/use-instance";
import { useWorkspace } from "./store/use-workspace";
import useLocalStorage from "./use-local-storage";

const APP_RAIL_PREFERENCES_KEY = "app_rail_preferences";

export const usePersonalNavigationPreferences = () => {
  const { workspaceSlug } = useParams();
  const { getNavigationPreferences, updateBulkSidebarPreferences } = useWorkspace();

  // Get preferences from the store
  const storePreferences = getNavigationPreferences(workspaceSlug?.toString() || "");

  // Convert store format to hook format for personal items
  const preferences: TPersonalNavigationPreferences = useMemo(() => {
    if (!storePreferences) {
      return DEFAULT_PERSONAL_PREFERENCES;
    }

    // Extract personal items from the store (stickies, your_work, drafts)
    const personalItems: Record<TPersonalNavigationItemKey, { enabled: boolean; sort_order: number }> = {
      stickies: {
        enabled: storePreferences.stickies?.is_pinned ?? DEFAULT_PERSONAL_PREFERENCES.items.stickies.enabled,
        sort_order: storePreferences.stickies?.sort_order ?? DEFAULT_PERSONAL_PREFERENCES.items.stickies.sort_order,
      },
      your_work: {
        enabled: storePreferences.your_work?.is_pinned ?? DEFAULT_PERSONAL_PREFERENCES.items.your_work.enabled,
        sort_order: storePreferences.your_work?.sort_order ?? DEFAULT_PERSONAL_PREFERENCES.items.your_work.sort_order,
      },
      drafts: {
        enabled: storePreferences.drafts?.is_pinned ?? DEFAULT_PERSONAL_PREFERENCES.items.drafts.enabled,
        sort_order: storePreferences.drafts?.sort_order ?? DEFAULT_PERSONAL_PREFERENCES.items.drafts.sort_order,
      },
      quick_links: {
        enabled: storePreferences.quick_links?.is_pinned ?? DEFAULT_PERSONAL_PREFERENCES.items.quick_links.enabled,
        sort_order:
          storePreferences.quick_links?.sort_order ?? DEFAULT_PERSONAL_PREFERENCES.items.quick_links.sort_order,
      },
    };

    return {
      items: personalItems,
    };
  }, [storePreferences]);

  const togglePersonalItem = useCallback(
    async (key: TPersonalNavigationItemKey, enabled: boolean) => {
      if (!workspaceSlug) return;

      const currentItem = preferences.items[key] || { enabled: false, sort_order: 0 };

      await updateBulkSidebarPreferences(workspaceSlug.toString(), [
        {
          key,
          is_pinned: enabled,
          sort_order: currentItem.sort_order,
        },
      ]);
    },
    [workspaceSlug, preferences, updateBulkSidebarPreferences]
  );

  const updatePersonalItemOrder = useCallback(
    async (items: Array<{ key: TPersonalNavigationItemKey; sortOrder: number }>) => {
      if (!workspaceSlug) return;

      const bulkData = items.map((item) => {
        const currentItem = preferences.items[item.key] || { enabled: true, sort_order: 0 };
        return {
          key: item.key,
          is_pinned: currentItem.enabled,
          sort_order: item.sortOrder,
        };
      });

      await updateBulkSidebarPreferences(workspaceSlug.toString(), bulkData);
    },
    [workspaceSlug, preferences, updateBulkSidebarPreferences]
  );

  const isPersonalItemEnabled = useCallback(
    (key: TPersonalNavigationItemKey): boolean => preferences.items[key]?.enabled ?? true,
    [preferences]
  );

  return {
    preferences,
    togglePersonalItem,
    updatePersonalItemOrder,
    isPersonalItemEnabled,
  };
};

/** Key of the `WorkspaceUserPreference` row that stores the member's choice for the department list. */
const DEPARTMENTS_PREFERENCE_KEY = "departments";

/**
 * The sidebar's department list (divisions > departments). Two switches: the
 * Super Admin's (God Mode > Visibility, module `departments`) and the member's own
 * (Customize navigation). The admin switch wins: a member's choice never turns on
 * what the instance turned off. Hiding is presentation only, access is unchanged.
 * No stored row (not loaded yet, or an old account) counts as shown.
 */
export const useDepartmentsMenu = () => {
  const { workspaceSlug } = useParams();
  const { config } = useInstance();
  const { getNavigationPreferences, updateBulkSidebarPreferences } = useWorkspace();

  const stored = getNavigationPreferences(workspaceSlug?.toString() || "")?.[DEPARTMENTS_PREFERENCE_KEY];
  const isAllowedByInstance = isParadiseModuleEnabled(config, "departments");
  const isChosenByMember = stored?.is_pinned ?? true;

  const setChosenByMember = useCallback(
    async (show: boolean) => {
      if (!workspaceSlug) return;
      await updateBulkSidebarPreferences(workspaceSlug.toString(), [
        { key: DEPARTMENTS_PREFERENCE_KEY, is_pinned: show, sort_order: stored?.sort_order ?? 0 },
      ]);
    },
    [workspaceSlug, stored?.sort_order, updateBulkSidebarPreferences]
  );

  return {
    /** What the sidebar renders. */
    isVisible: isAllowedByInstance && isChosenByMember,
    isAllowedByInstance,
    isChosenByMember,
    setChosenByMember,
  };
};

export const useProjectNavigationPreferences = () => {
  const { workspaceSlug } = useParams();
  const { getProjectNavigationPreferences, updateProjectNavigationPreferences } = useWorkspace();
  const { isVisible: isDepartmentsMenuVisible } = useDepartmentsMenu();

  // Get preferences from the store
  const storePreferences = getProjectNavigationPreferences(workspaceSlug?.toString() || "");

  // Computed preferences with fallback logic: API → defaults
  const storedPreferences: TProjectNavigationPreferences = useMemo(() => {
    // 1. Try API data first
    if (
      storePreferences &&
      (storePreferences.navigation_control_preference || storePreferences.navigation_project_limit !== undefined)
    ) {
      // Missing limit = show every project (0), never a silent limit of 10.
      const limit = storePreferences.navigation_project_limit ?? 0;

      return {
        navigationMode: storePreferences.navigation_control_preference || DEFAULT_PROJECT_PREFERENCES.navigationMode,
        limitedProjectsCount: limit > 0 ? limit : DEFAULT_PROJECT_PREFERENCES.limitedProjectsCount,
        showLimitedProjects: limit > 0, // Derived: 0 = false, >0 = true
      };
    }

    // 2. Fall back to defaults
    return DEFAULT_PROJECT_PREFERENCES;
  }, [storePreferences]);

  // Accordion mode puts a department's tabs inside the sidebar list. With the list
  // hidden there is nowhere to show them, so the tabs fall back to the horizontal bar.
  const preferences: TProjectNavigationPreferences = useMemo(
    () => (isDepartmentsMenuVisible ? storedPreferences : { ...storedPreferences, navigationMode: "TABBED" }),
    [isDepartmentsMenuVisible, storedPreferences]
  );

  // Update navigation mode
  const updateNavigationMode = useCallback(
    async (mode: TProjectNavigationMode) => {
      if (!workspaceSlug) return;

      await updateProjectNavigationPreferences(workspaceSlug.toString(), {
        navigation_control_preference: mode,
      });
    },
    [workspaceSlug, updateProjectNavigationPreferences]
  );

  // Update show limited projects
  const updateShowLimitedProjects = useCallback(
    async (show: boolean) => {
      if (!workspaceSlug) return;

      // When toggling off, set to 0; when toggling on, use current count or default
      const newLimit = show ? preferences.limitedProjectsCount || DEFAULT_PROJECT_PREFERENCES.limitedProjectsCount : 0;

      await updateProjectNavigationPreferences(workspaceSlug.toString(), {
        navigation_project_limit: newLimit,
      });
    },
    [workspaceSlug, updateProjectNavigationPreferences, preferences.limitedProjectsCount]
  );

  // Update limited projects count
  const updateLimitedProjectsCount = useCallback(
    async (count: number) => {
      if (!workspaceSlug) return;

      await updateProjectNavigationPreferences(workspaceSlug.toString(), {
        navigation_project_limit: count,
      });
    },
    [workspaceSlug, updateProjectNavigationPreferences]
  );

  return {
    preferences,
    /** The member's saved mode, even while the department list is hidden. */
    storedNavigationMode: storedPreferences.navigationMode,
    updateNavigationMode,
    updateShowLimitedProjects,
    updateLimitedProjectsCount,
  };
};

export const useWorkspaceNavigationPreferences = () => {
  const { workspaceSlug } = useParams();
  const { getNavigationPreferences, updateBulkSidebarPreferences } = useWorkspace();

  // Get preferences from the store
  const storePreferences = getNavigationPreferences(workspaceSlug?.toString() || "");

  // Convert store format to hook format
  const preferences: TWorkspaceNavigationPreferences = useMemo(() => {
    if (!storePreferences) {
      return DEFAULT_WORKSPACE_PREFERENCES;
    }

    return {
      items: storePreferences,
    };
  }, [storePreferences]);

  const toggleWorkspaceItem = useCallback(
    async (key: string, isPinned: boolean) => {
      if (!workspaceSlug) return;

      const currentItem = preferences.items[key] || { is_pinned: false, sort_order: 0 };

      await updateBulkSidebarPreferences(workspaceSlug.toString(), [
        {
          key,
          is_pinned: isPinned,
          sort_order: currentItem.sort_order,
        },
      ]);
    },
    [workspaceSlug, preferences, updateBulkSidebarPreferences]
  );

  const updateWorkspaceItemOrder = useCallback(
    async (items: Array<{ key: string; sortOrder: number }>) => {
      if (!workspaceSlug) return;

      const bulkData = items.map((item) => {
        const currentItem = preferences.items[item.key] || { is_pinned: true, sort_order: 0 };
        return {
          key: item.key,
          is_pinned: currentItem.is_pinned,
          sort_order: item.sortOrder,
        };
      });

      await updateBulkSidebarPreferences(workspaceSlug.toString(), bulkData);
    },
    [workspaceSlug, preferences, updateBulkSidebarPreferences]
  );

  const getWorkspaceItemState = useCallback(
    (key: string): TWorkspaceNavigationItemState => preferences.items[key] || { is_pinned: false, sort_order: 0 },
    [preferences]
  );

  const isWorkspaceItemPinned = useCallback(
    (key: string): boolean => {
      const state = getWorkspaceItemState(key);
      return state.is_pinned;
    },
    [getWorkspaceItemState]
  );

  const updateWorkspaceItemSortOrder = useCallback(
    async (key: string, sortOrder: number) => {
      if (!workspaceSlug) return;

      const currentItem = preferences.items[key] || { is_pinned: false, sort_order: 0 };

      await updateBulkSidebarPreferences(workspaceSlug.toString(), [
        {
          key,
          is_pinned: currentItem.is_pinned,
          sort_order: sortOrder,
        },
      ]);
    },
    [workspaceSlug, preferences, updateBulkSidebarPreferences]
  );

  return {
    preferences,
    toggleWorkspaceItem,
    updateWorkspaceItemOrder,
    updateWorkspaceItemSortOrder,
    getWorkspaceItemState,
    isWorkspaceItemPinned,
  };
};

export const useAppRailPreferences = () => {
  const { storedValue, setValue } = useLocalStorage<TAppRailPreferences>(
    APP_RAIL_PREFERENCES_KEY,
    DEFAULT_APP_RAIL_PREFERENCES
  );

  const updateDisplayMode = useCallback(
    (mode: TAppRailDisplayMode) => {
      setValue({
        displayMode: mode,
      });
    },
    [setValue]
  );

  const toggleDisplayMode = useCallback(() => {
    const currentPreferences = storedValue || DEFAULT_APP_RAIL_PREFERENCES;
    const newMode = currentPreferences.displayMode === "icon_only" ? "icon_with_label" : "icon_only";
    updateDisplayMode(newMode);
  }, [storedValue, updateDisplayMode]);

  return {
    preferences: storedValue || DEFAULT_APP_RAIL_PREFERENCES,
    updateDisplayMode,
    toggleDisplayMode,
  };
};
