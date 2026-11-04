/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { AccessForm } from "@/components/authentication/access-form";
import { AuthModeList } from "@/components/authentication/auth-mode-list";
import { PageWrapper } from "@/components/common/page-wrapper";
import { MenuTabs } from "@/components/common/section-tabs";
import type { Route } from "./+types/page";

const AccessMethodsPage = observer(function AccessMethodsPage(_props: Route.ComponentProps) {
  const { s } = useGodmodeStrings();
  return (
    <PageWrapper header={s.settings.tabs.access_methods}>
      <MenuTabs menu="access" />
      <div className="space-y-8">
        <AccessForm />
        <div className="space-y-3">
          <div className="text-16 font-medium text-primary">{s.settings.access.methods_title}</div>
          <AuthModeList modes={["unique-codes", "passwords-login"]} />
        </div>
      </div>
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [
  { title: `${godmodeStrings.settings.tabs.access_methods.title} - God Mode` },
];

export default AccessMethodsPage;
