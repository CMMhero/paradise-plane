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
import {
  InstanceMemberService,
  type TMemberNavigation,
  type TMemberPreferences,
  type TMemberPreferencesUpdate,
  type TWorkItemLayout,
} from "@plane/services";
import { Loader } from "@plane/ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BidangProfil, Saklar, type TProfil } from "./bidang-profil";
import { BidangNavigasi, BidangTataLetak } from "./bidang-tampilan";
import { MatriksNotifikasi } from "./matriks-notifikasi";

const memberService = new InstanceMemberService();

type TNotif = TMemberPreferences["notifications"];

/** Hanya kunci yang nilainya berbeda dari aslinya. */
const selisih = <T extends object>(asli: T, baru: T): Partial<T> =>
  Object.fromEntries(Object.entries(baru).filter(([k, v]) => v !== asli[k as keyof T])) as Partial<T>;

export function useMemberPreferences(memberId: string) {
  const [asli, setAsli] = useState<TMemberPreferences | null>(null);
  const [baru, setBaru] = useState<TMemberPreferences | null>(null);
  const [gagal, setGagal] = useState(false);
  const [layoutDisentuh, setLayoutDisentuh] = useState(false);

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
    const pinned = selisih(asli.navigasi.pinned, baru.navigasi.pinned);
    const navigasi: NonNullable<TMemberPreferencesUpdate["navigasi"]> = {
      ...(baru.navigasi.project_mode !== asli.navigasi.project_mode && { project_mode: baru.navigasi.project_mode }),
      ...(baru.navigasi.project_limit !== asli.navigasi.project_limit && {
        project_limit: baru.navigasi.project_limit,
      }),
      ...(Object.keys(pinned).length > 0 && { pinned }),
    };
    // Tata letak campuran: memilih nilai yang sama dengan mayoritas tetap
    // menyamakan semua project, jadi kirim kalau admin menyentuhnya.
    const layoutBerubah = baru.work_items.layout !== asli.work_items.layout || layoutDisentuh;
    if (
      Object.keys(profile).length === 0 &&
      Object.keys(notifications).length === 0 &&
      Object.keys(navigasi).length === 0 &&
      !layoutBerubah
    )
      return null;
    return {
      profile,
      notifications,
      ...(Object.keys(navigasi).length > 0 && { navigasi }),
      ...(layoutBerubah && { work_items: { layout: baru.work_items.layout } }),
    };
  };

  return {
    nilai: baru,
    gagal,
    ubahProfil: (p: Partial<TProfil>) => setBaru((b) => (b ? { ...b, profile: { ...b.profile, ...p } } : b)),
    ubahNotif: (n: Partial<TNotif>) => setBaru((b) => (b ? { ...b, notifications: { ...b.notifications, ...n } } : b)),
    ubahNavigasi: (n: Partial<TMemberNavigation>) =>
      setBaru((b) => (b ? { ...b, navigasi: { ...b.navigasi, ...n } } : b)),
    ubahTataLetak: (layout: TWorkItemLayout) => {
      setLayoutDisentuh(true);
      setBaru((b) => (b ? { ...b, work_items: { ...b.work_items, layout } } : b));
    },
    perubahan,
  };
}

type Props = {
  nilai: TMemberPreferences | null;
  gagal: boolean;
  onProfil: (p: Partial<TProfil>) => void;
  onNotif: (n: Partial<TNotif>) => void;
  onNavigasi: (n: Partial<TMemberNavigation>) => void;
  onTataLetak: (layout: TWorkItemLayout) => void;
};

export function PreferensiMember({ nilai, gagal, onProfil, onNotif, onNavigasi, onTataLetak }: Props) {
  const { s, fill } = useGodmodeStrings();
  const t = s.editor.prefs;

  if (gagal) return <p className="text-12 text-danger-primary">{t.load_failed}</p>;
  if (!nilai)
    return (
      <Loader className="space-y-2">
        <Loader.Item height="36px" />
        <Loader.Item height="36px" />
      </Loader>
    );

  const { profile, notifications, navigasi, work_items } = nilai;
  const notifikasiDikunci = nilai.notifikasi_dikunci ?? [];
  const catatanTataLetak = work_items.campuran
    ? s.tampilan.layout_mixed
    : fill(s.tampilan.layout_projects, { count: work_items.jumlah_project });
  return (
    <div className="space-y-5">
      <BidangProfil profile={profile} onProfil={onProfil} />

      <BidangTataLetak nilai={work_items.layout} onUbah={onTataLetak} hint={catatanTataLetak} />

      <div className="space-y-2">
        <div>
          <span className="block text-12 font-medium text-secondary">{s.bawaan.group_navigation}</span>
          <span className="block text-11 text-tertiary">{s.tampilan.nav_note}</span>
        </div>
        <BidangNavigasi nilai={navigasi} onUbah={onNavigasi} />
      </div>

      <div className="space-y-2">
        <div>
          <span className="block text-12 font-medium text-secondary">{t.email_title}</span>
          <span className="block text-11 text-tertiary">{t.email_note}</span>
        </div>
        <div className="rounded-md border border-subtle px-3 py-1">
          <Saklar
            label={t.ikut_bawaan_jabatan}
            nilai={notifications.ikut_bawaan_jabatan}
            onUbah={(v) => onNotif({ ikut_bawaan_jabatan: v })}
          />
          <p className="pb-1.5 text-11 text-tertiary">{t.ikut_bawaan_jabatan_note}</p>
        </div>
        <div className="rounded-md border border-subtle px-3 py-2">
          <MatriksNotifikasi
            nilai={notifications}
            // Mengubah satu saklar = berhenti ikut bawaan jabatan (sama dengan server).
            onUbah={(k, v) => onNotif({ [k]: v, ikut_bawaan_jabatan: false })}
            dikunci={notifikasiDikunci}
          />
          {notifikasiDikunci.length > 0 && <p className="pt-1.5 text-11 text-tertiary">{t.locked_note}</p>}
        </div>
      </div>
    </div>
  );
}
