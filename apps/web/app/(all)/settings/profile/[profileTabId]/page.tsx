/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
// plane imports
import { PROFILE_SETTINGS, PROFILE_SETTINGS_TABS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TProfileSettingsTabs } from "@plane/types";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
import { PageHead } from "@/components/core/page-title";
import { ProfileSettingsContent } from "@/components/settings/profile/content";
import { SettingsMobileNav } from "@/components/settings/mobile/nav";
import { ProfileSettingsSidebarRoot } from "@/components/settings/profile/sidebar";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
import { useUser, useUserSettings } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
import { isProfileTabAvailable, PROFILE_TAB_FALLBACK } from "@/lib/profile-tabs";
// local imports
import type { Route } from "../+types/layout";

// Isi hamburger di layar sempit: sidebar yang sama dengan desktop, menutup sendiri sesudah memilih tab.
const ProfileSettingsMobileSidebar = observer(function ProfileSettingsMobileSidebar(props: { className?: string }) {
  const { profileTabId } = useParams();
  const router = useAppRouter();
  const { toggleSidebar } = useUserSettings();
  return (
    <ProfileSettingsSidebarRoot
      activeTab={profileTabId as TProfileSettingsTabs}
      className={`w-[250px] ${props.className ?? ""}`}
      updateActiveTab={(tab) => {
        toggleSidebar(true);
        router.push(`/settings/profile/${tab}`);
      }}
    />
  );
});

function ProfileSettingsPage(props: Route.ComponentProps) {
  const { profileTabId } = props.params;
  // router
  const router = useAppRouter();
  // store hooks
  const { data: currentUser } = useUser();
  const { config } = useInstance();
  // translation
  const { t } = useTranslation();
  // derived values
  const isAValidTab = PROFILE_SETTINGS_TABS.includes(profileTabId as TProfileSettingsTabs);
  // Tab yang ada tapi tak tersedia di instance ini (mis. Connections tanpa
  // kredensial Google) dialihkan, bukan dibiarkan memutar spinner selamanya.
  const isTabUnavailable = isAValidTab && !isProfileTabAvailable(config, profileTabId as TProfileSettingsTabs);

  useEffect(() => {
    if (isTabUnavailable) router.replace(`/settings/profile/${PROFILE_TAB_FALLBACK}`);
  }, [isTabUnavailable, router]);

  if (!currentUser || !isAValidTab || isTabUnavailable)
    return (
      <div className="grid size-full place-items-center px-4">
        <LogoSpinner />
      </div>
    );

  return (
    <>
      {/* Judulnya mengikuti TAB yang sedang dibuka. Sebelumnya dipatok
          "General settings" untuk keempat tab, jadi tiga di antaranya menulis
          judul yang salah di tab peramban, bookmark, dan riwayat. Isinya sendiri
          selalu benar; hanya judulnya yang tertinggal.
          Memakai `i18n_label` dari PROFILE_SETTINGS, kunci yang SUDAH ADA dan
          sudah dipakai sidebar di sebelahnya, jadi nol berkas locale disentuh
          dan judulnya pasti sama dengan tulisan di menu. */}
      <PageHead
        title={`${t("profile.label")} - ${t(PROFILE_SETTINGS[profileTabId as TProfileSettingsTabs].i18n_label)}`}
      />
      <div className="relative flex size-full flex-col">
        <SettingsMobileNav
          hamburgerContent={ProfileSettingsMobileSidebar}
          activePath={PROFILE_SETTINGS[profileTabId as TProfileSettingsTabs].i18n_label}
        />
        <div className="flex size-full min-h-0">
          <ProfileSettingsSidebarRoot
            activeTab={profileTabId as TProfileSettingsTabs}
            className="hidden w-[250px] md:block"
            updateActiveTab={(tab) => router.push(`/settings/profile/${tab}`)}
          />
          <ProfileSettingsContent
            activeTab={profileTabId as TProfileSettingsTabs}
            className="mx-auto w-fit max-w-225 min-w-0 grow px-page-x py-6 md:py-20"
          />
        </div>
      </div>
    </>
  );
}

export default observer(ProfileSettingsPage);
