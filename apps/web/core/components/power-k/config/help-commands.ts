/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { FileText, Rocket } from "lucide-react";
// components
import type { TPowerKCommandConfig } from "@/components/power-k/core/types";
// hooks
import { usePowerK } from "@/hooks/store/use-power-k";

/**
 * Help commands - Help related commands
 *
 * Tiga perintah upstream dibuang: docs.plane.so, forum.plane.so, dan pelaporan
 * bug ke issue tracker makeplane/plane. Semuanya saluran dukungan vendor yang
 * tidak melayani PT Paradise Perkasa, mengarahkan karyawan ke sana bukan cuma
 * tak berguna, tapi menyesatkan. "Dokumentasi" kini menunjuk Wiki internal.
 */
export const usePowerKHelpCommands = (): TPowerKCommandConfig[] => {
  // store
  const { toggleShortcutsListModal } = usePowerK();

  return [
    {
      id: "open_keyboard_shortcuts",
      type: "action",
      group: "help",
      i18n_title: "power_k.help_actions.open_keyboard_shortcuts",
      icon: Rocket,
      modifierShortcut: "cmd+/",
      action: () => toggleShortcutsListModal(true),
      isEnabled: () => true,
      isVisible: () => true,
      closeOnSelect: true,
    },
    {
      id: "open_plane_documentation",
      type: "action",
      group: "help",
      i18n_title: "power_k.help_actions.open_plane_documentation",
      icon: FileText,
      action: () => {
        // Wiki internal. Slug workspace diambil dari URL supaya tidak perlu
        // hook tambahan di config yang dipakai lintas-workspace.
        const slug = window.location.pathname.split("/").find(Boolean);
        if (slug) window.location.assign(`/${slug}/wiki/`);
      },
      isEnabled: () => true,
      isVisible: () => true,
      closeOnSelect: true,
    },
  ];
};
