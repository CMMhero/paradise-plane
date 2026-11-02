/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: matriks notifikasi di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu jenis kabar = satu baris: inbox di aplikasi dan email, lalu bagian
 * ringkasan harian. Barisnya dari katalog yang sama dengan Profil > Notifikasi
 * (`NOTIFICATION_EVENTS`), jadi God Mode dan aplikasi tidak bisa berbeda daftar.
 * Dipakai preferensi per member dan tabel bawaan jabatan.
 */

import { NOTIFICATION_DIGEST_SECTIONS, NOTIFICATION_EVENTS } from "@plane/constants";
import type { TSaklarEmail } from "@plane/services";
import type { TNotificationPreferenceKey } from "@plane/types";
import { ToggleSwitch } from "@plane/ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { Saklar } from "./bidang-profil";

type Props = {
  nilai: TSaklarEmail;
  onUbah: (kunci: TNotificationPreferenceKey, v: boolean) => void;
  /** Saklar yang dipaksa mati kebijakan direktur; tampil mati dan tak bisa diubah. */
  dikunci?: readonly TNotificationPreferenceKey[];
};

const TANPA_KUNCI: readonly TNotificationPreferenceKey[] = [];

export function MatriksNotifikasi({ nilai, onUbah, dikunci = TANPA_KUNCI }: Props) {
  const { s } = useGodmodeStrings();
  const t = s.editor.prefs;
  const kunci = (k: TNotificationPreferenceKey) => dikunci.includes(k);

  return (
    <div className="space-y-3">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-subtle text-11 text-tertiary">
            <th className="py-1.5 text-left font-medium">{t.col_event}</th>
            <th className="w-16 py-1.5 text-center font-medium">{t.col_inbox}</th>
            <th className="w-16 py-1.5 text-center font-medium">{t.col_email}</th>
          </tr>
        </thead>
        <tbody>
          {NOTIFICATION_EVENTS.map((ev) => {
            const label = t[`event_${ev.key}` as keyof typeof t] as string;
            return (
              <tr key={ev.key} className="border-b border-subtle last:border-b-0">
                <td className="py-1.5 text-12 text-primary">{label}</td>
                <td className="py-1.5 text-center">
                  <ToggleSwitch
                    value={nilai[ev.inbox]}
                    label={`${label}: ${t.col_inbox}`}
                    onChange={() => onUbah(ev.inbox, !nilai[ev.inbox])}
                    disabled={kunci(ev.inbox)}
                  />
                </td>
                <td className="py-1.5 text-center">
                  <ToggleSwitch
                    value={nilai[ev.email]}
                    label={`${label}: ${t.col_email}`}
                    onChange={() => onUbah(ev.email, !nilai[ev.email])}
                    disabled={kunci(ev.email)}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="space-y-0.5">
        <span className="block text-11 font-medium text-secondary">{t.digest_title}</span>
        <span className="block text-11 text-tertiary">{t.digest_note}</span>
        <Saklar
          label={t.daily_digest}
          nilai={nilai.daily_digest}
          onUbah={(v) => onUbah("daily_digest", v)}
          disabled={kunci("daily_digest")}
        />
        <Saklar
          label={t.daily_digest_sore}
          nilai={nilai.daily_digest_sore}
          onUbah={(v) => onUbah("daily_digest_sore", v)}
          disabled={kunci("daily_digest_sore")}
        />
        {(nilai.daily_digest || nilai.daily_digest_sore) && (
          <div className="border-l-2 border-subtle pl-3">
            {NOTIFICATION_DIGEST_SECTIONS.map((k) => (
              <Saklar key={k} label={t[k]} nilai={nilai[k]} onUbah={(v) => onUbah(k, v)} disabled={kunci(k)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
