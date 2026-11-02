/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kredensial Google di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tab Google di menu API keys. Kredensial Google Calendar tinggal di sini;
 * saklar sinkronnya tetap di Features. Login Google memakai klien OAuth
 * sendiri (scope beda) dan tetap diatur di Authentication, di sini hanya
 * ditautkan.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { Section } from "@/components/common/paradise";
import { ApiKeysTabs } from "@/components/common/section-tabs";
// hooks
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// local
import { KredensialKalender } from "./kredensial-kalender";

const KredensialGooglePage = observer(function KredensialGooglePage(_props: Route.ComponentProps) {
  const { s } = useGodmodeStrings();
  const t = s.api_keys;
  const { formattedConfig, fetchInstanceConfigurations } = useInstance();

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  return (
    <PageWrapper header={{ title: t.title, description: t.google_description }}>
      <ApiKeysTabs />
      {formattedConfig ? (
        <div className="space-y-10">
          <Section title={t.gcal_title} description={t.gcal_note} bordered>
            <div className="px-4">
              <KredensialKalender config={formattedConfig} />
            </div>
          </Section>
          <Section title={t.signin_title} description={t.signin_note}>
            <Link href="/authentication/google/" className="text-13 font-medium text-accent-primary hover:underline">
              {t.signin_link}
            </Link>
          </Section>
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

export const meta: Route.MetaFunction = () => [{ title: "Google - God Mode" }];

export default KredensialGooglePage;
