/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IProjectView, IWorkspaceView } from "@plane/types";
import { EIssuesStoreType } from "@plane/types";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// components
import { ProjectViewForm } from "@/components/views/form";
import { ViewScopeField } from "@/components/views/form-sections";
// hooks
import { useGlobalView } from "@/hooks/store/use-global-view";
import { useProjectView } from "@/hooks/store/use-project-view";
import { useWorkItemFilters } from "@/hooks/store/work-item-filters/use-work-item-filters";
import { useAppRouter } from "@/hooks/use-app-router";
// local imports
import { WorkspaceViewForm } from "./form";

type Props = {
  data?: IWorkspaceView;
  isOpen: boolean;
  onClose: () => void;
  preLoadedData?: Partial<IWorkspaceView>;
};

export const CreateUpdateWorkspaceViewModal = observer(function CreateUpdateWorkspaceViewModal(props: Props) {
  const { isOpen, onClose, data, preLoadedData } = props;
  // Kustomisasi Paradise: saat MEMBUAT, view bisa ditaruh di workspace atau di satu departemen.
  // `null` = workspace. Sesudah dibuat tempatnya terkunci (kolom `project` hanya-baca di server).
  const [scopeProjectId, setScopeProjectId] = useState<string | null>(null);
  // router
  const router = useAppRouter();
  const { workspaceSlug: routerWorkspaceSlug } = useParams();
  const workspaceSlug = routerWorkspaceSlug ? routerWorkspaceSlug.toString() : undefined;
  // store hooks
  const { createGlobalView, updateGlobalView } = useGlobalView();
  const { createView } = useProjectView();
  const { resetExpression } = useWorkItemFilters();

  const handleClose = () => {
    onClose();
    setScopeProjectId(null);
  };

  const handleCreateView = async (payload: Partial<IWorkspaceView>) => {
    if (!workspaceSlug) return;

    try {
      const payloadData: Partial<IWorkspaceView> = {
        ...payload,
        rich_filters: {
          ...payload?.rich_filters,
        },
      };
      const res = await createGlobalView(workspaceSlug, payloadData);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Success!",
        message: "View created successfully.",
      });
      router.push(`/${workspaceSlug}/workspace-views/${res.id}`);
      handleClose();
    } catch (_error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: "View could not be created. Please try again.",
      });
    }
  };

  const handleCreateDepartmentView = async (payload: IProjectView) => {
    if (!workspaceSlug || !scopeProjectId) return;

    try {
      const res = await createView(workspaceSlug, scopeProjectId, payload);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Success!",
        message: "View created successfully.",
      });
      router.push(`/${workspaceSlug}/projects/${scopeProjectId}/views/${res.id}`);
      handleClose();
    } catch (_error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: "View could not be created. Please try again.",
      });
    }
  };

  const handleUpdateView = async (payload: Partial<IWorkspaceView>) => {
    if (!workspaceSlug || !data) return;

    try {
      const payloadData: Partial<IWorkspaceView> = {
        ...payload,
        query: {
          ...payload?.rich_filters,
        },
      };
      const res = await updateGlobalView(workspaceSlug, data.id, payloadData);
      if (res) {
        resetExpression(EIssuesStoreType.GLOBAL, data.id, res.rich_filters);
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Success!",
          message: "View updated successfully.",
        });
        handleClose();
      }
    } catch (_error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error!",
        message: "View could not be updated. Please try again.",
      });
    }
  };

  const handleFormSubmit = async (formData: Partial<IWorkspaceView>) => {
    if (!workspaceSlug) return;

    if (!data) await handleCreateView(formData);
    else await handleUpdateView(formData);
  };

  if (!workspaceSlug) return null;

  const scopeSlot = data ? undefined : <ViewScopeField projectId={scopeProjectId} onChange={setScopeProjectId} />;

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.TOP} width={EModalWidth.XXL}>
      {!data && scopeProjectId ? (
        // Formulir departemen: filter, layout, dan tampilan milik departemen itu.
        <ProjectViewForm
          key={scopeProjectId}
          handleClose={handleClose}
          handleFormSubmit={handleCreateDepartmentView}
          projectId={scopeProjectId}
          workspaceSlug={workspaceSlug}
          scopeSlot={scopeSlot}
        />
      ) : (
        <WorkspaceViewForm
          handleFormSubmit={handleFormSubmit}
          handleClose={handleClose}
          data={data}
          preLoadedData={preLoadedData}
          workspaceSlug={workspaceSlug}
          scopeSlot={scopeSlot}
        />
      )}
    </ModalCore>
  );
});
