/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { lazy, Suspense, useEffect, useState } from "react";
import { observer } from "mobx-react";
// plane package imports
import { ModalPortal, EPortalWidth, EPortalPosition } from "@plane/propel/portal";
import type { ICycle, IModule, IProject } from "@plane/types";
import { useAnalytics } from "@/hooks/store/use-analytics";
// plane web components
import { WorkItemsModalHeader } from "./header";

// Paradise: isi modal (grafik recharts) dimuat saat modal dibuka. Modal ini
// diimpor statis oleh header daftar work item & modul, jadi tanpa ini recharts
// ikut bundel awal halaman-halaman itu walau modal jarang dibuka.
const WorkItemsModalMainContent = lazy(() =>
  import("./content").then((m) => ({ default: m.WorkItemsModalMainContent }))
);

type Props = {
  isOpen: boolean;
  onClose: () => void;
  projectDetails?: IProject | undefined;
  cycleDetails?: ICycle | undefined;
  moduleDetails?: IModule | undefined;
  isEpic?: boolean;
};

export const WorkItemsModal = observer(function WorkItemsModal(props: Props) {
  const { isOpen, onClose, projectDetails, moduleDetails, cycleDetails, isEpic } = props;
  const { updateIsEpic, isPeekView } = useAnalytics();
  const [fullScreen, setFullScreen] = useState(false);

  const handleClose = () => {
    setFullScreen(false);
    onClose();
  };

  useEffect(() => {
    updateIsEpic(isPeekView ? (isEpic ?? false) : false);
  }, [isEpic, updateIsEpic, isPeekView]);

  return (
    <ModalPortal
      isOpen={isOpen}
      onClose={handleClose}
      width={fullScreen ? EPortalWidth.FULL : EPortalWidth.THREE_QUARTER}
      position={EPortalPosition.RIGHT}
      fullScreen={fullScreen}
    >
      <div
        className={`flex h-full flex-col overflow-hidden border-subtle bg-surface-1 text-left ${
          fullScreen ? "rounded-lg border" : "border-l"
        }`}
      >
        <WorkItemsModalHeader
          fullScreen={fullScreen}
          handleClose={handleClose}
          setFullScreen={setFullScreen}
          title={projectDetails?.name ?? ""}
          cycle={cycleDetails}
          module={moduleDetails}
        />
        <Suspense fallback={<div className="flex-1" />}>
          <WorkItemsModalMainContent
            fullScreen={fullScreen}
            projectDetails={projectDetails}
            cycleDetails={cycleDetails}
            moduleDetails={moduleDetails}
            isEpic={isEpic}
          />
        </Suspense>
      </div>
    </ModalPortal>
  );
});
