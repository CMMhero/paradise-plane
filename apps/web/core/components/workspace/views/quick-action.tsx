/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { MoreHorizontal } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IWorkspaceView } from "@plane/types";
import { ContextMenu, CustomMenu } from "@plane/ui";
import { copyUrlToClipboard, cn } from "@plane/utils";
// helpers
import { useViewMenuItems } from "@/components/common/quick-actions-helper";
// hooks
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { useIzinSumber } from "@/hooks/use-izin-sumber";
// local imports
import { DeleteGlobalViewModal } from "./delete-view-modal";
import { CreateUpdateWorkspaceViewModal } from "./modal";

type Props = {
  workspaceSlug: string;
  view: IWorkspaceView;
  /** Kustomisasi Paradise: ada = klik kanan pada baris membuka menu yang sama (seperti view departemen). */
  parentRef?: React.RefObject<HTMLElement>;
  customClassName?: string;
};

export const WorkspaceViewQuickActions = observer(function WorkspaceViewQuickActions(props: Props) {
  const { workspaceSlug, view, parentRef, customClassName } = props;
  // states
  const [updateViewModal, setUpdateViewModal] = useState(false);
  const [deleteViewModal, setDeleteViewModal] = useState(false);
  // store hooks
  const { data } = useUser();
  const { allowPermissions } = useUserPermissions();
  // auth
  const isOwner = view?.owned_by === data?.id;
  const isAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);
  // Paradise KEP-85: view workspace tanpa project; atasan dinilai server saja.
  const izin = useIzinSumber(workspaceSlug);

  const viewLink = `${workspaceSlug}/workspace-views/${view.id}`;
  const handleCopyText = async () => {
    await copyUrlToClipboard(viewLink);
    setToast({
      type: TOAST_TYPE.SUCCESS,
      title: "Link Copied!",
      message: "View link copied to clipboard.",
    });
  };

  const handleOpenInNewTab = () => window.open(`/${viewLink}`, "_blank");

  const MENU_ITEMS = useViewMenuItems({
    isOwner,
    isAdmin,
    isEditAllowed: izin.boleh("PERM_VIEW_EDIT", { pemilikId: view?.owned_by }),
    isDeleteAllowed: izin.boleh("PERM_VIEW_DELETE", { pemilikId: view?.owned_by }),
    handleDelete: () => setDeleteViewModal(true),
    handleEdit: () => setUpdateViewModal(true),
    handleOpenInNewTab,
    handleCopyLink: handleCopyText,
    workspaceSlug,
    view,
  });

  return (
    <>
      <CreateUpdateWorkspaceViewModal data={view} isOpen={updateViewModal} onClose={() => setUpdateViewModal(false)} />
      <DeleteGlobalViewModal data={view} isOpen={deleteViewModal} onClose={() => setDeleteViewModal(false)} />
      {parentRef && <ContextMenu parentRef={parentRef} items={MENU_ITEMS.items} />}
      <CustomMenu
        customButton={<IconButton variant="tertiary" size="lg" icon={MoreHorizontal} />}
        placement="bottom-end"
        closeOnSelect
        buttonClassName={customClassName}
      >
        {MENU_ITEMS.items.map((item) => {
          if (item.shouldRender === false) return null;
          return (
            <CustomMenu.MenuItem
              key={item.key}
              onClick={() => {
                item.action();
              }}
              className={cn(
                "flex items-center gap-2",
                {
                  "text-placeholder": item.disabled,
                },
                item.className
              )}
              disabled={item.disabled}
            >
              {item.icon && <item.icon className={cn("h-3 w-3", item.iconClassName)} />}
              <div>
                <h5>{item.title}</h5>
                {item.description && (
                  <p
                    className={cn("whitespace-pre-line text-tertiary", {
                      "text-placeholder": item.disabled,
                    })}
                  >
                    {item.description}
                  </p>
                )}
              </div>
            </CustomMenu.MenuItem>
          );
        })}
      </CustomMenu>
    </>
  );
});
