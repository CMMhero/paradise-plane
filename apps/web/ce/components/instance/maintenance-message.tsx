/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";

// Tautan mailto:support@plane.so dibuang, dukungan vendor tidak melayani
// instalasi ini. Pesannya juga diarahkan ke orang yang benar-benar bisa
// menolong: tim IT internal yang memegang servernya.
export function MaintenanceMessage() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-2.5">
      <h1 className="text-left text-18 font-semibold text-primary">
        &#x1F6A7; {t("connections_ui.maintenance_title")}
      </h1>
      <span className="text-left text-14 font-medium text-secondary">{t("connections_ui.maintenance_message")}</span>
    </div>
  );
}
