/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kelola member di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Susunan daftar mengikuti tampilan work item: cari, Filters (chip per
 * properti), Display (urutan, kolom, baris per halaman), tabel dengan kepala
 * yang bisa diklik untuk mengurutkan. Semua akun dimuat lalu disaring di klien,
 * lihat saringan.ts.
 */

import { useMemo, useState } from "react";
import { Pencil, ShieldCheck, UserPlus } from "lucide-react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { Badge } from "@plane/propel/badge";
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import { InstanceHierarkiService, InstanceMemberService } from "@plane/services";
import { Input, Loader, ToggleSwitch } from "@plane/ui";
// components
import {
  DataTable,
  ViewToolbar,
  applyConditions,
  applySearch,
  paginate,
  sortRows,
  useViewState,
  type TColumn,
} from "@/components/common/data-view";
import { PageWrapper } from "@/components/common/page-wrapper";
import { Pagination, StateBox } from "@/components/common/paradise";
import { formatDateTime, formatRelative } from "@/components/common/paradise-styles";
import { EModalWidth, Field, IconAction, ParadiseModal, PersonCell } from "@/components/common/paradise-ui";
import { MembersTabs } from "@/components/common/section-tabs";
// hooks
import { useUser } from "@/hooks/store";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BadgeJabatan } from "./jabatan";
import { MemberEditor } from "./member-editor";
import {
  URUTAN_LEVEL,
  VIEW_BAWAAN,
  bangunBaris,
  bangunField,
  labelMetode,
  labelPeran,
  teksCari,
  urutanSesi,
  type TBarisMember,
} from "./saringan";
import { SessionCell } from "./session-cell";
// types
import type { Route } from "./+types/page";

const memberService = new InstanceMemberService();
const hierarkiService = new InstanceHierarkiService();

const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"];

const toastError = (err: unknown, fallback: string, title: string) => {
  const message = (err as { error?: string })?.error ?? fallback;
  setToast({ type: TOAST_TYPE.ERROR, title, message });
};

const waktu = (iso: string | null | undefined): number | null => (iso ? new Date(iso).getTime() : null);

function SelWaktu({ iso, never }: { iso: string | null | undefined; never: string }) {
  return (
    <Tooltip tooltipContent={formatDateTime(iso)} disabled={!iso}>
      <span className="whitespace-nowrap text-secondary">{iso ? formatRelative(iso) : never}</span>
    </Tooltip>
  );
}

const MembersPage = function MembersPage(_props: Route.ComponentProps) {
  const { s, fill } = useGodmodeStrings();
  const m = s.members;
  const [buatTerbuka, setBuatTerbuka] = useState(false);
  const [sibuk, setSibuk] = useState<string | null>(null);
  const [sedangEdit, setSedangEdit] = useState<string | null>(null);
  // Dipakai menyembunyikan tombol kick di baris sendiri, backend menolaknya,
  // dan tombol yang selalu gagal lebih buruk daripada tombol yang tidak ada.
  const { currentUser } = useUser();

  const { data, isLoading, error, mutate } = useSWR("INSTANCE_MEMBERS_ALL", () => memberService.listAll(), {
    revalidateOnFocus: false,
  });
  // Jabatan + divisi per orang: satu panggilan untuk seluruh workspace, digabung
  // ke baris member lewat id. Tanpa ?workspace = workspace tertua (produksi).
  const { data: hierarki, mutate: mutateHierarki } = useSWR(["INSTANCE_HIERARKI"], () => hierarkiService.ringkasan(), {
    revalidateOnFocus: false,
  });

  const semua = useMemo(() => bangunBaris(data ?? [], hierarki), [data, hierarki]);
  const fields = useMemo(() => bangunField(semua, hierarki, s), [semua, hierarki, s]);
  const view = useViewState("members", VIEW_BAWAAN, fields);

  const handleUbah = async (row: TBarisMember, patch: { is_active?: boolean; is_super_admin?: boolean }) => {
    setSibuk(row.id);
    try {
      await memberService.update(row.id, patch);
      await mutate();
      setToast({ type: TOAST_TYPE.SUCCESS, title: m.saved, message: row.display_name });
    } catch (err) {
      toastError(err, m.save_failed, m.failed);
    } finally {
      setSibuk(null);
    }
  };

  const columns: TColumn<TBarisMember>[] = [
    {
      key: "member",
      label: m.col_member,
      locked: true,
      className: "max-w-[280px]",
      sortValue: (r) => (r.display_name || r.email).toLowerCase(),
      render: (r) => (
        <button
          type="button"
          onClick={() => setSedangEdit(r.id)}
          className="block w-full min-w-0 rounded-md text-left focus-visible:ring-1 focus-visible:ring-accent-strong focus-visible:outline-none"
        >
          <PersonCell
            name={r.display_name}
            email={r.email}
            muted={!r.is_active}
            badges={
              <>
                {r.is_super_admin && (
                  <Badge variant="warning" size="sm" prependIcon={<ShieldCheck />}>
                    {s.supercell.label}
                  </Badge>
                )}
                {r.id === currentUser?.id && (
                  <Badge variant="brand" size="sm">
                    {m.you}
                  </Badge>
                )}
                {!r.is_active && (
                  <Badge variant="danger" size="sm">
                    {m.deactivated}
                  </Badge>
                )}
              </>
            }
          />
        </button>
      ),
    },
    {
      key: "level",
      label: m.col_position,
      sortValue: (r) => URUTAN_LEVEL[r.level],
      render: (r) =>
        r.h ? (
          <BadgeJabatan tingkat={r.h.tingkat} size="sm" />
        ) : (
          <span className="text-11 text-placeholder">{m.not_in_workspace}</span>
        ),
    },
    {
      key: "placement",
      label: m.col_placement,
      sortValue: (r) => r.penempatan,
      render: (r) =>
        r.h ? (
          <span className="block max-w-[200px] truncate text-11 text-tertiary">
            {r.penempatan ?? (r.h.divisi.length > 0 ? fill(m.divisions_count, { n: r.h.divisi.length }) : m.not_placed)}
          </span>
        ) : (
          <span className="text-placeholder">—</span>
        ),
    },
    {
      key: "access",
      label: m.col_access,
      sortValue: (r) => (r.workspace_role === null ? null : -r.workspace_role),
      render: (r) =>
        r.workspace_role ? (
          <Badge variant={r.workspace_role === 20 ? "brand" : "neutral"}>{labelPeran(r.workspace_role, s)}</Badge>
        ) : (
          <span className="text-placeholder">—</span>
        ),
    },
    {
      key: "session",
      label: m.col_session,
      sortValue: (r) => urutanSesi(r.sesi),
      render: (r) => (
        <SessionCell
          userId={r.id}
          nama={r.display_name || r.email}
          masihLogin={r.masih_login}
          sedangMemakai={r.sedang_memakai}
          diriSendiri={r.id === currentUser?.id}
          onSelesai={() => mutate()}
        />
      ),
    },
    {
      key: "last_active",
      label: m.col_last_active,
      sortValue: (r) => waktu(r.last_active),
      render: (r) => <SelWaktu iso={r.last_active} never={m.never} />,
    },
    {
      key: "last_login",
      label: m.col_sign_in,
      sortValue: (r) => waktu(r.last_login_time),
      render: (r) => <SelWaktu iso={r.last_login_time} never={m.never} />,
    },
    {
      key: "sign_in_ip",
      label: m.col_sign_in_ip,
      sortValue: (r) => r.last_login_ip,
      render: (r) => <span className="font-code text-11 text-tertiary">{r.last_login_ip || "—"}</span>,
    },
    {
      key: "sign_in_method",
      label: m.col_sign_in_method,
      sortValue: (r) => r.last_login_medium,
      render: (r) => <span className="text-secondary">{labelMetode(r.last_login_medium, s)}</span>,
    },
    {
      key: "last_logout",
      label: m.col_last_logout,
      sortValue: (r) => waktu(r.last_logout_time),
      render: (r) => <SelWaktu iso={r.last_logout_time} never={m.never} />,
    },
    {
      key: "created",
      label: m.col_created,
      sortValue: (r) => waktu(r.created_at),
      render: (r) => <SelWaktu iso={r.created_at} never={m.never} />,
    },
    {
      key: "active",
      label: m.col_active,
      headClassName: "text-center",
      className: "text-center",
      sortValue: (r) => (r.is_active ? 0 : 1),
      render: (r) => (
        <ToggleSwitch
          value={r.is_active}
          label={`${m.col_active}: ${r.display_name || r.email}`}
          onChange={() => handleUbah(r, { is_active: !r.is_active })}
          disabled={sibuk === r.id}
        />
      ),
    },
    {
      key: "edit",
      label: m.col_edit,
      locked: true,
      srOnlyLabel: true,
      headClassName: "w-12",
      className: "text-right",
      render: (r) => (
        <IconAction
          label={fill(m.edit_member, { name: r.display_name || r.email })}
          icon={Pencil}
          onClick={() => setSedangEdit(r.id)}
        />
      ),
    },
  ];

  const kolomUrut = columns.find((c) => c.key === view.sort.key)?.sortValue;
  const tersaring = sortRows(
    applyConditions(applySearch(semua, view.search, teksCari), fields, view.conditions),
    view.sort,
    kolomUrut
  );
  const halaman = paginate(tersaring, view.page, view.perPage);
  const diedit = semua.find((r) => r.id === sedangEdit);

  return (
    <PageWrapper
      header={{
        title: m.title,
        description: m.description,
        actions: (
          <Button variant="primary" size="sm" prependIcon={<UserPlus />} onClick={() => setBuatTerbuka(true)}>
            {m.new_account}
          </Button>
        ),
      }}
    >
      <MembersTabs />
      <div className="space-y-3">
        <ViewToolbar
          view={view}
          fields={fields}
          searchPlaceholder={m.search_placeholder}
          sortOptions={columns.filter((c) => c.sortValue).map((c) => ({ key: c.key, label: c.label }))}
          columns={columns.filter((c) => !c.locked).map((c) => ({ key: c.key, label: c.label }))}
          summary={
            data &&
            (tersaring.length === semua.length
              ? fill(m.count_all, { n: semua.length })
              : fill(m.count_filtered, { n: tersaring.length, total: semua.length }))
          }
        />

        {isLoading ? (
          <Loader className="space-y-2">
            {SKELETON_ROWS.map((k) => (
              <Loader.Item key={k} height="56px" />
            ))}
          </Loader>
        ) : error ? (
          <StateBox tone="danger">{m.load_failed}</StateBox>
        ) : tersaring.length === 0 ? (
          <StateBox>{m.empty}</StateBox>
        ) : (
          <DataTable
            rows={halaman.rows}
            columns={columns}
            hidden={view.hidden}
            sort={view.sort}
            onSort={view.setSort}
            rowKey={(r) => r.id}
            // Super Admin harus bisa dipindai sekilas di antara puluhan baris.
            rowClassName={(r) => (r.is_super_admin ? "bg-warning-subtle" : undefined)}
            minWidth={960}
          />
        )}

        {tersaring.length > view.perPage && (
          <Pagination
            summary={fill(m.page_summary, { page: halaman.page, total: halaman.totalPages })}
            page={halaman.page}
            totalPages={halaman.totalPages}
            onChange={view.setPage}
            prevLabel={s.common.prev_page}
            nextLabel={s.common.next_page}
          />
        )}
      </div>

      <ModalAkunBaru
        isOpen={buatTerbuka}
        onClose={() => setBuatTerbuka(false)}
        onDibuat={async () => {
          await mutate();
          await mutateHierarki();
        }}
      />

      {diedit && (
        // Kunci per orang: membuka orang lain mulai dari keadaan form yang bersih.
        <MemberEditor
          key={diedit.id}
          member={diedit}
          hierarki={diedit.h}
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
          onCabutSuperAdmin={() => handleUbah(diedit, { is_super_admin: false })}
          sibukSuperAdmin={sibuk === diedit.id}
        />
      )}
    </PageWrapper>
  );
};

function ModalAkunBaru({
  isOpen,
  onClose,
  onDibuat,
}: {
  isOpen: boolean;
  onClose: () => void;
  onDibuat: () => Promise<unknown>;
}) {
  const { s } = useGodmodeStrings();
  const [form, setForm] = useState({ email: "", display_name: "", password: "" });
  const [sibuk, setSibuk] = useState(false);
  const pendek = form.password.length > 0 && form.password.length < 8;
  const siap = form.email.trim() && form.display_name.trim() && form.password.length >= 8 && !sibuk;

  const tutup = () => {
    setForm({ email: "", display_name: "", password: "" });
    onClose();
  };

  const handleBuat = async () => {
    if (!siap) return;
    setSibuk(true);
    try {
      await memberService.create(form);
      await onDibuat();
      tutup();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: s.members.account_created,
        message: s.members.account_created_message,
      });
    } catch (err) {
      toastError(err, s.members.create_failed, s.members.failed);
    } finally {
      setSibuk(false);
    }
  };

  return (
    <ParadiseModal
      isOpen={isOpen}
      onClose={tutup}
      width={EModalWidth.LG}
      title={s.members.new_account}
      subtitle={s.members.new_account_subtitle}
      closeLabel={s.editor.close}
      footerNote={s.members.smtp_note}
      footer={
        <>
          <Button variant="secondary" size="sm" onClick={tutup}>
            {s.members.cancel}
          </Button>
          <Button variant="primary" size="sm" disabled={!siap} loading={sibuk} onClick={handleBuat}>
            {s.members.create_account}
          </Button>
        </>
      }
    >
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void handleBuat();
        }}
      >
        <Field label={s.members.field_name}>
          <Input
            className="w-full"
            placeholder={s.members.name_placeholder}
            value={form.display_name}
            onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
          />
        </Field>
        <Field label={s.members.field_email}>
          <Input
            className="w-full"
            type="email"
            placeholder={s.members.email_placeholder}
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          />
        </Field>
        <Field
          label={s.members.field_password}
          hint={s.members.field_password_hint}
          error={pendek ? s.editor.password_too_short : undefined}
        >
          <Input
            className="w-full"
            type="password"
            autoComplete="new-password"
            hasError={pendek}
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          />
        </Field>
        {/* Enter di kolom mana pun mengirim form. */}
        <button type="submit" hidden aria-hidden tabIndex={-1} />
      </form>
    </ParadiseModal>
  );
}

export default observer(MembersPage);
