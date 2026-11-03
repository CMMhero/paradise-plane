/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { useInstance } from "@/hooks/store/use-instance";

// Paradise: with sign-up closed, accounts come from the admin, so the footer says
// who to ask. With sign-up open the header already links to it, so nothing shows.
export const AuthFooter = observer(function AuthFooter() {
  const { t } = useTranslation();
  const { config } = useInstance();
  const isSignUpOpen = config?.enable_signup ?? false;

  return (
    <div className="flex flex-col items-center gap-2">
      {!isSignUpOpen && <span className="text-center text-13 text-tertiary">{t("login_ui.no_account")}</span>}
      {/* Tawaran kode sumber AGPL-3.0 pasal 13. Wajib untuk pengguna yang BELUM masuk juga. */}
    </div>
  );
});
