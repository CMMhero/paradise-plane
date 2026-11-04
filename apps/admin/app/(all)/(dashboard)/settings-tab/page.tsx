/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: generic registry settings tab
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * One module serves every tab that is just a list of registry rows (company,
 * sessions, rules, dates, permissions, sending, schedule, modules, chat, dashboards, files,
 * retention). The URL picks the tab; the rows come from components/settings/layouts.ts
 * and the values from GET /api/instances/settings/.
 */

import { useLocation } from "react-router";
import Link from "next/link";
import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { PageWrapper } from "@/components/common/page-wrapper";
import { MenuTabs } from "@/components/common/section-tabs";
import type { TMenuId, TTabId } from "@/components/common/section-tabs";
import type { TSettingsTabId } from "@/components/settings/layouts";
import { SettingsTabForm } from "@/components/settings/settings-tab-form";
import { SmtpBanner } from "@/components/settings/smtp-banner";

type TTabRoute = { menu: TMenuId; tab: TTabId; layout: TSettingsTabId };

const TAB_BY_PATH: Record<string, TTabRoute> = {
  "/general/company": { menu: "general", tab: "general_company", layout: "general_company" },
  "/access/sessions": { menu: "access", tab: "access_sessions", layout: "access_sessions" },
  "/rules": { menu: "rules", tab: "rules_approvals", layout: "rules_approvals" },
  "/rules/dates": { menu: "rules", tab: "rules_dates", layout: "rules_dates" },
  "/rules/permissions": { menu: "rules", tab: "rules_permissions", layout: "rules_permissions" },
  "/notifications/sending": { menu: "notifications", tab: "notifications_sending", layout: "notifications_sending" },
  "/notifications/schedule": { menu: "notifications", tab: "notifications_schedule", layout: "notifications_schedule" },
  "/modules": { menu: "modules", tab: "modules_visibility", layout: "modules_visibility" },
  "/modules/chat": { menu: "modules", tab: "modules_chat", layout: "modules_chat" },
  "/modules/dashboards": { menu: "modules", tab: "modules_dashboards", layout: "modules_dashboards" },
  "/modules/files": { menu: "modules", tab: "modules_files", layout: "modules_files" },
  "/logs/retention": { menu: "logs", tab: "logs_retention", layout: "logs_retention" },
};

const tabForPath = (pathname: string): TTabRoute | undefined => TAB_BY_PATH[pathname.replace(/\/+$/, "")];

export default function SettingsTabPage() {
  const { pathname } = useLocation();
  const { s } = useGodmodeStrings();
  const route = tabForPath(pathname);
  if (!route) return null;
  const header = s.settings.tabs[route.tab];

  return (
    <PageWrapper header={header}>
      <MenuTabs menu={route.menu} />
      {route.menu === "notifications" && <SmtpBanner />}
      <SettingsTabForm
        tab={route.layout}
        tabTitle={header.title}
        showOfficeZone={route.layout === "notifications_schedule"}
        intro={
          route.layout === "general_company" ? (
            <div className="space-y-1 text-11 text-tertiary">
              <p>{s.settings.company.timezone_note}</p>
              <p>{s.settings.company.workspace_note}</p>
            </div>
          ) : route.layout === "rules_permissions" ? (
            <p className="text-11 text-tertiary">{s.settings.permissions.intro}</p>
          ) : route.layout === "notifications_schedule" ? (
            <p className="text-11 text-tertiary">
              {s.settings.tabs.notifications_schedule.description}{" "}
              <Link href="/general/company/" className="font-medium text-accent-primary hover:underline">
                {s.settings.tabs.general_company.title}
              </Link>
            </p>
          ) : undefined
        }
      />
    </PageWrapper>
  );
}

export const meta = ({ location }: { location: { pathname: string } }) => {
  const route = tabForPath(location.pathname);
  return [{ title: `${route ? godmodeStrings.settings.tabs[route.tab].title : "Settings"} - God Mode` }];
};
