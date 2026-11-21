/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Work rules > All rules
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Every God Mode rule on one screen, by topic. The registry lives in
 * apps/api/plane/utils/aturan; the screen is components/rules/rules-screen.tsx.
 */

import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { PageWrapper } from "@/components/common/page-wrapper";
import { MenuTabs } from "@/components/common/section-tabs";
import { RulesScreen } from "@/components/rules/rules-screen";

export default function AllRulesPage() {
  const { s } = useGodmodeStrings();

  return (
    <PageWrapper header={s.settings.tabs.rules_all}>
      <MenuTabs menu="rules" />
      <RulesScreen />
    </PageWrapper>
  );
}

export const meta = () => [{ title: `${godmodeStrings.settings.tabs.rules_all.title} - God Mode` }];
