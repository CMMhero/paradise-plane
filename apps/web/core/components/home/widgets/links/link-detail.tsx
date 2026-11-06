/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { observer } from "mobx-react";

import { useTranslation } from "@plane/i18n";
import { LinkIcon, NewTabIcon, EditIcon, TrashIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TContextMenuItem } from "@plane/ui";
import { LinkItemBlock } from "@plane/ui";
// plane utils
import { copyTextToClipboard } from "@plane/utils";
// components
import { usePratinjauTautan } from "@/components/pratinjau-tautan/kartu";
// hooks
import { useHome } from "@/hooks/store/use-home";
// types
import { getQuickLinkIcon, getQuickLinkImage, getQuickLinkTitle } from "./quick-link-display";
import { renderLogo } from "./quick-link-logo";
import type { TLinkOperations } from "./use-links";

export type TProjectLinkDetail = {
  linkId: string;
  linkOperations: TLinkOperations;
};

export const ProjectLinkDetail = observer(function ProjectLinkDetail(props: TProjectLinkDetail) {
  // props
  const { linkId, linkOperations } = props;
  // hooks
  const {
    quickLinks: { getLinkById, toggleLinkModal, setLinkData },
  } = useHome();
  const { t } = useTranslation();
  // derived values
  const linkDetail = getLinkById(linkId);
  const linkUrl = linkDetail?.url;
  // Link preview (description) from the shared link-preview endpoint. Asked only once the card
  // scrolls into view, so a long list does not fire one request per card at load.
  const cardRef = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);
  useEffect(() => {
    const node = cardRef.current;
    if (!node || isInView) return;
    if (typeof IntersectionObserver === "undefined") {
      setIsInView(true);
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        setIsInView(true);
        observer.disconnect();
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [isInView, linkDetail?.id]);
  const preview = usePratinjauTautan(isInView ? linkUrl : undefined);
  const previewDescription = preview && !preview.kosong ? preview.description?.trim() || undefined : undefined;

  // handlers
  const handleEdit = useCallback(
    (modalToggle: boolean) => {
      toggleLinkModal(modalToggle);
      setLinkData(linkDetail);
    },
    [linkDetail, setLinkData, toggleLinkModal]
  );

  const handleCopyText = useCallback(() => {
    if (!linkUrl) return;
    copyTextToClipboard(linkUrl).then(() =>
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("link_copied"),
        message: t("view_link_copied_to_clipboard"),
      })
    );
  }, [linkUrl, t]);

  const handleOpenInNewTab = useCallback(() => {
    window.open(linkUrl, "_blank", "noopener,noreferrer");
  }, [linkUrl]);

  const handleDelete = useCallback(() => {
    linkOperations.remove(linkId);
  }, [linkId, linkOperations]);

  // derived values
  const menuItems = useMemo<TContextMenuItem[]>(
    () => [
      {
        key: "edit",
        action: () => handleEdit(true),
        title: t("edit"),
        icon: EditIcon,
      },
      {
        key: "open-new-tab",
        action: handleOpenInNewTab,
        title: t("open_in_new_tab"),
        icon: NewTabIcon,
      },
      {
        key: "copy-link",
        action: handleCopyText,
        title: t("copy_link"),
        icon: LinkIcon,
      },
      {
        key: "delete",
        action: handleDelete,
        title: t("delete"),
        icon: TrashIcon,
      },
    ],
    [handleEdit, handleOpenInNewTab, handleCopyText, handleDelete, t]
  );

  if (!linkDetail) return null;

  return (
    <div ref={cardRef} className="min-w-0">
      <LinkItemBlock
        title={getQuickLinkTitle(linkDetail)}
        iconSrc={getQuickLinkIcon(linkDetail)}
        icon={renderLogo(linkDetail)}
        imageSrc={getQuickLinkImage(linkDetail)}
        url={linkDetail.url}
        createdAt={linkDetail.created_at}
        description={previewDescription}
        menuItems={menuItems}
        onClick={handleOpenInNewTab}
      />
    </div>
  );
});
