/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
// ui
import { Button, getButtonStyling } from "@plane/propel/button";
// hooks
import ParadiseLogo from "@/app/assets/images/paradise-logo.png?url";
import { useTheme } from "@/hooks/store";
// icons

export const NewUserPopup = observer(function NewUserPopup() {
  // hooks
  const { isNewUserPopup, toggleNewUserPopup } = useTheme();

  if (!isNewUserPopup) return <></>;
  return (
    <div className="shadow-md absolute right-8 bottom-8 w-96 rounded-lg border border-subtle bg-surface-1 p-6">
      <div className="flex gap-4">
        <div className="grow">
          <div className="text-14 font-semibold">Create workspace</div>
          <div className="py-2 text-13 font-medium text-tertiary">
            Instance setup done! Welcome to Paradise Task Tracker instance portal. Start your journey by creating your
            first workspace.
          </div>
          <div className="flex items-center gap-4 pt-2">
            <Link href="/workspace/create" className={getButtonStyling("primary", "lg")}>
              Create workspace
            </Link>
            <Button variant="secondary" size="lg" onClick={toggleNewUserPopup}>
              Close
            </Button>
          </div>
        </div>
        <div className="flex shrink-0 items-center justify-center">
          <img src={ParadiseLogo} height={80} width={80} className="object-contain" alt="Paradise Perkasa icon" />
        </div>
      </div>
    </div>
  );
});
