/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { EUserPermissions, EUserPermissionsLevel, IS_FAVORITE_MENU_OPEN } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
import type { IProjectView } from "@plane/types";
import { FavoriteStar } from "@plane/ui";
import { getPublishViewLink } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useProjectView } from "@/hooks/store/use-project-view";
import { useUserPermissions } from "@/hooks/store/user";
// plane web imports
import { PublishViewModal } from "@/plane-web/components/views/publish";
// local imports
import { ViewQuickActions } from "./quick-actions";
import { ViewListItemMeta } from "./view-list-item-meta";

type Props = {
  parentRef: React.RefObject<HTMLElement>;
  view: IProjectView;
  /** Kustomisasi Paradise: halaman Views workspace menandai departemen tiap baris. */
  showScope?: boolean;
};

export const ViewListItemAction = observer(function ViewListItemAction(props: Props) {
  const { parentRef, view, showScope = false } = props;
  // states
  const [isPublishModalOpen, setPublishModalOpen] = useState<boolean>(false);
  // router
  const { workspaceSlug } = useParams();
  // Kustomisasi Paradise: departemen diambil dari view, bukan dari URL, supaya baris yang
  // sama bisa tampil di halaman Views workspace (tanpa projectId di URL).
  const projectId = view.project;
  // store
  const { allowPermissions } = useUserPermissions();

  const { addViewToFavorites, removeViewFromFavorites } = useProjectView();
  const { getUserDetails } = useMember();

  // local storage
  const { setValue: toggleFavoriteMenu, storedValue: isFavoriteOpen } = useLocalStorage<boolean>(
    IS_FAVORITE_MENU_OPEN,
    false
  );

  // derived values
  const isEditingAllowed = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug?.toString(),
    projectId
  );

  const publishLink = getPublishViewLink(view?.anchor);

  // handlers
  const handleAddToFavorites = async () => {
    if (!workspaceSlug || !projectId) return;

    await addViewToFavorites(workspaceSlug.toString(), projectId, view.id);
    if (!isFavoriteOpen) toggleFavoriteMenu(true);
  };

  const handleRemoveFromFavorites = () => {
    if (!workspaceSlug || !projectId) return;

    removeViewFromFavorites(workspaceSlug.toString(), projectId, view.id);
  };

  const ownedByDetails = view.owned_by ? getUserDetails(view.owned_by) : undefined;

  return (
    <>
      <PublishViewModal isOpen={isPublishModalOpen} onClose={() => setPublishModalOpen(false)} view={view} />

      {view?.anchor && publishLink ? (
        <button
          type="button"
          className="flex cursor-pointer items-center gap-1.5 rounded-sm bg-success-subtle px-3 py-1.5 text-11 font-medium text-success-primary"
          onClick={() => setPublishModalOpen(true)}
        >
          <span className="size-1.5 flex-shrink-0 rounded-full bg-success-primary" />
          Live
        </button>
      ) : (
        <></>
      )}

      <ViewListItemMeta
        access={view.access}
        ownerId={ownedByDetails?.id}
        scope={showScope ? { projectId } : undefined}
      />

      {isEditingAllowed && (
        <FavoriteStar
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            if (view.is_favorite) handleRemoveFromFavorites();
            else handleAddToFavorites();
          }}
          selected={view.is_favorite}
        />
      )}
      {projectId && workspaceSlug && (
        <div className="hidden md:block">
          <ViewQuickActions
            parentRef={parentRef}
            projectId={projectId}
            view={view}
            workspaceSlug={workspaceSlug.toString()}
          />
        </div>
      )}
    </>
  );
});
