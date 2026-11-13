/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: filter & urutan daftar akun God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Daftar akun kecil (puluhan orang), jadi seluruhnya dimuat lalu disaring di
 * klien. Itu satu-satunya cara menyaring kolom yang datang dari ringkasan
 * hierarki (jabatan, departemen, divisi) tanpa join baru di backend.
 */

import {
  CalendarClock,
  CalendarPlus,
  CircleDot,
  Building2,
  KeyRound,
  LogIn,
  LogOut,
  Mail,
  MonitorSmartphone,
  Network,
  ShieldCheck,
  UserCog,
  Users,
  Wifi,
} from "lucide-react";
import {
  TINGKAT_DIREKTUR,
  TINGKAT_MANAGER,
  TINGKAT_SEKRETARIS,
  TINGKAT_SUPERVISOR,
  type TAnggotaHierarki,
  type THierarkiResponse,
  type TInstanceMember,
} from "@plane/services";
import type { TFilterField, TViewState } from "@/components/common/data-view";
import type { TGodmodeStrings } from "@/app/i18n/godmode";

export type TLevel = "director" | "secretary" | "manager" | "supervisor" | "staff" | "unset" | "outside";
export type TSesi = "in_use" | "signed_in" | "signed_out";

export type TBarisMember = TInstanceMember & {
  h: TAnggotaHierarki | undefined;
  level: TLevel;
  sesi: TSesi;
  penempatan: string | null;
  departemenIds: string[];
  divisiIds: string[];
};

export const levelDari = (h: TAnggotaHierarki | undefined): TLevel => {
  if (!h) return "outside";
  if (h.tingkat === null) return "unset";
  if (h.tingkat >= TINGKAT_DIREKTUR) return "director";
  if (h.tingkat >= TINGKAT_SEKRETARIS) return "secretary";
  if (h.tingkat >= TINGKAT_MANAGER) return "manager";
  if (h.tingkat >= TINGKAT_SUPERVISOR) return "supervisor";
  return "staff";
};

/** Urutan jabatan dari yang paling luas, untuk mengurutkan kolom Position. */
export const URUTAN_LEVEL: Record<TLevel, number> = {
  director: 0,
  secretary: 1,
  manager: 2,
  supervisor: 3,
  staff: 4,
  unset: 5,
  outside: 6,
};

const URUTAN_SESI: Record<TSesi, number> = { in_use: 0, signed_in: 1, signed_out: 2 };
export const urutanSesi = (s: TSesi): number => URUTAN_SESI[s];

/** "Finance · ACC"; direktur menjangkau seluruh perusahaan, tidak ditempatkan. */
const labelPenempatan = (h: TAnggotaHierarki, hierarki: THierarkiResponse | undefined): string | null => {
  if (h.departemen_id) {
    const d = hierarki?.departemen_pilihan?.find((x) => x.id === h.departemen_id);
    if (d) return `${d.nama} · ${d.kode}`;
  }
  if (h.divisi_id) {
    const v = hierarki?.divisi_pilihan?.find((x) => x.id === h.divisi_id);
    if (v) return `${v.nama} · ${v.kode}`;
  }
  return null;
};

export const bangunBaris = (members: TInstanceMember[], hierarki: THierarkiResponse | undefined): TBarisMember[] => {
  const orang = new Map((hierarki?.anggota ?? []).map((a) => [a.id, a]));
  const departemen = new Map((hierarki?.departemen_pilihan ?? []).map((d) => [d.id, d]));
  return members.map((m) => {
    const h = orang.get(m.id);
    const departemenIds = h
      ? [...new Set([...(h.departemen_ids ?? []), ...(h.departemen_id ? [h.departemen_id] : [])])]
      : [];
    // Staf yang ditempatkan di departemen ikut divisi departemen itu.
    const divisiIds = [
      ...new Set([
        ...(h?.divisi_id ? [h.divisi_id] : []),
        ...departemenIds.map((id) => departemen.get(id)?.divisi_id).filter((x): x is string => Boolean(x)),
      ]),
    ];
    return {
      ...m,
      h,
      level: levelDari(h),
      sesi: m.sedang_memakai ? "in_use" : m.masih_login ? "signed_in" : "signed_out",
      penempatan: h ? labelPenempatan(h, hierarki) : null,
      departemenIds,
      divisiIds,
    };
  });
};

export const labelLevel = (level: TLevel, s: TGodmodeStrings): string =>
  ({
    director: s.members.level_director,
    secretary: s.members.level_secretary,
    manager: s.members.level_manager,
    supervisor: s.members.level_supervisor,
    staff: s.members.level_staff,
    unset: s.members.level_unset,
    outside: s.members.not_in_workspace,
  })[level];

export const labelPeran = (role: number | null, s: TGodmodeStrings): string =>
  role === 20
    ? s.members.role_admin
    : role === 15
      ? s.members.role_member
      : role === 5
        ? s.members.role_guest
        : s.members.role_none;

export const labelSesi = (sesi: TSesi, s: TGodmodeStrings): string =>
  ({
    in_use: s.members.session_in_use,
    signed_in: s.members.session_signed_in,
    signed_out: s.members.session_signed_out,
  })[sesi];

/** Medium masuk mentah dari backend ("email", "google", …) ke teks yang terbaca. */
export const labelMetode = (medium: string | null, s: TGodmodeStrings): string => {
  if (!medium) return s.members.unknown;
  return medium.charAt(0).toUpperCase() + medium.slice(1).replace(/[-_]/g, " ");
};

export const VIEW_BAWAAN: TViewState = {
  search: "",
  conditions: [],
  sort: { key: "member", dir: "asc" },
  hidden: ["sign_in_ip", "sign_in_method", "last_logout", "created"],
  perPage: 50,
};

export const teksCari = (r: TBarisMember): string =>
  `${r.display_name} ${r.first_name} ${r.last_name} ${r.email} ${r.penempatan ?? ""} ${r.last_login_ip ?? ""}`;

export const bangunField = (
  rows: TBarisMember[],
  hierarki: THierarkiResponse | undefined,
  s: TGodmodeStrings
): TFilterField<TBarisMember>[] => {
  const m = s.members;
  const metode = [...new Set(rows.map((r) => r.last_login_medium ?? ""))];
  metode.sort();
  return [
    {
      key: "status",
      label: m.filter_status,
      icon: CircleDot,
      kind: "select",
      options: [
        { value: "active", label: m.active },
        { value: "inactive", label: m.inactive },
      ],
      get: (r) => (r.is_active ? "active" : "inactive"),
    },
    {
      key: "super_admin",
      label: m.filter_super_admin,
      icon: ShieldCheck,
      kind: "select",
      operators: ["is"],
      options: [
        { value: "yes", label: m.yes },
        { value: "no", label: m.no },
      ],
      get: (r) => (r.is_super_admin ? "yes" : "no"),
    },
    {
      key: "level",
      label: m.filter_level,
      icon: UserCog,
      kind: "select",
      options: (Object.keys(URUTAN_LEVEL) as TLevel[]).map((l) => ({ value: l, label: labelLevel(l, s) })),
      get: (r) => r.level,
    },
    {
      key: "department",
      label: m.filter_department,
      icon: Users,
      kind: "select",
      options: [
        ...(hierarki?.departemen_pilihan ?? []).map((d) => ({ value: d.id, label: `${d.nama} · ${d.kode}` })),
        { value: "none", label: m.not_placed },
      ],
      get: (r) => (r.departemenIds.length ? r.departemenIds : "none"),
    },
    {
      key: "division",
      label: m.filter_division,
      icon: Building2,
      kind: "select",
      options: [
        ...(hierarki?.divisi_pilihan ?? []).map((d) => ({ value: d.id, label: `${d.nama} · ${d.kode}` })),
        { value: "none", label: m.not_placed },
      ],
      get: (r) => (r.divisiIds.length ? r.divisiIds : "none"),
    },
    {
      key: "access",
      label: m.col_access,
      icon: KeyRound,
      kind: "select",
      options: [20, 15, 5, 0].map((v) => ({ value: String(v), label: labelPeran(v || null, s) })),
      get: (r) => String(r.workspace_role ?? 0),
    },
    {
      key: "session",
      label: m.col_session,
      icon: Wifi,
      kind: "select",
      options: (["in_use", "signed_in", "signed_out"] as TSesi[]).map((v) => ({ value: v, label: labelSesi(v, s) })),
      // "Signed in" mencakup yang sedang memakai: keduanya punya sesi hidup.
      get: (r) => (r.sesi === "in_use" ? ["in_use", "signed_in"] : r.sesi),
    },
    { key: "last_active", label: m.col_last_active, icon: CalendarClock, kind: "date", get: (r) => r.last_active },
    { key: "last_login", label: m.col_last_login, icon: LogIn, kind: "date", get: (r) => r.last_login_time },
    { key: "last_logout", label: m.col_last_logout, icon: LogOut, kind: "date", get: (r) => r.last_logout_time },
    { key: "created", label: m.col_created, icon: CalendarPlus, kind: "date", get: (r) => r.created_at },
    {
      key: "sign_in_method",
      label: m.col_sign_in_method,
      icon: MonitorSmartphone,
      kind: "select",
      options: metode.map((v) => ({ value: v || "none", label: labelMetode(v || null, s) })),
      get: (r) => r.last_login_medium || "none",
    },
    { key: "sign_in_ip", label: m.col_sign_in_ip, icon: Network, kind: "text", get: (r) => r.last_login_ip },
    { key: "email", label: m.filter_email, icon: Mail, kind: "text", get: (r) => r.email },
  ];
};
