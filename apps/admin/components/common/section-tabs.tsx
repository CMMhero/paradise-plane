/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tabs for grouped God Mode menus
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * One sidebar entry, several pages. Members groups accounts, organization
 * structure, and new member defaults; Logs groups sign-in activity, the audit
 * log, and the trash; API keys groups AI, image library, and Google credentials.
 */

import { useGodmodeStrings } from "@/app/i18n/godmode";
import { PageTabs } from "./paradise";

export function MembersTabs() {
  const { s } = useGodmodeStrings();
  return (
    <PageTabs
      tabs={[
        { label: s.nav.members_accounts, href: "/members/" },
        { label: s.nav.members_organization, href: "/members/organization/" },
        { label: s.nav.members_defaults, href: "/members/defaults/" },
      ]}
    />
  );
}

export function WorkspacesTabs() {
  const { s } = useGodmodeStrings();
  return (
    <PageTabs
      tabs={[
        { label: s.nav.workspaces_list, href: "/workspace/" },
        { label: s.nav.workspaces_project_defaults, href: "/workspace/project-defaults/" },
      ]}
    />
  );
}

export function LogsTabs() {
  const { s } = useGodmodeStrings();
  return (
    <PageTabs
      tabs={[
        { label: s.nav.logs_activity, href: "/logs/" },
        { label: s.nav.logs_audit, href: "/logs/audit/" },
        { label: s.nav.logs_trash, href: "/logs/trash/" },
      ]}
    />
  );
}

export function ApiKeysTabs() {
  const { s } = useGodmodeStrings();
  return (
    <PageTabs
      tabs={[
        { label: s.nav.api_keys_ai, href: "/api-keys/" },
        { label: s.nav.api_keys_image, href: "/api-keys/image/" },
        { label: s.nav.api_keys_google, href: "/api-keys/google/" },
      ]}
    />
  );
}

export function EmailTabs() {
  const { s } = useGodmodeStrings();
  return (
    <PageTabs
      tabs={[
        { label: s.nav.email_settings, href: "/email/" },
        { label: s.nav.email_preview, href: "/email/preview/" },
      ]}
    />
  );
}
