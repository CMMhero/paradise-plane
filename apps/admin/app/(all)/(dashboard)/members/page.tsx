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
import { inputClass, PERAN } from "./constants";
import { MemberEditor } from "./member-editor";
import { SessionCell } from "./session-cell";
// types
import type { Route } from "./+types/page";

const memberService = new InstanceMemberService();
const hierarkiService = new InstanceHierarkiService();

const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"];

const URUTAN: { value: NonNullable<TMemberFilter["sort"]>; label: string }[] = [
  { value: "name", label: "Nama" },
  { value: "email", label: "Email" },
  { value: "last_active", label: "Terakhir aktif" },
  { value: "last_login", label: "Terakhir masuk" },
  { value: "created", label: "Terbaru dibuat" },
];

const toastError = (err: unknown, fallback: string) => {
  const message = (err as { error?: string })?.error ?? fallback;
  setToast({ type: TOAST_TYPE.ERROR, title: "Gagal", message });
};

function waktu(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const MembersPage = function MembersPage(_props: Route.ComponentProps) {
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

  const handleBuat = async () => {
    setSibuk("buat");
    try {
      await memberService.create(form);
      setForm({ email: "", display_name: "", password: "" });
      setBuatTerbuka(false);
      await mutate();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Akun dibuat",
        message: "Sampaikan password awalnya langsung ke orangnya, email undangan belum bisa dikirim.",
      });
    } catch (err) {
      toastError(err, "Tidak bisa membuat akun.");
    } finally {
      setSibuk(null);
    }
  };

  const handleUbah = async (m: TInstanceMember, patch: { is_active?: boolean; is_super_admin?: boolean }) => {
    setSibuk(m.id);
    try {
      await memberService.update(m.id, patch);
      await mutate();
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Tersimpan", message: m.display_name });
    } catch (err) {
      toastError(err, "Tidak bisa menyimpan perubahan.");
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
        title: "Member",
        description:
          "Buat, nonaktifkan, dan atur hak akses akun. Pendaftaran mandiri dimatikan, akun hanya lahir dari sini.",
        actions: (
          <Button variant="primary" size="sm" onClick={() => setBuatTerbuka((v) => !v)}>
            <UserPlus className="size-4" /> Akun baru
          </Button>
        ),
      }}
    >
      {buatTerbuka && (
        <div className="mx-4 space-y-3 rounded border border-subtle bg-layer-1 p-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <input
              className={inputClass}
              placeholder="email@paradiseperkasa.com"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            />
            <input
              className={inputClass}
              placeholder="Nama lengkap"
              value={form.display_name}
              onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
            />
            <input
              className={inputClass}
              type="password"
              placeholder="Password awal (min. 8)"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            />
          </div>
          <p className="text-11 text-secondary">
            Password awal harus kamu sampaikan langsung, SMTP belum jalan, jadi tidak ada email yang terkirim.
          </p>
          <div className="flex gap-2">
            <Button variant="primary" size="sm" disabled={sibuk === "buat"} onClick={handleBuat}>
              Buat akun
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setBuatTerbuka(false)}>
              Batal
            </Button>
          </div>
        </div>
      )}

      <div className="mx-4 flex flex-wrap items-center gap-2">
        <input
          className={`${inputClass} min-w-[220px] flex-1`}
          placeholder="Cari nama atau email…"
          value={filter.search ?? ""}
          onChange={(e) => ubah({ search: e.target.value })}
        />
        <select
          className={inputClass}
          value={filter.status ?? ""}
          onChange={(e) => ubah({ status: (e.target.value || undefined) as TMemberFilter["status"] })}
        >
          <option value="">Semua status</option>
          <option value="active">Aktif</option>
          <option value="inactive">Nonaktif</option>
        </select>
        <select
          className={inputClass}
          value={filter.sort ?? "name"}
          onChange={(e) => ubah({ sort: e.target.value as TMemberFilter["sort"] })}
        >
          {URUTAN.map((u) => (
            <option key={u.value} value={u.value}>
              Urut: {u.label}
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
            Gagal memuat daftar member.
          </div>
        ) : !data?.results.length ? (
          <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
            Tidak ada member yang cocok.
          </div>
        ) : (
          <div className="overflow-x-auto rounded border border-subtle">
            <table className="w-full min-w-[900px] text-body-sm-regular">
              <thead className="bg-layer-1 text-secondary">
                <tr>
                  <th className="w-10 px-2 py-2 text-center font-medium" title="Ubah">
                    <span className="sr-only">Ubah</span>
                  </th>
                  <th className="px-3 py-2 text-left font-medium">Nama</th>
                  <th className="px-3 py-2 text-left font-medium">Jabatan</th>
                  <th className="px-3 py-2 text-left font-medium">Peran</th>
                  <th className="px-3 py-2 text-center font-medium">Sesi</th>
                  <th className="px-3 py-2 text-left font-medium">Terakhir aktif</th>
                  <th className="px-3 py-2 text-left font-medium">Terakhir masuk</th>
                  <th className="px-3 py-2 text-left font-medium">Terakhir keluar</th>
                  <th className="px-3 py-2 text-center font-medium">Aktif</th>
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
                          title="Ubah akun, jabatan, dan divisi"
                          className={sedangEdit === m.id ? "text-accent-primary" : "text-placeholder"}
                        >
                          <Pencil className="size-4" />
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
                          if (!h) return "—";
                          // Jabatan kosong = staf (keputusan user).
                          const jab = h.tingkat === null ? "Member (staf)" : (h.tingkat_nama ?? String(h.tingkat));
                          return `${jab} · ${h.divisi.length} divisi`;
                        })()}
                      </td>
                      <td className="px-3 py-2 text-secondary">
                        {m.workspace_role ? (PERAN[m.workspace_role] ?? m.workspace_role) : "—"}
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
                      <td className="px-3 py-2 whitespace-nowrap text-secondary">{waktu(m.last_active)}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-secondary">
                        <div>{waktu(m.last_login_time)}</div>
                        {m.last_login_ip ? <div className="text-placeholder">{m.last_login_ip}</div> : null}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-secondary">{waktu(m.last_logout_time)}</td>
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
            {data.count} akun · halaman {halaman} dari {totalHalaman}
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={halaman <= 1}
              onClick={() => setFilter((f) => ({ ...f, page: halaman - 1 }))}
            >
              <ChevronLeft className="size-4" /> Sebelumnya
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={halaman >= totalHalaman}
              onClick={() => setFilter((f) => ({ ...f, page: halaman + 1 }))}
            >
              Berikutnya <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      )}
    </PageWrapper>
  );
};

export default observer(MembersPage);
