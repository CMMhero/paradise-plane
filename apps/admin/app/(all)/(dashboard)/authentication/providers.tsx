/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Sign-in & access > Providers
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { AuthModeList } from "@/components/authentication/auth-mode-list";
import { PageWrapper } from "@/components/common/page-wrapper";
import { MenuTabs } from "@/components/common/section-tabs";

export default function AccessProvidersPage() {
  const { s } = useGodmodeStrings();
  return (
    <PageWrapper header={s.settings.tabs.access_providers}>
      <MenuTabs menu="access" />
      <div className="space-y-4">
        <p className="text-11 text-tertiary">
          {s.settings.access.google_link}{" "}
          <Link href="/integrations/" className="font-medium text-accent-primary hover:underline">
            {s.settings.access.google_open}
          </Link>
        </p>
        <AuthModeList modes={["google", "github", "gitlab", "gitea"]} />
      </div>
    </PageWrapper>
  );
}

export const meta = () => [{ title: `${godmodeStrings.settings.tabs.access_providers.title} - God Mode` }];
