/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kelola member di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Fragment, useState } from "react";
import { ChevronLeft, ChevronRight, Pencil, UserPlus } from "lucide-react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import {
  InstanceHierarkiService,
  InstanceMemberService,
  type TInstanceMember,
  type TMemberFilter,
} from "@plane/services";
import { Loader, ToggleSwitch } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// hooks
import { useUser } from "@/hooks/store";
// local
import { GodmodeLangToggle, useGodmodeStrings } from "@/app/i18n/godmode";
import { inputClass } from "./constants";
import { MemberEditor } from "./member-editor";
import { SessionCell } from "./session-cell";
// types
import type { Route } from "./+types/page";

const memberService = new InstanceMemberService();
const hierarkiService = new InstanceHierarkiService();

const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"];

// Dibangun dari kamus supaya labelnya mengikuti bahasa aktif.

const toastError = (err: unknown, fallback: string, title: string) => {
  const message = (err as { error?: string })?.error ?? fallback;
  setToast({ type: TOAST_TYPE.ERROR, title, message });
};

function waktu(iso: string | null, locale: string) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(locale, {
      day: "2-digit",
      month: "short",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return new Date(iso).toLocaleString("en-US", {
      day: "2-digit",
      month: "short",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }
}

const MembersPage = function MembersPage(_props: Route.ComponentProps) {
  const { s, lang, setLang, fill } = useGodmodeStrings();
  const locale = lang === "id" ? "id-ID" : "en-US";
  const [filter, setFilter] = useState<TMemberFilter>({ page: 1, per_page: 50, sort: "name" });
  const [buatTerbuka, setBuatTerbuka] = useState(false);
  const [form, setForm] = useState({ email: "", display_name: "", password: "" });
  const [sibuk, setSibuk] = useState<string | null>(null);
  const [sedangEdit, setSedangEdit] = useState<string | null>(null);
  // Dipakai menyembunyikan tombol kick di baris sendiri, backend menolaknya,
  // dan tombol yang selalu gagal lebih buruk daripada tombol yang tidak ada.
  const { currentUser } = useUser();

  const { data, isLoading, error, mutate } = useSWR(["INSTANCE_MEMBERS", filter], () => memberService.list(filter), {
    revalidateOnFocus: false,
  });
  // Jabatan + divisi per orang: satu panggilan untuk seluruh workspace, digabung
  // ke baris member lewat id. Tanpa ?workspace = workspace tertua (produksi).
  const { data: hierarki, mutate: mutateHierarki } = useSWR(["INSTANCE_HIERARKI"], () => hierarkiService.ringkasan(), {
    revalidateOnFocus: false,
  });

  // Mengubah saringan wajib kembali ke halaman 1, menyaring dari halaman 2
  // bisa mendarat di hasil kosong padahal datanya ada.
  const ubah = (patch: Partial<TMemberFilter>) => setFilter((f) => ({ ...f, ...patch, page: 1 }));

  const urutan: { value: NonNullable<TMemberFilter["sort"]>; label: string }[] = [
    { value: "name", label: s.members.sort_name },
    { value: "email", label: s.members.sort_email },
    { value: "last_active", label: s.members.sort_last_active },
    { value: "last_login", label: s.members.sort_last_login },
    { value: "created", label: s.members.sort_created },
  ];

  const handleBuat = async () => {
    setSibuk("buat");
    try {
      await memberService.create(form);
      setForm({ email: "", display_name: "", password: "" });
      setBuatTerbuka(false);
      await mutate();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: s.members.account_created,
        message: s.members.account_created_message,
      });
    } catch (err) {
      toastError(err, s.members.create_failed, s.members.failed);
    } finally {
      setSibuk(null);
    }
  };

  const handleUbah = async (m: TInstanceMember, patch: { is_active?: boolean; is_super_admin?: boolean }) => {
    setSibuk(m.id);
    try {
      await memberService.update(m.id, patch);
      await mutate();
      setToast({ type: TOAST_TYPE.SUCCESS, title: s.members.saved, message: m.display_name });
    } catch (err) {
      toastError(err, s.members.save_failed, s.members.failed);
    } finally {
      setSibuk(null);
    }
  };

  const halaman = data?.page ?? 1;
  const totalHalaman = data?.total_pages ?? 1;

  return (
    <PageWrapper
      size="lg"
      header={{
        title: s.members.title,
        description: s.members.description,
        actions: (
          <div className="flex items-center gap-2">
            <GodmodeLangToggle lang={lang} onChange={setLang} />
            <Button variant="primary" size="sm" onClick={() => setBuatTerbuka((v) => !v)}>
              <UserPlus className="size-4" aria-hidden /> {s.members.new_account}
            </Button>
          </div>
        ),
      }}
    >
      {buatTerbuka && (
        <div className="mx-4 space-y-3 rounded border border-subtle bg-layer-1 p-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <input
              className={inputClass}
              placeholder={s.members.email_placeholder}
              aria-label={s.members.email_placeholder}
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            />
            <input
              className={inputClass}
              placeholder={s.members.name_placeholder}
              aria-label={s.members.name_placeholder}
              value={form.display_name}
              onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
            />
            <input
              className={inputClass}
              type="password"
              placeholder={s.members.password_placeholder}
              aria-label={s.members.password_placeholder}
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            />
          </div>
          <p className="text-11 text-secondary">{s.members.smtp_note}</p>
          <div className="flex gap-2">
            <Button variant="primary" size="sm" disabled={sibuk === "buat"} onClick={handleBuat}>
              {s.members.create_account}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setBuatTerbuka(false)}>
              {s.members.cancel}
            </Button>
          </div>
        </div>
      )}

      <div className="mx-4 flex flex-wrap items-center gap-2">
        <input
          className={`${inputClass} min-w-[220px] flex-1`}
          placeholder={s.members.search_placeholder}
          aria-label={s.members.search_placeholder}
          value={filter.search ?? ""}
          onChange={(e) => ubah({ search: e.target.value })}
        />
        <select
          className={inputClass}
          value={filter.status ?? ""}
          aria-label={s.members.all_status}
          onChange={(e) => ubah({ status: (e.target.value || undefined) as TMemberFilter["status"] })}
        >
          <option value="">{s.members.all_status}</option>
          <option value="active">{s.members.active}</option>
          <option value="inactive">{s.members.inactive}</option>
        </select>
        <select
          className={inputClass}
          value={filter.sort ?? "name"}
          aria-label={s.members.sort_by}
          onChange={(e) => ubah({ sort: e.target.value as TMemberFilter["sort"] })}
        >
          {urutan.map((u) => (
            <option key={u.value} value={u.value}>
              {s.members.sort_by}: {u.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mx-4">
        {isLoading ? (
          <Loader className="space-y-2">
            {SKELETON_ROWS.map((k) => (
              <Loader.Item key={k} height="52px" />
            ))}
          </Loader>
        ) : error ? (
          <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
            {s.members.load_failed}
          </div>
        ) : !data?.results.length ? (
          <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
            {s.members.empty}
          </div>
        ) : (
          <div className="overflow-x-auto rounded border border-subtle">
            <table className="w-full min-w-[900px] text-body-sm-regular">
              <thead className="bg-layer-1 text-secondary">
                <tr>
                  <th className="w-10 px-2 py-2 text-center font-medium" title={s.members.col_edit}>
                    <span className="sr-only">{s.members.col_edit}</span>
                  </th>
                  <th className="px-3 py-2 text-left font-medium">{s.members.col_name}</th>
                  <th className="px-3 py-2 text-left font-medium">{s.members.col_position}</th>
                  <th className="px-3 py-2 text-left font-medium">{s.members.col_role}</th>
                  <th className="px-3 py-2 text-center font-medium">{s.members.col_session}</th>
                  <th className="px-3 py-2 text-left font-medium">{s.members.col_last_active}</th>
                  <th className="px-3 py-2 text-left font-medium">{s.members.col_last_login}</th>
                  <th className="px-3 py-2 text-left font-medium">{s.members.col_last_logout}</th>
                  <th className="px-3 py-2 text-center font-medium">{s.members.col_active}</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((m) => (
                  <Fragment key={m.id}>
                    {/* Garis kiri kuning: Super Admin harus bisa dipindai
                        sekilas di antara 90 baris, bukan dicari satu-satu. */}
                    <tr
                      className={`border-t border-subtle ${
                        m.is_super_admin ? "border-l-warning-primary border-l-2 bg-warning-subtle/20" : ""
                      }`}
                    >
                      <td className="w-10 px-2 py-2 text-center">
                        <button
                          type="button"
                          onClick={() => setSedangEdit((id) => (id === m.id ? null : m.id))}
                          title={s.members.edit_hint}
                          aria-label={`${s.members.edit_hint}: ${m.display_name || m.email}`}
                          aria-expanded={sedangEdit === m.id}
                          className={sedangEdit === m.id ? "text-accent-primary" : "text-placeholder"}
                        >
                          <Pencil className="size-4" aria-hidden />
                        </button>
                      </td>
                      <td className="px-3 py-2">
                        <div className="text-primary">{m.display_name}</div>
                        <div className="text-placeholder">{m.email}</div>
                      </td>
                      {/* Jabatan + hitungan divisi dari panggilan hierarki (satu
                      untuk seluruh workspace); "—" kalau ia bukan anggota
                      workspace atau panggilannya belum kembali. */}
                      <td className="px-3 py-2 text-secondary">
                        {(() => {
                          const h = (hierarki?.anggota ?? []).find((a) => a.id === m.id);
                          if (!h) return s.members.no_division;
                          // Jabatan kosong = staf (keputusan user).
                          const jab =
                            h.tingkat === null ? s.members.staff_position : (h.tingkat_nama ?? String(h.tingkat));
                          return fill(s.members.position_divisions, { jabatan: jab, n: h.divisi.length });
                        })()}
                      </td>
                      <td className="px-3 py-2 text-secondary">
                        {m.workspace_role
                          ? m.workspace_role === 20
                            ? s.members.role_admin
                            : m.workspace_role === 5
                              ? s.members.role_guest
                              : s.members.role_member
                          : s.members.no_division}
                      </td>
                      <td className="px-3 py-2">
                        <SessionCell
                          userId={m.id}
                          nama={m.display_name || m.email}
                          masihLogin={m.masih_login}
                          sedangMemakai={m.sedang_memakai}
                          diriSendiri={m.id === currentUser?.id}
                          onSelesai={() => mutate()}
                        />
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-secondary">{waktu(m.last_active, locale)}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-secondary">
                        <div>{waktu(m.last_login_time, locale)}</div>
                        {m.last_login_ip ? <div className="text-placeholder">{m.last_login_ip}</div> : null}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-secondary">
                        {waktu(m.last_logout_time, locale)}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <ToggleSwitch
                          value={m.is_active}
                          onChange={() => handleUbah(m, { is_active: !m.is_active })}
                          disabled={sibuk === m.id}
                        />
                      </td>
                    </tr>
                    {sedangEdit === m.id && (
                      <tr>
                        <td colSpan={9} className="p-0">
                          <MemberEditor
                            member={m}
                            hierarki={(hierarki?.anggota ?? []).find((a) => a.id === m.id)}
                            daftarDivisi={Object.keys(hierarki?.projects ?? {})}
                            petaDivisi={hierarki?.projects ?? {}}
                            namaDivisi={hierarki?.project_names ?? {}}
                            pilihanDepartemen={hierarki?.departemen_pilihan ?? []}
                            pilihanDivisi={hierarki?.divisi_pilihan ?? []}
                            onSelesai={async () => {
                              await mutate();
                              await mutateHierarki();
                            }}
                            onTutup={() => setSedangEdit(null)}
                            onCabutSuperAdmin={() => handleUbah(m, { is_super_admin: false })}
                            sibukSuperAdmin={sibuk === m.id}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data && data.count > 0 && (
        <div className="mx-4 flex items-center justify-between">
          <span className="text-body-sm-regular text-secondary">
            {fill(s.members.accounts_count, { count: data.count, page: halaman, total: totalHalaman })}
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={halaman <= 1}
              onClick={() => setFilter((f) => ({ ...f, page: halaman - 1 }))}
            >
              <ChevronLeft className="size-4" aria-hidden /> {s.members.prev}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={halaman >= totalHalaman}
              onClick={() => setFilter((f) => ({ ...f, page: halaman + 1 }))}
            >
              {s.members.next} <ChevronRight className="size-4" aria-hidden />
            </Button>
          </div>
        </div>
      )}
    </PageWrapper>
  );
};

export default observer(MembersPage);
