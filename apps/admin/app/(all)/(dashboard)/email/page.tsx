/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Loader, ToggleSwitch } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { MenuTabs } from "@/components/common/section-tabs";
// hooks
import { godmodeStrings } from "@/app/i18n/godmode";
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// local
import { InstanceEmailForm } from "./email-config-form";
import { InstanceImapForm } from "./imap-config-form";

const InstanceEmailPage = observer(function InstanceEmailPage(_props: Route.ComponentProps) {
  // store
  const { fetchInstanceConfigurations, formattedConfig, disableEmail } = useInstance();

  const { isLoading } = useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSMTPEnabled, setIsSMTPEnabled] = useState(false);

  const handleToggle = async () => {
    if (isSMTPEnabled) {
      setIsSubmitting(true);
      try {
        await disableEmail();
        setIsSMTPEnabled(false);
        setToast({
          title: "Email feature disabled",
          message: "Email feature has been disabled",
          type: TOAST_TYPE.SUCCESS,
        });
      } catch (_error) {
        setToast({
          title: "Error disabling email",
          message: "Failed to disable email feature. Please try again.",
          type: TOAST_TYPE.ERROR,
        });
      } finally {
        setIsSubmitting(false);
      }
      return;
    }
    setIsSMTPEnabled(true);
  };
  useEffect(() => {
    if (formattedConfig) {
      // Sama dengan `email_aktif()` di server: host terisi = email menyala.
      // ENABLE_SMTP tidak dibaca server (benihnya "0"), jadi jangan dipakai di sini.
      setIsSMTPEnabled(Boolean(formattedConfig.EMAIL_HOST?.trim()));
    }
  }, [formattedConfig]);

  return (
    <PageWrapper
      header={{
        title: godmodeStrings.settings.tabs.notifications_email.title,
        description: (
          <>
            This instance can email you and its users through your own server, without going out to the internet.
            <div className="text-13 font-regular text-tertiary">
              Set it up below and please test your settings before you save them.&nbsp;
              <span className="text-danger-primary">Misconfigs can lead to email bounces and errors.</span>
            </div>
          </>
        ),
        actions: isLoading ? (
          <Loader>
            <Loader.Item width="24px" height="16px" className="rounded-control" />
          </Loader>
        ) : (
          <ToggleSwitch value={isSMTPEnabled} onChange={handleToggle} size="sm" disabled={isSubmitting} />
        ),
      }}
    >
      <MenuTabs menu="notifications" />
      {isSMTPEnabled && !isLoading && (
        <>
          {formattedConfig ? (
            <div className="space-y-10">
              {/* Dua server berbeda dengan port dan kredensial berbeda. Dulu
                  halaman ini hanya menampilkan yang keluar tanpa menyebutnya,
                  jadi tidak ada petunjuk bahwa yang masuk memang belum ada. */}
              <section>
                <h3 className="text-13 font-medium text-primary">Outgoing email (SMTP)</h3>
                <p className="mb-4 text-11 font-regular text-tertiary">
                  Used to send invitations, password resets, and notifications.
                </p>
                <InstanceEmailForm config={formattedConfig} />
              </section>

              <section className="border-t border-subtle pt-8">
                <h3 className="text-13 font-medium text-primary">Incoming email (IMAP)</h3>
                <p className="mb-4 text-11 font-regular text-tertiary">
                  The office inbox server, kept here next to the outgoing settings.
                </p>
                <InstanceImapForm config={formattedConfig} />
              </section>
            </div>
          ) : (
            <Loader className="space-y-10">
              <Loader.Item height="50px" width="75%" />
              <Loader.Item height="50px" width="75%" />
              <Loader.Item height="50px" width="40%" />
              <Loader.Item height="50px" width="40%" />
              <Loader.Item height="50px" width="20%" />
            </Loader>
          )}
        </>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [
  { title: `${godmodeStrings.settings.tabs.notifications_email.title} - God Mode` },
];

export default InstanceEmailPage;
