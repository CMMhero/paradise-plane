/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu menu "KPI" untuk tiga halaman yang dulu terpisah: KPI (semua orang),
 * Analitik dan Dasbor Divisi (admin, bukan Direktur). Halaman lamanya dipakai apa
 * adanya sebagai isi tab; URL lama (/analytics, /dashboard-divisi, /dashboards)
 * dialihkan ke sini oleh routes/redirects/core.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { Navigate, Outlet, useLocation, useParams } from "react-router";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { TabNavigationItem, TabNavigationList } from "@plane/propel/tab-navigation";
// components
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
import { useIsDirektur } from "@/hooks/use-is-direktur";
import { useParadiseModules } from "@/hooks/use-paradise-module";
// local imports
import { KinerjaHeader } from "./header";

type TKinerjaTab = "kpi" | "analitik" | "dasbor";

/** Tab aktif menurut path; "kpi" untuk /kinerja dan segala yang bukan dua tab lainnya. */
const tabFromPath = (pathname: string): TKinerjaTab => {
  if (/\/kinerja\/analitik(\/|$)/.test(pathname)) return "analitik";
  if (/\/kinerja\/dasbor(\/|$)/.test(pathname)) return "dasbor";
  return "kpi";
};

function KinerjaLayout() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { workspaceSlug } = useParams();
  const { allowPermissions } = useUserPermissions();
  const { isModuleEnabled } = useParadiseModules();
  const { isDirektur, isResolved } = useIsDirektur(workspaceSlug);

  const slug = workspaceSlug ?? "";
  const activeTab = tabFromPath(pathname);
  // Gerbang tab sama dengan gerbang menu lamanya: admin workspace. Direktur tidak
  // memakai Analitik dan Dasbor. Analitik juga ikut sakelar modul di God Mode.
  const isAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE, slug);
  const canSeeExtraTabs = isAdmin && isResolved && !isDirektur;

  const tabs: { key: TKinerjaTab; label: string; href: string }[] = [
    { key: "kpi", label: t("kinerja.tab_kpi"), href: `/${slug}/kinerja` },
  ];
  if (canSeeExtraTabs && isModuleEnabled("analytics"))
    tabs.push({ key: "analitik", label: t("kinerja.tab_analytics"), href: `/${slug}/kinerja/analitik/overview` });
  if (canSeeExtraTabs)
    tabs.push({ key: "dasbor", label: t("kinerja.tab_dashboards"), href: `/${slug}/kinerja/dasbor` });

  // Direktur tidak boleh membuka Analitik dan Dasbor lewat URL langsung.
  if (isDirektur && activeTab !== "kpi") return <Navigate to={`/${slug}/kinerja`} replace />;
  // Tunggu profil terbaca sebelum merender dua tab itu, supaya Direktur tidak sempat melihat isinya.
  const isWaitingForRole = activeTab !== "kpi" && !isResolved;

  return (
    <>
      <AppHeader header={<KinerjaHeader />} />
      <div className="flex min-h-0 flex-1 flex-col">
        {tabs.length > 1 && (
          <nav aria-label={t("kinerja.tabs_label")} className="shrink-0 border-b border-subtle bg-surface-1 px-6 py-2">
            <TabNavigationList>
              {tabs.map((tab) => (
                <Link
                  key={tab.key}
                  href={tab.href}
                  aria-current={activeTab === tab.key ? "page" : undefined}
                  className="rounded-item outline-none focus-visible:ring-2 focus-visible:ring-accent-strong"
                >
                  <TabNavigationItem isActive={activeTab === tab.key}>
                    <span>{tab.label}</span>
                  </TabNavigationItem>
                </Link>
              ))}
            </TabNavigationList>
          </nav>
        )}
        <div className="min-h-0 flex-1">
          <ContentWrapper>{isWaitingForRole ? null : <Outlet />}</ContentWrapper>
        </div>
      </div>
    </>
  );
}

export default observer(KinerjaLayout);
