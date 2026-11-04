/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: undangan kedaluwarsa (KEP-83)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";

/** Penanda "Expired" untuk baris undangan yang sudah lewat masa berlakunya. */
export function InviteExpiredBadge() {
  const { t } = useTranslation();
  return (
    <span className="flex-shrink-0 rounded-sm bg-danger-subtle px-2 py-0.5 text-11 font-medium text-danger-primary">
      {t("aturan_tugas_ui.invite_expired_badge")}
    </span>
  );
}
