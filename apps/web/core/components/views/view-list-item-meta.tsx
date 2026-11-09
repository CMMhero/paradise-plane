/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: metadata baris view (dipakai view workspace & departemen)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Earth } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { LockIcon } from "@plane/propel/icons";
import { Tooltip } from "@plane/propel/tooltip";
import { EViewAccess } from "@plane/types";
// hooks
import { useProject } from "@/hooks/store/use-project";
// local imports
import { ButtonAvatars } from "../dropdowns/member/avatar";

type Props = {
  access: EViewAccess;
  ownerId: string | undefined;
  /** Halaman Views workspace mencampur view workspace dan departemen: tempatnya ditandai. */
  scope?: { projectId: string | null };
};

/** Tempat view: nama departemen dengan logonya, atau "Workspace". */
export const ViewScopeChip = observer(function ViewScopeChip({ projectId }: { projectId: string | null }) {
  const { t } = useTranslation();
  const { getProjectById } = useProject();
  const project = projectId ? getProjectById(projectId) : undefined;

  return (
    <span className="flex max-w-40 items-center gap-1.5 rounded-control border border-subtle px-2 py-0.5 text-11 text-secondary">
      {project?.logo_props && <Logo logo={project.logo_props} size={12} />}
      <span className="truncate">{project ? project.name : t("views_ui.scope_workspace")}</span>
    </span>
  );
});

/** Ikon akses, tempat (opsional), dan pemilik: urutan dan gaya sama di setiap baris view. */
export const ViewListItemMeta = observer(function ViewListItemMeta({ access, ownerId, scope }: Props) {
  const { t } = useTranslation();
  const isPublic = access === EViewAccess.PUBLIC;

  return (
    <>
      {scope && <ViewScopeChip projectId={scope.projectId} />}
      <div className="cursor-default text-tertiary">
        <Tooltip tooltipContent={isPublic ? t("public") : t("private")}>
          {isPublic ? (
            <Earth className="h-4 w-4" aria-label={t("public")} />
          ) : (
            <LockIcon className="h-4 w-4" aria-label={t("private")} />
          )}
        </Tooltip>
      </div>
      <ButtonAvatars showProfileCard showTooltip={false} userIds={ownerId ?? []} />
    </>
  );
});
