/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { useTranslation } from "@plane/i18n";
import { AuthShowcase } from "@plane/propel/auth-showcase";
import ParadiseLogo from "@/app/assets/images/paradise-logo.png?url";
import { AuthRoot } from "@/components/account/auth-forms/auth-root";
import type { EAuthModes } from "@/helpers/authentication.helper";
import { AuthFooter } from "./footer";
import { AuthHeader } from "./header";

type AuthBaseProps = {
  authType: EAuthModes;
};

// Paradise: one framed card from lg up, the app preview on the left and the form
// on the right. Below lg the card dissolves into a plain single column.
// Only presentation changed; AuthRoot keeps every auth flow as upstream.
export function AuthBase({ authType }: AuthBaseProps) {
  const { t } = useTranslation();

  return (
    <div className="relative z-10 flex h-screen w-screen overflow-y-auto bg-canvas lg:p-8">
      <div className="m-auto grid min-h-full w-full max-w-[1180px] bg-surface-1 lg:min-h-[min(720px,100%)] lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-4 lg:rounded-overlay lg:border lg:border-subtle lg:p-4 lg:shadow-overlay-200">
        <AuthShowcase
          className="hidden lg:flex"
          brandName="Space Paradise Perkasa"
          logoSrc={ParadiseLogo}
          label={t("login_ui.panel_label")}
          captions={[
            { title: t("login_ui.slide_board_title"), description: t("login_ui.slide_board_desc") },
            { title: t("login_ui.slide_dashboard_title"), description: t("login_ui.slide_dashboard_desc") },
            { title: t("login_ui.slide_task_title"), description: t("login_ui.slide_task_desc") },
            { title: t("login_ui.slide_chat_title"), description: t("login_ui.slide_chat_desc") },
          ]}
        />
        <main className="flex min-w-0 flex-col items-center px-5 pt-5 pb-8 sm:px-10 sm:pt-6">
          <AuthHeader type={authType} logoClassName="lg:invisible" />
          <AuthRoot authMode={authType} />
          <AuthFooter />
        </main>
      </div>
    </div>
  );
}
