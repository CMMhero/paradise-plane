/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Integrations > Google
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Everything Google on one page (KEP-83): the sign-in OAuth client, the Calendar
 * OAuth client, and the Calendar sync switch. Sign-in and Calendar keep separate
 * clients because their scopes differ; the sync switch cannot be turned on
 * until the Calendar credentials are filled in.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { Section } from "@/components/common/paradise";
import { MenuTabs } from "@/components/common/section-tabs";
import { SettingsTabForm } from "@/components/settings/settings-tab-form";
// hooks
import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// local
import { InstanceGoogleConfigForm } from "../authentication/google/form";
import { KredensialKalender } from "./kredensial-kalender";

const GooglePage = observer(function GooglePage(_props: Route.ComponentProps) {
  const { s } = useGodmodeStrings();
  const t = s.settings;
  const { formattedConfig, fetchInstanceConfigurations } = useInstance();

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  const hasCalendarCredentials = Boolean(
    formattedConfig?.GOOGLE_CALENDAR_CLIENT_ID && formattedConfig?.GOOGLE_CALENDAR_CLIENT_SECRET
  );

  return (
    <PageWrapper header={t.tabs.integrations_google}>
      <MenuTabs menu="integrations" />
      {formattedConfig ? (
        <div className="space-y-10">
          <Section title={t.sections.google_signin.title} description={t.google.signin_help}>
            <InstanceGoogleConfigForm config={formattedConfig} hideBack />
          </Section>
          <Section title={t.google.calendar_credentials} bordered>
            <div className="px-4">
              <KredensialKalender config={formattedConfig} />
            </div>
          </Section>
          <SettingsTabForm
            tab="integrations_google"
            tabTitle={t.tabs.integrations_google.title}
            blockedOn={hasCalendarCredentials ? undefined : { ENABLE_GOOGLE_CALENDAR_SYNC: t.google.calendar_missing }}
          />
        </div>
      ) : (
        <Loader className="space-y-8">
          <Loader.Item height="50px" width="50%" />
          <Loader.Item height="50px" width="20%" />
        </Loader>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [
  { title: `${godmodeStrings.settings.tabs.integrations_google.title} - God Mode` },
];

export default GooglePage;
