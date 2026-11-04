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
import { QUICK_LINK_GRID_CLASS } from "@/components/home/widgets/links/quick-link-display";
import { SharedQuickLinks } from "@/components/home/widgets/links/shared-links";
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
    quickLinks: { toggleLinkModal, setLinkData, fetchLinks, getLinksByWorkspaceId, getSharedLinks },
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
  // Paradise KEP-82: the full-page empty state only when there is nothing at all to show.
  const shared = getSharedLinks(workspaceSlug);
  const hasSharedSection = Boolean(shared && (shared.links.length > 0 || shared.boleh_kelola));

  return (
    <>
      <PageHead title={t("home.quick_links.title_plural")} />
      <LinkCreateUpdateModal workspaceSlug={workspaceSlug} linkOperations={linkOperations} />
      {links?.length === 0 && !hasSharedSection ? (
        // Kosong: templat halaman penuh yang sama dengan Drafts, Projects, dst.
        <div className="relative h-full w-full overflow-y-auto">
          <SharedQuickLinks workspaceSlug={workspaceSlug} isManageView />
          <EmptyStateDetailed
            title={t("workspace_empty_state.home_widget_quick_links.title")}
            description={t("home.quick_links.empty")}
            assetKey="link"
            actions={[{ label: t("home.quick_links.add"), onClick: handleAdd, variant: "primary" }]}
          />
        </div>
      ) : (
        <div className="relative h-full w-full overflow-y-auto px-page-x py-6">
          <SharedQuickLinks workspaceSlug={workspaceSlug} isManageView />
          {hasSharedSection && (
            <div className="mb-2 text-12 font-medium text-tertiary">{t("quick_links_ui.my_links")}</div>
          )}
          {links === undefined ? (
            <WidgetLoader widgetKey={EWidgetKeys.QUICK_LINKS} />
          ) : links.length === 0 ? (
            <p className="text-13 text-tertiary">{t("home.quick_links.empty")}</p>
          ) : (
            <div className={QUICK_LINK_GRID_CLASS}>
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
