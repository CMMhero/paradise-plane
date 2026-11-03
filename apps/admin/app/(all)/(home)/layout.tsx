/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useRouter } from "next/navigation";
import { Outlet } from "react-router";
import { AuthShowcase } from "@plane/propel/auth-showcase";
import type { AuthShowcaseProps } from "@plane/propel/auth-showcase";
import ParadiseLogo from "@/app/assets/images/paradise-logo.png?url";
// hooks
import { useUser } from "@/hooks/store/use-user";

// God Mode is English-only (no i18n provider), so the captions live here.
// Keep them in step with `login_ui.slide_*` in the web app's paradise.json.
const CAPTIONS: AuthShowcaseProps["captions"] = [
  { title: "Every project, one board", description: "Work grouped by department and division." },
  { title: "See where each division stands", description: "What's done and what's overdue." },
  { title: "Everything about a task in one place", description: "Sub-tasks, files and due dates." },
  { title: "Talk next to the work", description: "Channels and direct messages." },
];

function RootLayout() {
  // router
  const { replace } = useRouter();
  // store hooks
  const { isUserLoggedIn } = useUser();

  useEffect(() => {
    if (isUserLoggedIn === true) replace("/general");
  }, [replace, isUserLoggedIn]);

  // Paradise: same framed card as the web sign-in. App preview on the left from
  // lg up, the form on the right; below lg a plain single column.
  return (
    <div className="relative z-10 flex h-screen w-screen overflow-y-auto bg-canvas lg:p-8">
      <div className="m-auto grid min-h-full w-full max-w-[1180px] bg-surface-1 lg:min-h-[min(720px,100%)] lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-4 lg:rounded-overlay lg:border lg:border-subtle lg:p-4 lg:shadow-overlay-200">
        <AuthShowcase
          className="hidden lg:flex"
          brandName="Space Paradise Perkasa"
          logoSrc={ParadiseLogo}
          label="App preview"
          captions={CAPTIONS}
        />
        <main className="flex min-w-0 flex-col items-center px-5 pt-5 pb-8 sm:px-10 sm:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default observer(RootLayout);
