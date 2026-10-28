/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pengaturan pribadi member di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bagian dari panel MemberEditor: ikut tombol Simpan yang sama. Hook memegang
 * keadaan + selisih; komponen hanya menggambar.
 */

import { useEffect, useState } from "react";
// plane imports
import { InstanceMemberService, type TMemberPreferences, type TMemberPreferencesUpdate } from "@plane/services";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BAHASA_PROFIL, inputClass } from "./constants";

const memberService = new InstanceMemberService();

type TProfile = TMemberPreferences["profile"];
type TNotif = TMemberPreferences["notifications"];

const SAKLAR_NOTIF: (keyof TNotif)[] = [
  "approval",
  "issue_completed",
  "daily_digest",
  "mention",
  "comment",
  "state_change",
  "property_change",
];

/** Hanya kunci yang nilainya berbeda dari aslinya. */
const selisih = <T extends object>(asli: T, baru: T): Partial<T> =>
  Object.fromEntries(Object.entries(baru).filter(([k, v]) => v !== asli[k as keyof T])) as Partial<T>;

export function useMemberPreferences(memberId: string) {
  const [asli, setAsli] = useState<TMemberPreferences | null>(null);
  const [baru, setBaru] = useState<TMemberPreferences | null>(null);
  const [gagal, setGagal] = useState(false);

  useEffect(() => {
    let hidup = true;
    memberService
      .preferensi(memberId)
      .then((p) => {
        if (hidup) {
          setAsli(p);
          setBaru(p);
        }
        return null;
      })
      .catch(() => {
        if (hidup) setGagal(true);
      });
    return () => {
      hidup = false;
    };
  }, [memberId]);

  const perubahan = (): TMemberPreferencesUpdate | null => {
    if (!asli || !baru) return null;
    const profile = selisih(asli.profile, baru.profile);
    const notifications = selisih(asli.notifications, baru.notifications);
    if (Object.keys(profile).length === 0 && Object.keys(notifications).length === 0) return null;
    return { profile, notifications };
  };

  return {
    nilai: baru,
    gagal,
    ubahProfil: (p: Partial<TProfile>) => setBaru((b) => (b ? { ...b, profile: { ...b.profile, ...p } } : b)),
    ubahNotif: (n: Partial<TNotif>) => setBaru((b) => (b ? { ...b, notifications: { ...b.notifications, ...n } } : b)),
    perubahan,
  };
}

type Props = {
  nilai: TMemberPreferences | null;
  gagal: boolean;
  onProfil: (p: Partial<TProfile>) => void;
  onNotif: (n: Partial<TNotif>) => void;
};

export function PreferensiMember({ nilai, gagal, onProfil, onNotif }: Props) {
  const { s } = useGodmodeStrings();
  const t = s.editor.prefs;

  if (gagal) return <p className="text-danger text-11">{t.load_failed}</p>;
  if (!nilai) return <p className="text-11 text-secondary">{t.loading}</p>;

  const { profile, notifications } = nilai;
  return (
    <div className="space-y-3 rounded border border-subtle px-3 py-2">
      <span className="block text-11 font-medium text-secondary">{t.title}</span>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="space-y-1">
          <span className="block text-11 text-secondary">{t.language}</span>
          <select
            className={`${inputClass} w-full`}
            value={profile.language}
            onChange={(e) => onProfil({ language: e.target.value })}
          >
            {BAHASA_PROFIL.map((b) => (
              <option key={b.value} value={b.value}>
                {b.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block text-11 text-secondary">{t.week_start}</span>
          <select
            className={`${inputClass} w-full`}
            value={profile.start_of_the_week}
            onChange={(e) => onProfil({ start_of_the_week: Number(e.target.value) })}
          >
            {t.days.map((hari, i) => (
              <option key={hari} value={i}>
                {hari}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block text-11 text-secondary">{t.notif_view}</span>
          <select
            className={`${inputClass} w-full`}
            value={profile.notification_view_mode}
            onChange={(e) => onProfil({ notification_view_mode: e.target.value as TProfile["notification_view_mode"] })}
          >
            <option value="full">{t.notif_view_full}</option>
            <option value="compact">{t.notif_view_compact}</option>
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <Saklar
          label={t.smooth_cursor}
          nilai={profile.is_smooth_cursor_enabled}
          onUbah={(v) => onProfil({ is_smooth_cursor_enabled: v })}
        />
        <Saklar
          label={t.app_rail}
          nilai={profile.is_app_rail_docked}
          onUbah={(v) => onProfil({ is_app_rail_docked: v })}
        />
      </div>

      <div className="space-y-1">
        <span className="block text-11 text-secondary">{t.email_title}</span>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {SAKLAR_NOTIF.map((k) => (
            <Saklar key={k} label={t[k]} nilai={notifications[k]} onUbah={(v) => onNotif({ [k]: v })} />
          ))}
        </div>
        <p className="text-11 text-tertiary">{t.email_note}</p>
      </div>
    </div>
  );
}

function Saklar({ label, nilai, onUbah }: { label: string; nilai: boolean; onUbah: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-1.5 text-11 text-primary">
      <input type="checkbox" checked={nilai} onChange={(e) => onUbah(e.target.checked)} />
      {label}
    </label>
  );
}
