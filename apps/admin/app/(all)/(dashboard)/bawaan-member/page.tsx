/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bawaan member baru di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Setelan yang diterima akun baru (KEP-44). Server: plane/utils/bawaan_member.py.
 * Profil dan tabel email per jabatan ditulis sekali saat akun lahir (akun lama tak
 * berubah); keanggotaan dipakai saat akun dibuat.
 */

import { useState } from "react";
import type { ReactNode } from "react";
import useSWR from "swr";
import { Button } from "@plane/propel/button";
import { setPromiseToast } from "@plane/propel/toast";
import { InstanceMemberService, type TMemberDefaults, type TSaklarEmail } from "@plane/services";
import { CustomSelect, Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { Field } from "@/components/common/paradise-ui";
import { UnsavedBar } from "@/components/common/unsaved-changes";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { MembersTabs } from "@/components/common/section-tabs";
import { BidangProfil } from "../members/bidang-profil";
import { BidangNavigasi, BidangTataLetak } from "../members/bidang-tampilan";
import { TerapkanKeSemua } from "./terapkan";
import { MatriksNotifikasi } from "../members/matriks-notifikasi";
import type { Route } from "./+types/page";

const memberService = new InstanceMemberService();

type TKelompokEmail = keyof TMemberDefaults["email"];
type TKeanggotaan = TMemberDefaults["keanggotaan"];

// Staf, leader (supervisor & manager), direktur. Kolom direktur juga batas atas di server.
const KELOMPOK_EMAIL: readonly TKelompokEmail[] = ["staf", "pimpinan", "direktur"];

const sama = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

function Bagian({ title, note, children }: { title: string; note: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <div className="space-y-0.5">
        <h3 className="text-11 font-medium tracking-wide text-secondary uppercase">{title}</h3>
        <p className="text-12 text-tertiary">{note}</p>
      </div>
      <div className="space-y-3 rounded-card border border-subtle px-4 py-3">{children}</div>
    </section>
  );
}

function BawaanMemberPage(_props: Route.ComponentProps) {
  const { s } = useGodmodeStrings();
  const t = s.bawaan;
  const judulKelompok: Record<TKelompokEmail, string> = {
    staf: t.col_staf,
    pimpinan: t.col_pimpinan,
    direktur: t.col_direktur,
  };
  const { data, error, mutate } = useSWR("INSTANCE_MEMBER_DEFAULTS", () => memberService.bawaan());
  // null = belum disentuh, tampilkan nilai server apa adanya.
  const [draf, setDraf] = useState<TMemberDefaults | null>(null);
  const [sedangSimpan, setSedangSimpan] = useState(false);

  const tersimpan: TMemberDefaults | null = data
    ? {
        profile: data.profile,
        email: data.email,
        keanggotaan: data.keanggotaan,
        navigasi: data.navigasi,
        work_items: data.work_items,
      }
    : null;
  const nilai = draf ?? tersimpan;
  const berubah = Boolean(draf && tersimpan && !sama(draf, tersimpan));

  const ubah = (f: (b: TMemberDefaults) => TMemberDefaults) => {
    if (!tersimpan) return;
    setDraf((d) => f(d ?? tersimpan));
  };

  const ubahEmail = (kelompok: TKelompokEmail, kunci: keyof TSaklarEmail, v: boolean) =>
    ubah((b) => ({ ...b, email: { ...b.email, [kelompok]: { ...b.email[kelompok], [kunci]: v } } }));

  const ubahKeanggotaan = (k: Partial<TKeanggotaan>) =>
    ubah((b) => ({ ...b, keanggotaan: { ...b.keanggotaan, ...k } }));

  const simpan = async () => {
    if (!draf) return;
    setSedangSimpan(true);
    const janji = memberService.ubahBawaan(draf);
    setPromiseToast(janji, {
      loading: t.saving,
      success: { title: t.saved, message: () => t.title },
      error: { title: t.save_failed, message: (e) => (e as { error?: string })?.error ?? t.save_failed },
    });
    try {
      await mutate(await janji, { revalidate: false });
      setDraf(null);
    } catch {
      // Toast sudah memberi tahu; draf dibiarkan supaya tidak hilang.
    } finally {
      setSedangSimpan(false);
    }
  };

  const tingkatPilihan: { value: 10 | 20 | 30; label: string }[] = [
    { value: 10, label: s.editor.position_member },
    { value: 20, label: s.editor.position_supervisor },
    { value: 30, label: s.editor.position_manager },
  ];

  // Data lama bisa menyimpan null; server menghitungnya staf, jadi tampilkan Staff.
  const tingkatTerpilih = nilai?.keanggotaan.tingkat ?? 10;

  return (
    <PageWrapper
      header={{
        title: s.members.title,
        description: t.description,
      }}
    >
      <MembersTabs />
      <UnsavedBar isDirty={berubah} isSaving={sedangSimpan} onSave={simpan} onDiscard={() => setDraf(null)} />
      {error && <p className="text-13 text-danger-primary">{t.load_failed}</p>}
      {!error && !nilai && (
        <Loader className="space-y-4">
          <Loader.Item height="120px" />
          <Loader.Item height="120px" />
        </Loader>
      )}
      {nilai && data && (
        <div className="space-y-8">
          <Bagian title={t.group_profile} note={t.profile_note}>
            <BidangProfil
              profile={nilai.profile}
              onProfil={(p) => ubah((b) => ({ ...b, profile: { ...b.profile, ...p } }))}
            />
          </Bagian>

          <Bagian title={t.group_email} note={t.email_note}>
            <div className="grid gap-6 lg:grid-cols-2 2xl:grid-cols-3">
              {KELOMPOK_EMAIL.map((kelompok) => (
                <div key={kelompok} className="space-y-1.5">
                  <span className="block text-11 font-medium text-secondary">{judulKelompok[kelompok]}</span>
                  {kelompok === "direktur" && <p className="text-11 text-warning-primary">{t.direktur_note}</p>}
                  <MatriksNotifikasi nilai={nilai.email[kelompok]} onUbah={(k, v) => ubahEmail(kelompok, k, v)} />
                </div>
              ))}
            </div>
          </Bagian>

          <Bagian title={t.group_membership} note={t.membership_note}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={s.editor.workspace_role} hint={t.role_note}>
                <CustomSelect
                  value={nilai.keanggotaan.workspace_role}
                  label={nilai.keanggotaan.workspace_role === 5 ? s.members.role_guest : s.members.role_member}
                  onChange={(v: 5 | 15) => ubahKeanggotaan({ workspace_role: Number(v) as 5 | 15 })}
                  buttonClassName="w-full"
                  className="w-full"
                  input
                >
                  <CustomSelect.Option value={15}>{s.members.role_member}</CustomSelect.Option>
                  <CustomSelect.Option value={5}>{s.members.role_guest}</CustomSelect.Option>
                </CustomSelect>
              </Field>
              <Field label={s.editor.position} hint={t.position_note}>
                <CustomSelect
                  value={tingkatTerpilih}
                  label={tingkatPilihan.find((p) => p.value === tingkatTerpilih)?.label}
                  onChange={(v: number) => ubahKeanggotaan({ tingkat: Number(v) as 10 | 20 | 30 })}
                  buttonClassName="w-full"
                  className="w-full"
                  input
                >
                  {tingkatPilihan.map((p) => (
                    <CustomSelect.Option key={p.value} value={p.value}>
                      {p.label}
                    </CustomSelect.Option>
                  ))}
                </CustomSelect>
              </Field>
            </div>
          </Bagian>

          <Bagian title={t.group_navigation} note={t.navigation_note}>
            <BidangNavigasi
              nilai={nilai.navigasi}
              onUbah={(n) => ubah((b) => ({ ...b, navigasi: { ...b.navigasi, ...n } }))}
            />
          </Bagian>

          <Bagian title={t.group_work_items} note={t.work_items_note}>
            <BidangTataLetak
              nilai={nilai.work_items.layout}
              onUbah={(layout) => ubah((b) => ({ ...b, work_items: { layout } }))}
            />
          </Bagian>

          <div className="flex flex-wrap items-center gap-3 border-t border-subtle pt-4">
            <Button variant="primary" size="base" disabled={!berubah || sedangSimpan} onClick={() => void simpan()}>
              {t.save}
            </Button>
            <Button
              variant="secondary"
              size="base"
              disabled={sedangSimpan || sama(nilai, data.pabrik)}
              onClick={() => setDraf(data.pabrik)}
            >
              {t.reset}
            </Button>
            {berubah && <span className="text-11 text-warning-primary">{t.unsaved}</span>}
          </div>

          <TerapkanKeSemua isDirty={berubah} />
        </div>
      )}
    </PageWrapper>
  );
}

export const meta: Route.MetaFunction = () => [{ title: "New member defaults - God Mode" }];

export default BawaanMemberPage;
