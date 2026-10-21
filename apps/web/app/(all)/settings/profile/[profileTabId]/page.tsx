/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { PROFILE_SETTINGS, PROFILE_SETTINGS_TABS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TProfileSettingsTabs } from "@plane/types";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
import { PageHead } from "@/components/core/page-title";
import { ProfileSettingsContent } from "@/components/settings/profile/content";
import { ProfileSettingsSidebarRoot } from "@/components/settings/profile/sidebar";
// hooks
import { useUser } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
// local imports
import type { Route } from "../+types/layout";

function ProfileSettingsPage(props: Route.ComponentProps) {
  const { profileTabId } = props.params;
  // router
  const router = useAppRouter();
  // store hooks
  const { data: currentUser } = useUser();
  // translation
  const { t } = useTranslation();
  // derived values
  const isAValidTab = PROFILE_SETTINGS_TABS.includes(profileTabId as TProfileSettingsTabs);

  if (!currentUser || !isAValidTab)
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
      <div className="relative size-full">
        <div className="flex size-full">
          <ProfileSettingsSidebarRoot
            activeTab={profileTabId as TProfileSettingsTabs}
            className="w-[250px]"
            updateActiveTab={(tab) => router.push(`/settings/profile/${tab}`)}
          />
          <ProfileSettingsContent
            activeTab={profileTabId as TProfileSettingsTabs}
            className="mx-auto w-fit max-w-225 grow px-page-x py-20"
          />
        </div>
      </div>
    </>
  );
}

export default observer(ProfileSettingsPage);
