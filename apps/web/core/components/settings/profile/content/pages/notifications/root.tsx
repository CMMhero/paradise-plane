/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
// components
import { ProfileSettingsHeading } from "@/components/settings/profile/heading";
import { EmailSettingsLoader } from "@/components/ui/loader/settings/email";
// services
import { UserService } from "@/services/user.service";
// local imports
import { EMAIL_SETTINGS_SWR_KEY, NotificationsProfileSettingsForm } from "./email-notification-form";

const userService = new UserService();

export const NotificationsProfileSettings = observer(function NotificationsProfileSettings() {
  const { t } = useTranslation();
  // fetching user email notification settings
  const { data, error, isLoading, mutate } = useSWR(EMAIL_SETTINGS_SWR_KEY, () =>
    userService.currentUserEmailNotificationSettings()
  );

  // Without this branch a failed request leaves the skeleton up forever.
  if (error && !data) {
    return (
      <div className="flex size-full flex-col items-center justify-center gap-3 py-10 text-center">
        <p className="text-13 text-secondary">{t("something_went_wrong_please_try_again")}</p>
        <Button variant="secondary" size="sm" onClick={() => void mutate()}>
          {t("refresh")}
        </Button>
      </div>
    );
  }

  if (!data || isLoading) {
    return <EmailSettingsLoader />;
  }

  return (
    <div className="size-full">
      <ProfileSettingsHeading
        title={t("account_settings.notifications.heading")}
        description={t("account_settings.notifications.description")}
      />
      <div className="mt-7">
        <NotificationsProfileSettingsForm data={data} />
      </div>
    </div>
  );
});
