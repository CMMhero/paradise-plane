/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { Earth, Info, Minus, Plus } from "lucide-react";
// plane imports
import { LockIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import type { TPage } from "@plane/types";
import { Avatar, FavoriteStar } from "@plane/ui";
import { renderFormattedDate, getFileURL } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useAppRouter } from "@/hooks/use-app-router";
import { usePageOperations } from "@/hooks/use-page-operations";
// plane web hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
// store
import type { TPageInstance } from "@/store/pages/base-page";
// local imports
import { PageActions } from "../dropdowns";

type Props = {
  page: TPageInstance;
  parentRef: React.RefObject<HTMLElement>;
  storeType: EPageStoreType;
};

export const BlockItemAction = observer(function BlockItemAction(props: Props) {
  const { page, parentRef, storeType } = props;
  // states
  const [isCreatingSubPage, setIsCreatingSubPage] = useState(false);
  // store hooks
  const { getUserDetails } = useMember();
  const { createPage } = usePageStore(EPageStoreType.PROJECT);
  // router
  const router = useAppRouter();
  const { workspaceSlug } = useParams();
  // page operations
  const { pageOperations } = usePageOperations({
    page,
  });
  // derived values
  const { access, created_at, id, is_favorite, owned_by, project_ids, canCurrentUserFavoritePage } = page;
  const ownerDetails = owned_by ? getUserDetails(owned_by) : undefined;
  // sub-halaman mewarisi akses induknya; kalau tidak, halaman anak dari folder
  // privat bisa lahir sebagai publik tanpa disadari siapa pun
  const handleCreateSubPage = async () => {
    if (!id || isCreatingSubPage) return;
    setIsCreatingSubPage(true);
    const payload: Partial<TPage> = { parent: id, access };
    try {
      const res = await createPage(payload);
      const projectId = project_ids?.[0];
      if (res?.id && projectId) {
        router.push(`/${workspaceSlug}/projects/${projectId}/pages/${res.id}`);
      }
    } catch (error) {
      const message = (error as { data?: { error?: string } })?.data?.error;
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: message || "Sub-halaman gagal dibuat. Coba lagi.",
      });
    } finally {
      setIsCreatingSubPage(false);
    }
  };

  return (
    <>
      {/* page details */}
      <div className="cursor-default">
        <Tooltip tooltipHeading="Owned by" tooltipContent={ownerDetails?.display_name}>
          <Avatar src={getFileURL(ownerDetails?.avatar_url ?? "")} name={ownerDetails?.display_name} />
        </Tooltip>
      </div>
      <div className="cursor-default text-tertiary">
        <Tooltip tooltipContent={access === 0 ? "Public" : "Private"}>
          {access === 0 ? <Earth className="h-4 w-4" /> : <LockIcon className="h-4 w-4" />}
        </Tooltip>
      </div>
      {/* vertical divider */}
      <Minus className="-mx-3 h-5 w-5 rotate-90 text-placeholder" strokeWidth={1} />

      {/* page info */}
      <Tooltip tooltipContent={`Created on ${renderFormattedDate(created_at)}`}>
        <span className="grid h-4 w-4 cursor-default place-items-center">
          <Info className="h-4 w-4 text-tertiary" />
        </span>
      </Tooltip>

      {/* tambah sub-halaman */}
      <Tooltip tooltipContent="Tambah sub-halaman">
        <button
          type="button"
          onClick={(e) => {
            // tombol ini duduk di dalam baris yang bisa diklik; tanpa kedua
            // penahan ini, membuat sub-halaman juga membuka halaman induknya
            e.preventDefault();
            e.stopPropagation();
            void handleCreateSubPage();
          }}
          disabled={isCreatingSubPage}
          className="grid size-5 place-items-center rounded text-tertiary transition-colors hover:bg-layer-3-hover hover:text-secondary disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Tambah sub-halaman"
        >
          <Plus className="size-4" />
        </button>
      </Tooltip>

      {/* favorite/unfavorite */}
      {canCurrentUserFavoritePage && (
        <FavoriteStar
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            pageOperations.toggleFavorite();
          }}
          selected={is_favorite}
        />
      )}

      {/* quick actions dropdown */}
      <PageActions
        optionsOrder={[
          "open-in-new-tab",
          "copy-link",
          "make-a-copy",
          "toggle-lock",
          "toggle-access",
          "archive-restore",
          "delete",
        ]}
        page={page}
        parentRef={parentRef}
        storeType={storeType}
      />
    </>
  );
});
