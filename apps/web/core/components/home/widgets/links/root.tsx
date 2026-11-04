/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";

import { useTranslation } from "@plane/i18n";
import { PlusIcon } from "@plane/propel/icons";
import type { THomeWidgetProps } from "@plane/types";
import { useHome } from "@/hooks/store/use-home";
import { LinkCreateUpdateModal } from "./create-update-link-modal";
import { ProjectLinkList } from "./links";
import { SharedQuickLinks } from "./shared-links";
import { useLinks } from "./use-links";

export const DashboardQuickLinks = observer(function DashboardQuickLinks(props: THomeWidgetProps) {
  const { workspaceSlug } = props;
  const { linkOperations } = useLinks(workspaceSlug);
  const {
    quickLinks: { toggleLinkModal, setLinkData, fetchLinks },
  } = useHome();
  const { t } = useTranslation();

  const handleCreateLinkModal = useCallback(() => {
    toggleLinkModal(true);
    setLinkData(undefined);
  }, [toggleLinkModal, setLinkData]);

  useSWR(
    workspaceSlug ? `HOME_LINKS_${workspaceSlug}` : null,
    workspaceSlug ? () => fetchLinks(workspaceSlug.toString()) : null,
    {
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );
  return (
    <>
      <LinkCreateUpdateModal workspaceSlug={workspaceSlug} linkOperations={linkOperations} />
      <div className="mb-2">
        <div className="mb-4 flex items-center justify-between">
          <div className="text-14 font-semibold text-tertiary">{t("home.quick_links.title_plural")}</div>
          <button
            onClick={handleCreateLinkModal}
            className="my-auto flex gap-1 text-13 font-medium text-accent-primary"
          >
            <PlusIcon className="my-auto size-4" /> <span>{t("home.quick_links.add")}</span>
          </button>
        </div>
        {/* Paradise KEP-82: links shared by admins come first. */}
        <SharedQuickLinks workspaceSlug={workspaceSlug} />
        <div className="w-full">
          {/* rendering links */}
          <ProjectLinkList workspaceSlug={workspaceSlug} linkOperations={linkOperations} />
        </div>
      </div>
    </>
  );
});
