/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
import { X } from "lucide-react";
import { observer } from "mobx-react";
// plane imports
import { IconButton } from "@plane/propel/icon-button";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// hooks
import { useCommandPalette } from "@/hooks/store/use-command-palette";
import { useInstance } from "@/hooks/store/use-instance";
import { isProfileTabAvailable, PROFILE_TAB_FALLBACK } from "@/lib/profile-tabs";
// local imports
import { ProfileSettingsContent } from "./content";
import { ProfileSettingsSidebarRoot } from "./sidebar";

export const ProfileSettingsModal = observer(function ProfileSettingsModal() {
  // store hooks
  const { profileSettingsModal, toggleProfileSettingsModal } = useCommandPalette();
  const { config } = useInstance();
  // derived values
  const diminta = profileSettingsModal.activeTab ?? PROFILE_TAB_FALLBACK;
  const activeTab = isProfileTabAvailable(config, diminta) ? diminta : PROFILE_TAB_FALLBACK;

  const handleClose = useCallback(() => {
    toggleProfileSettingsModal({
      isOpen: false,
    });
    setTimeout(() => {
      toggleProfileSettingsModal({
        activeTab: null,
      });
    }, 300);
  }, [toggleProfileSettingsModal]);

  return (
    <ModalCore
      isOpen={profileSettingsModal.isOpen}
      handleClose={handleClose}
      position={EModalPosition.CENTER}
      width={EModalWidth.VIXL}
      className="h-175"
    >
      <div className="@container relative size-full">
        <div className="flex size-full">
          <ProfileSettingsSidebarRoot
            activeTab={activeTab}
            className="w-[250px] rounded-l-xl"
            updateActiveTab={(tab) => toggleProfileSettingsModal({ activeTab: tab })}
          />
          <ProfileSettingsContent activeTab={activeTab} className="flex-1 rounded-r-xl" />
        </div>
        <div className="absolute top-3.5 right-3.5">
          <IconButton size="base" variant="tertiary" icon={X} onClick={handleClose} />
        </div>
      </div>
    </ModalCore>
  );
});
