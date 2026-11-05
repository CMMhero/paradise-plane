/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useTheme } from "next-themes";
// plane imports
import { getButtonStyling } from "@plane/propel/button";
import { cn } from "@plane/utils";
// assets
import ProjectDarkEmptyState from "@/app/assets/empty-state/project-settings/no-projects-dark.png?url";
import ProjectLightEmptyState from "@/app/assets/empty-state/project-settings/no-projects-light.png?url";

function ProjectSettingsPage() {
  // store hooks
  const { resolvedTheme } = useTheme();
  // derived values
  const resolvedPath = resolvedTheme === "dark" ? ProjectDarkEmptyState : ProjectLightEmptyState;
  // Paradise: departemen hanya dibuat di God Mode, jadi tidak ada tombol buat di sini.
  return (
    <div className="mx-auto flex h-full max-w-[480px] flex-col items-center justify-center gap-4">
      <img src={resolvedPath} alt="No departments yet" />
      <div className="text-16 font-semibold text-tertiary">No departments yet</div>
      <div className="text-center text-13 text-tertiary">
        Departments are created in God Mode. Once one exists, you can manage its teams, tasks, and everything you need
        to get things done here.
      </div>
      <div className="flex gap-2">
        <Link href="https://plane.so/" target="_blank" className={cn(getButtonStyling("secondary", "base"))}>
          Learn more about departments
        </Link>
      </div>
    </div>
  );
}

export default observer(ProjectSettingsPage);
