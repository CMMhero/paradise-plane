/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { CreateProjectModal } from "@/components/project/create-project-modal";
// hooks
import { useCommandPalette } from "@/hooks/store/use-command-palette";
import { useBolehBuatProject } from "@/hooks/use-boleh-buat-project";

export type TWorkspaceLevelModalsProps = {
  workspaceSlug: string;
};

export const WorkspaceLevelModals = observer(function WorkspaceLevelModals(props: TWorkspaceLevelModalsProps) {
  const { workspaceSlug } = props;
  // store hooks
  const { isCreateProjectModalOpen, toggleCreateProjectModal } = useCommandPalette();
  // Paradise: jaring terakhir. Pintu mana pun yang lupa dijaga tetap tidak membuka
  // formulir yang pasti ditolak server untuk staf / member biasa.
  const bolehBuatProject = useBolehBuatProject(workspaceSlug);

  return (
    <>
      <CreateProjectModal
        isOpen={isCreateProjectModalOpen && bolehBuatProject}
        onClose={() => toggleCreateProjectModal(false)}
        workspaceSlug={workspaceSlug.toString()}
      />
    </>
  );
});
