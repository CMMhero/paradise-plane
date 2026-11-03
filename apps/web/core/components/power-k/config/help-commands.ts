/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Rocket } from "lucide-react";
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
 * tak berguna, tapi menyesatkan. Perintah "Dokumentasi" (pernah menunjuk Wiki)
 * juga dibuang: Wiki sekarang punya perintah navigasi sendiri, `nav_wiki` (gw).
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
  ];
};
