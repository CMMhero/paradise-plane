/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Work rules > Archiving
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Both archive rules on one screen (KEP-83): the instance ceiling in days and
 * the per-project timing in months a new project starts with.
 */

import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { PageWrapper } from "@/components/common/page-wrapper";
import { MenuTabs } from "@/components/common/section-tabs";
import { ProjectArchiveDefaults } from "@/components/settings/project-archive-defaults";
import { SettingsTabForm } from "@/components/settings/settings-tab-form";

export default function ArchivingPage() {
  const { s } = useGodmodeStrings();
  const header = s.settings.tabs.rules_archiving;

  return (
    <PageWrapper header={header}>
      <MenuTabs menu="rules" />
      <SettingsTabForm
        tab="rules_archiving"
        tabTitle={header.title}
        intro={<p className="text-12 font-medium text-primary">{s.settings.archiving.ceiling_hint}</p>}
        after={<ProjectArchiveDefaults />}
      />
    </PageWrapper>
  );
}

export const meta = () => [{ title: `${godmodeStrings.settings.tabs.rules_archiving.title} - God Mode` }];
