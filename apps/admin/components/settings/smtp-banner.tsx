/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: "email is not set up" banner for Notifications tabs
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { MailWarning } from "lucide-react";
import useSWR from "swr";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { Callout } from "@/components/common/paradise";
import { useInstance } from "@/hooks/store";

/**
 * Mirrors the server's `email_aktif()`: a host is filled in. ENABLE_SMTP is not read
 * (its seed is "0"). Shown above every Notifications tab except Email server itself.
 */
export const SmtpBanner = observer(function SmtpBanner() {
  const { s } = useGodmodeStrings();
  const { fetchInstanceConfigurations, formattedConfig } = useInstance();
  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  if (!formattedConfig) return null;
  const isConfigured = Boolean(formattedConfig.EMAIL_HOST?.trim());
  if (isConfigured) return null;

  return (
    <div className="mb-6">
      <Callout icon={<MailWarning className="size-4" />} title={s.settings.smtp.title}>
        {s.settings.smtp.body}{" "}
        <Link href="/notifications/" className="font-medium text-accent-primary hover:underline">
          {s.settings.smtp.link}
        </Link>
      </Callout>
    </div>
  );
});
