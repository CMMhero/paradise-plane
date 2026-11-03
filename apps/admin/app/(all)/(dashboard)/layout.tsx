/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useRouter } from "next/navigation";
import { Outlet } from "react-router";
// components
import { AdminHeader } from "@/components/common/header";
import { LogoSpinner } from "@/components/common/logo-spinner";
import { NewUserPopup } from "@/components/common/new-user-popup";
import { UnsavedChangesBar, UnsavedChangesProvider } from "@/components/common/unsaved-changes";
// hooks
import { useUser } from "@/hooks/store";
// local components
import type { Route } from "./+types/layout";
import { AdminSidebar } from "./sidebar";

function AdminLayout(_props: Route.ComponentProps) {
  // router
  const { replace } = useRouter();
  // store hooks
  const { isUserLoggedIn } = useUser();

  useEffect(() => {
    if (isUserLoggedIn === false) replace("/");
  }, [replace, isUserLoggedIn]);

  if (isUserLoggedIn === undefined) {
    return (
      <div className="relative flex h-screen w-full items-center justify-center">
        <LogoSpinner />
      </div>
    );
  }

  if (isUserLoggedIn) {
    return (
      <UnsavedChangesProvider>
        <div className="relative flex h-screen w-screen overflow-hidden">
          <AdminSidebar />
          <main className="relative flex h-full w-full flex-col overflow-hidden bg-surface-1">
            <AdminHeader />
            <div className="vertical-scrollbar scrollbar-md min-h-0 w-full flex-1 overflow-hidden overflow-y-scroll">
              <Outlet />
            </div>
            {/* Paradise: outside the scroll area, so Save / Discard never scroll away. */}
            <UnsavedChangesBar />
          </main>
          <NewUserPopup />
        </div>
      </UnsavedChangesProvider>
    );
  }

  return <></>;
}

export default observer(AdminLayout);
