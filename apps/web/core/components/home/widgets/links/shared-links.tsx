/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise KEP-82: quick links shared by admins, shown above each person's own links.
import { useMemo } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { EditIcon, LinkIcon, NewTabIcon, TrashIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TSharedQuickLink, TSharedQuickLinkDivision } from "@plane/types";
import type { TContextMenuItem } from "@plane/ui";
import { LinkItemBlock } from "@plane/ui";
import { copyTextToClipboard } from "@plane/utils";
import { useHome } from "@/hooks/store/use-home";
import { useKonfirmasi } from "@/hooks/use-konfirmasi";
import { QUICK_LINK_GRID_CLASS, getQuickLinkIcon, getQuickLinkImage, getQuickLinkTitle } from "./quick-link-display";
import { renderLogo } from "./quick-link-logo";

export const sharedQuickLinksKey = (workspaceSlug: string) => `HOME_SHARED_LINKS_${workspaceSlug}`;

type Props = {
  workspaceSlug: string;
  /** Quick links page: admins see and manage every shared link, not only the ones aimed at them. */
  isManageView?: boolean;
};

/** "Everyone" or the unit codes a link is aimed at, for admins deciding what to edit. */
const describeAudience = (
  link: TSharedQuickLink,
  divisions: TSharedQuickLinkDivision[],
  t: (key: string) => string
): string => {
  if (link.cakupan === "semua") return t("quick_links_ui.audience_everyone_short");
  const codes = [
    ...divisions.filter((d) => link.divisi_ids.includes(d.id)).map((d) => d.kode),
    ...divisions
      .flatMap((d) => d.departemen)
      .filter((dep) => link.departemen_ids.includes(dep.id))
      .map((dep) => dep.kode),
  ];
  return codes.length > 0 ? codes.join(", ") : t("quick_links_ui.audience_nobody");
};

export const SharedQuickLinks = observer(function SharedQuickLinks({ workspaceSlug, isManageView = false }: Props) {
  const { t } = useTranslation();
  const {
    quickLinks: { fetchSharedLinks, getSharedLinks, openSharedLinkModal, removeSharedLink },
  } = useHome();
  const { minta, dialog } = useKonfirmasi();

  useSWR(workspaceSlug ? sharedQuickLinksKey(workspaceSlug) : null, () => fetchSharedLinks(workspaceSlug), {
    revalidateIfStale: false,
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  });

  const data = getSharedLinks(workspaceSlug);
  const canManage = Boolean(data?.boleh_kelola);
  const links = (isManageView && canManage ? data?.semua : data?.links) ?? [];
  const divisions = useMemo(() => data?.organisasi ?? [], [data?.organisasi]);

  if (!data) return null;
  if (links.length === 0 && !(isManageView && canManage)) return null;

  const menuFor = (link: TSharedQuickLink): TContextMenuItem[] => {
    const items: TContextMenuItem[] = [
      {
        key: "open-new-tab",
        action: () => window.open(link.url, "_blank", "noopener,noreferrer"),
        title: t("open_in_new_tab"),
        icon: NewTabIcon,
      },
      {
        key: "copy-link",
        action: () =>
          void copyTextToClipboard(link.url).then(() =>
            setToast({ type: TOAST_TYPE.SUCCESS, title: t("link_copied"), message: t("view_link_copied_to_clipboard") })
          ),
        title: t("copy_link"),
        icon: LinkIcon,
      },
    ];
    if (!canManage) return items;
    return [
      { key: "edit", action: () => openSharedLinkModal(link), title: t("edit"), icon: EditIcon },
      ...items,
      {
        key: "delete",
        action: () =>
          minta(
            {
              judul: t("quick_links_ui.delete_title"),
              isi: t("quick_links_ui.delete_body"),
            },
            async () => {
              try {
                await removeSharedLink(workspaceSlug, link.id);
                setToast({ type: TOAST_TYPE.SUCCESS, title: t("quick_links_ui.removed") });
              } catch {
                setToast({ type: TOAST_TYPE.ERROR, title: t("quick_links_ui.remove_failed") });
              }
            }
          ),
        title: t("delete"),
        icon: TrashIcon,
      },
    ];
  };

  return (
    <section className="mb-4" aria-label={t("quick_links_ui.shared_title")}>
      <div className="mb-2 text-12 font-medium text-tertiary">{t("quick_links_ui.shared_title")}</div>
      {links.length === 0 ? (
        <p className="text-13 text-tertiary">{t("quick_links_ui.shared_empty_admin")}</p>
      ) : (
        <div className={QUICK_LINK_GRID_CLASS}>
          {links.map((link) => (
            <LinkItemBlock
              key={link.id}
              title={getQuickLinkTitle(link)}
              iconSrc={getQuickLinkIcon(link)}
              icon={renderLogo(link)}
              imageSrc={getQuickLinkImage(link)}
              url={link.url}
              description={canManage ? describeAudience(link, divisions, t) : t("quick_links_ui.shared_by_admin")}
              menuItems={menuFor(link)}
              onClick={() => window.open(link.url, "_blank", "noopener,noreferrer")}
            />
          ))}
        </div>
      )}
      {dialog}
    </section>
  );
});
