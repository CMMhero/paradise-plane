/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Notifications > Defaults by role
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * The notification matrix per position, moved here from New member defaults
 * (KEP-83). Same endpoint and same stored JSON row (PARADISE_BAWAAN_MEMBER.email);
 * the PATCH carries only the `email` section.
 */

import { useState } from "react";
import useSWR from "swr";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { InstanceMemberService, type TMemberDefaults, type TSaklarEmail } from "@plane/services";
import { Loader } from "@plane/ui";
import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { PageWrapper } from "@/components/common/page-wrapper";
import { MenuTabs } from "@/components/common/section-tabs";
import { useUnsavedChanges } from "@/components/common/unsaved-changes";
import { SmtpBanner } from "@/components/settings/smtp-banner";
import { MatriksNotifikasi } from "../members/matriks-notifikasi";

const memberService = new InstanceMemberService();

type TEmailDefaults = TMemberDefaults["email"];
type TGroup = keyof TEmailDefaults;

// Staff, leaders (supervisor and manager), directors (secretaries share this column). The director column is also the cap.
const GROUPS: readonly TGroup[] = ["staf", "pimpinan", "direktur"];

const isSame = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

export default function DefaultsByRolePage() {
  const { s } = useGodmodeStrings();
  const t = s.settings.roles;
  const header = s.settings.tabs.notifications_roles;
  const { data, error, mutate } = useSWR("INSTANCE_MEMBER_DEFAULTS", () => memberService.bawaan());
  // null = untouched, show the server value as is.
  const [draft, setDraft] = useState<TEmailDefaults | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const current = draft ?? data?.email ?? null;
  const isDirty = Boolean(draft && data && !isSame(draft, data.email));
  const groupTitle: Record<TGroup, string> = {
    staf: t.col_staf,
    pimpinan: t.col_pimpinan,
    direktur: t.col_direktur,
  };

  const change = (group: TGroup, key: keyof TSaklarEmail, value: boolean) => {
    if (!current) return;
    setDraft({ ...current, [group]: { ...current[group], [key]: value } });
  };

  const save = async () => {
    if (!draft) return;
    setIsSaving(true);
    try {
      const fresh = await memberService.ubahBawaan({ email: draft });
      await mutate(fresh, { revalidate: false });
      setDraft(null);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t.saved, message: t.label });
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t.save_failed,
        message: (err as { error?: string })?.error ?? t.save_failed,
      });
    } finally {
      setIsSaving(false);
    }
  };

  useUnsavedChanges({ label: t.label, isDirty, isSaving, onSave: save, onDiscard: () => setDraft(null) });

  return (
    <PageWrapper header={header}>
      <MenuTabs menu="notifications" />
      <SmtpBanner />
      {error && <p className="text-13 text-danger-primary">{t.load_failed}</p>}
      {!error && !current && (
        <Loader className="space-y-4">
          <Loader.Item height="240px" />
        </Loader>
      )}
      {current && data && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-3xl text-11 text-tertiary">{t.admin_note}</p>
            <Button
              variant="secondary"
              size="base"
              disabled={isSaving || isSame(current, data.pabrik.email)}
              onClick={() => setDraft(data.pabrik.email)}
            >
              {t.reset}
            </Button>
          </div>
          <div className="grid gap-6 rounded-card border border-subtle px-4 py-3 lg:grid-cols-3">
            {GROUPS.map((group) => (
              <div key={group} className="space-y-1.5">
                <span className="block text-11 font-medium text-secondary">{groupTitle[group]}</span>
                {group === "direktur" && <p className="text-11 text-warning-primary">{t.direktur_note}</p>}
                <MatriksNotifikasi nilai={current[group]} onUbah={(k, v) => change(group, k, v)} />
              </div>
            ))}
          </div>
        </div>
      )}
    </PageWrapper>
  );
}

export const meta = () => [{ title: `${godmodeStrings.settings.tabs.notifications_roles.title} - God Mode` }];
