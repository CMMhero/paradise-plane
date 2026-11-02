/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { EmptyStateDetailed } from "@plane/propel/empty-state";
// components
import { PageHead } from "@/components/core/page-title";
import { LinkCreateUpdateModal } from "@/components/home/widgets/links/create-update-link-modal";
import { ProjectLinkDetail } from "@/components/home/widgets/links/link-detail";
import { useLinks } from "@/components/home/widgets/links/use-links";
import { EWidgetKeys, WidgetLoader } from "@/components/home/widgets/loaders";
// hooks
import { useHome } from "@/hooks/store/use-home";

// Kunci SWR SAMA dengan widget Home, jadi cache-nya dipakai bersama.
const quickLinksKey = (workspaceSlug: string) => `HOME_LINKS_${workspaceSlug}`;

function WorkspaceQuickLinksPage() {
  const { workspaceSlug: routeSlug } = useParams();
  const workspaceSlug = routeSlug?.toString() ?? "";
  const { t } = useTranslation();
  const { linkOperations } = useLinks(workspaceSlug);
  const {
    quickLinks: { isLinkModalOpen, toggleLinkModal, linkData, setLinkData, fetchLinks, getLinksByWorkspaceId },
  } = useHome();

  const handleAdd = () => {
    setLinkData(undefined);
    toggleLinkModal(true);
  };

  useSWR(workspaceSlug ? quickLinksKey(workspaceSlug) : null, () => fetchLinks(workspaceSlug), {
    revalidateIfStale: false,
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  });

  const links = getLinksByWorkspaceId(workspaceSlug);

  return (
    <>
      <PageHead title={t("home.quick_links.title_plural")} />
      <LinkCreateUpdateModal
        isModalOpen={isLinkModalOpen}
        handleOnClose={() => toggleLinkModal(false)}
        linkOperations={linkOperations}
        preloadedData={linkData}
      />
      {links?.length === 0 ? (
        // Kosong: templat halaman penuh yang sama dengan Drafts, Projects, dst.
        <div className="relative h-full w-full overflow-y-auto">
          <EmptyStateDetailed
            title={t("workspace_empty_state.home_widget_quick_links.title")}
            description={t("home.quick_links.empty")}
            assetKey="link"
            actions={[{ label: t("home.quick_links.add"), onClick: handleAdd, variant: "primary" }]}
          />
        </div>
      ) : (
        <div className="relative h-full w-full overflow-y-auto px-page-x py-6">
          {links === undefined ? (
            <WidgetLoader widgetKey={EWidgetKeys.QUICK_LINKS} />
          ) : (
            <div className="flex flex-wrap gap-2">
              {links.map((linkId) => (
                <ProjectLinkDetail key={linkId} linkId={linkId} linkOperations={linkOperations} />
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}

export default observer(WorkspaceQuickLinksPage);
