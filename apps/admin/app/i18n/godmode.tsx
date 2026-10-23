/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kamus God Mode (id/en)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * God Mode (admin) tidak memakai @plane/i18n — ia aplikasi React Router
 * terpisah tanpa TranslationProvider. Supaya tidak ada teks hardcode yang
 * tersebar di tiap berkas, SEMUA string antarmuka God Mode tinggal di sini,
 * dikunci bentuknya oleh tipe: `en` harus punya kunci yang sama persis dengan
 * `id`, kalau kurang, TypeScript yang berteriak saat build.
 *
 * Pilihan bahasa disimpan di localStorage ("paradise-godmode-lang"), default
 * "id" (perilaku lama). Web tetap memakai @plane/i18n seperti biasa — modul
 * ini hanya untuk panel admin.
 */

import { useCallback, useState, type JSX } from "react";

export type TGodmodeLang = "id" | "en";

const LANG_KEY = "paradise-godmode-lang";

/**
 * Frasa konfirmasi ketik-ulang untuk MEMBERI Super Admin (keputusan user
 * 2026-10-22, menggantikan passphrase). Keduanya diterima server apa pun
 * bahasa UI — yang diperiksa adalah niat eksplisit, bukan bahasa.
 */
const FRASA_KONFIRMASI_ID = "jadikan superadmin";
const FRASA_KONFIRMASI_EN = "make superadmin";

export const KONFIRMASI_GRANT = [FRASA_KONFIRMASI_ID, FRASA_KONFIRMASI_EN] as const;

/** Tombol kirim aktif hanya kalau ketikan cocok salah satu frasa (normalisasi
 * huruf/spasi sama seperti server: caps-lock atau spasi ganda tidak
 * menggagalkan yang sah). */
export const cocokKonfirmasiGrant = (ketikan: string): boolean => {
  const normal = ketikan.toLowerCase().split(/\s+/).join(" ").trim();
  return (KONFIRMASI_GRANT as readonly string[]).includes(normal);
};

const id = {
  lang_label: "Bahasa",
  // NOTE: jangan tambah `as const` di sini — tipenya dilebarkan ke `string`
  // supaya `en` di bawah cukup cocok BENTUK (kunci sama), bukan nilai harfiah.
  members: {
    title: "Member",
    description:
      "Buat, nonaktifkan, dan atur hak akses akun. Pendaftaran mandiri dimatikan, akun hanya lahir dari sini.",
    new_account: "Akun baru",
    email_placeholder: "email@paradiseperkasa.com",
    name_placeholder: "Nama lengkap",
    password_placeholder: "Password awal (min. 8)",
    smtp_note: "Password awal harus kamu sampaikan langsung, SMTP belum jalan, jadi tidak ada email yang terkirim.",
    create_account: "Buat akun",
    cancel: "Batal",
    account_created: "Akun dibuat",
    account_created_message: "Sampaikan password awalnya langsung ke orangnya, email undangan belum bisa dikirim.",
    create_failed: "Tidak bisa membuat akun.",
    saved: "Tersimpan",
    save_failed: "Tidak bisa menyimpan perubahan.",
    failed: "Gagal",
    search_placeholder: "Cari nama atau email…",
    all_status: "Semua status",
    active: "Aktif",
    inactive: "Nonaktif",
    sort_by: "Urut",
    sort_name: "Nama",
    sort_email: "Email",
    sort_last_active: "Terakhir aktif",
    sort_last_login: "Terakhir masuk",
    sort_created: "Terbaru dibuat",
    load_failed: "Gagal memuat daftar member.",
    empty: "Tidak ada member yang cocok.",
    col_edit: "Ubah",
    col_name: "Nama",
    col_position: "Jabatan",
    col_role: "Peran",
    col_session: "Sesi",
    col_last_active: "Terakhir aktif",
    col_last_login: "Terakhir masuk",
    col_last_logout: "Terakhir keluar",
    col_active: "Aktif",
    role_admin: "Admin",
    role_member: "Member",
    role_guest: "Tamu",
    edit_hint: "Ubah akun, jabatan, dan divisi",
    no_division: "—",
    staff_position: "Member (staf)",
    divisions_count: "{n} divisi",
    position_divisions: "{jabatan} · {n} divisi",
    accounts_count: "{count} akun · halaman {page} dari {total}",
    prev: "Sebelumnya",
    next: "Berikutnya",
  },
  editor: {
    name: "Nama",
    email: "Email (identitas login)",
    workspace: "Workspace",
    workspace_none: "— Bukan anggota workspace —",
    workspace_role: "Hak akses workspace",
    new_password: "Password baru",
    password_hint: "kosongkan = tidak diubah",
    password_too_short: "Password minimal 8 karakter.",
    position: "Jabatan",
    position_member: "Member (staf)",
    position_supervisor: "Supervisor",
    position_manager: "Manager",
    position_director: "Direktur",
    placement: "Penempatan",
    director_note: "Direktur menjangkau seluruh perusahaan, tidak perlu ditempatkan.",
    led_division: "Divisi yang dipimpin",
    not_placed: "— Belum ditempatkan —",
    manager_note: "Manager melihat semua departemen di divisi ini.",
    department: "Departemen",
    supervisor_note: "Supervisor melihat dan mengelola project departemen ini.",
    staff_note: "Staf melihat semua project departemen ini, mengubah hanya tugas miliknya.",
    extra_projects: "Project tambahan, pengecualian eksplisit ({n})",
    divisions: "Divisi ({n})",
    not_workspace_member: "Bukan anggota workspace — jabatan dan divisi tak bisa diatur.",
    joined: "Masuk: {list}.",
    left: "Keluar: {list}.",
    supervised: "Divisi yang dia bawahi (pengawasan)",
    supervised_empty: "Ikut rumus (kosong)",
    supervised_note:
      "Kosong = ikut rumus (direktur semua divisi; lainnya divisinya sendiri). Centang = menang atas rumus.",
    password_note:
      "Mengubah password atau email mengakhiri semua sesi orang itu, dia harus masuk lagi. Manager/supervisor otomatis jadi Admin di divisinya; member jadi Member biasa. Password barunya sampaikan langsung; SMTP belum jalan, tidak ada email yang terkirim.",
    superadmin_badge: "Super Admin — akses seluruh project.",
    revoke: "Cabut",
    make_superadmin: "Jadikan Super Admin",
    make_superadmin_note:
      "Akses seluruh project termasuk yang dibuat nanti. Ketik frasa di bawah persis untuk mengonfirmasi.",
    confirm_phrase: FRASA_KONFIRMASI_ID,
    confirm_instruction: "Ketik {phrase} untuk mengonfirmasi.",
    grant_superadmin: "Beri Super Admin",
    save: "Simpan",
    cancel: "Batal",
    superadmin_granted: "Super Admin diberikan",
    superadmin_granted_message: "{name} sekarang mengakses semua project.",
    grant_denied: "Ditolak",
    grant_failed: "Tidak bisa memberi Super Admin.",
    saved_ok: "Tersimpan",
    saved_message: "{name}: {jabatan}, {n} divisi.",
    saved_message_sessions: "{name}: {jabatan}, {n} divisi, {sesi} sesi diakhiri.",
    save_failed: "Gagal menyimpan",
    save_failed_message: "Tidak bisa menyimpan.",
    delete_zone: "Hapus akun ini",
    delete_zone_note: "Nonaktif + gosok identitas. Riwayat tetap utuh.",
    delete_open: "Hapus…",
    delete_confirm: "Ketik {name} persis untuk mengonfirmasi. Tidak bisa dibatalkan.",
    delete_now: "Hapus permanen",
    account_deleted: "Akun dihapus",
    account_deleted_message:
      "{name} dinonaktifkan dan identitasnya digosok ({sesi} sesi diakhiri). Riwayat tetap utuh.",
    delete_failed: "Gagal menghapus",
    delete_failed_message: "Tidak bisa menghapus akun.",
  },
  picker: {
    default_placeholder: "Pilih…",
    select_all: "Pilih semua",
    clear: "Bersihkan",
    empty: "Tidak ada divisi yang cocok.",
    search_placeholder: "Cari…",
    chosen_count: "{n} divisi dipilih",
  },
  grant: {
    title: "Jadikan {name} Super Admin?",
    description:
      "Dia akan mengakses seluruh project, termasuk yang dibuat setelah ini, tanpa muncul di daftar anggota mana pun. Ketik frasa di bawah persis untuk melanjutkan.",
    confirm_phrase: FRASA_KONFIRMASI_ID,
    confirm_instruction: "Ketik {phrase} untuk mengonfirmasi.",
    confirm: "Beri Super Admin",
    cancel: "Batal",
    granted: "Super Admin diberikan",
    granted_message: "{name} sekarang mengakses semua project, termasuk yang dibuat nanti.",
    denied: "Ditolak",
    failed: "Tidak bisa memberi Super Admin.",
  },
  session: {
    active: "Sedang memakai",
    active_hint: "Ada request dalam beberapa menit terakhir",
    idle: "Masih login",
    idle_hint: "Sesi masih hidup, tapi tidak ada aktivitas terbaru",
    out: "Keluar",
    out_hint: "Tidak ada sesi hidup",
    kick_confirm: "Putuskan semua sesi {name}? Dia akan diminta login lagi.",
    kicked: "Sesi diputus",
    kicked_message: "{n} sesi {name} diakhiri.",
    failed: "Gagal",
    kick_failed: "Tidak bisa memutus sesi.",
    kick_hint: "Putuskan sesi, dia harus login lagi",
    kick_label: "Putuskan sesi {name}",
  },
  supercell: {
    revoke_hint: "Cabut status Super Admin",
    label: "Super Admin",
    grant_hint: "Jadikan Super Admin, perlu konfirmasi ketik",
    grant_label: "Jadikan",
  },
  org: {
    title: "Struktur organisasi",
    description:
      "Divisi berisi departemen, departemen berisi project dan orang. Staf & supervisor melihat project departemennya, manager melihat semua departemen di divisinya, direktur melihat semuanya.",
    new_division: "Divisi baru",
    division_created: "Divisi {kode} dibuat",
    division_saved: "Divisi {kode} disimpan",
    division_deleted: "Divisi dihapus",
    department_saved: "Departemen disimpan",
    department_created: "Departemen {kode} dibuat",
    department_deleted: "Departemen dihapus",
    new_department: "Departemen baru",
    code_placeholder: "Kode",
    name_placeholder: "Nama",
    save_failed: "Gagal",
    save_failed_message: "Tidak bisa menyimpan.",
    no_division: "Belum ada divisi. Selama kosong, akses tetap mengikuti keanggotaan project seperti sebelumnya.",
    departments_count: "· {n} departemen",
    division_manager: "Manager divisi",
    no_manager: "Belum ada manager. Calon hanya orang berjenjang Manager (atur jenjang di halaman Member).",
    member_moved_from: "{name} (pindah dari {from})",
    person_placed: "{name} ditempatkan",
    person_removed: "{name} dikeluarkan",
    placed_message: "Akses project-nya sudah disesuaikan.",
    members: "Anggota",
    no_members: "Belum ada orang di departemen ini.",
    add_person: "Tambah orang…",
    add: "Tambah",
    not_yet_leveled: "belum berjenjang, jadi Staf",
    moved_from: ", pindah dari {from}",
    moved_from_bare: "pindah dari {from}",
    move_target_other: "departemen lain",
    move_division_other: "divisi lain",
    remove_person: "Keluarkan {name}",
    projects: "Project ({n})",
    project_picker: "Pilih project…",
    save_projects: "Simpan project",
    projects_moved_note: "Project yang sudah di departemen lain akan dipindah ke sini; akses orangnya menyesuaikan.",
    edit_label: "Ubah {kind} {name}",
    delete_label: "Hapus {kind} {name}",
    kind_division: "divisi",
    kind_department: "departemen",
    save: "Simpan",
    cancel: "Batal",
    division_of: "Divisi",
    division_of_dept: "Divisi departemen {name}",
    legacy_title: "Project yang belum punya departemen ({n})",
    legacy_description:
      "Ini struktur lama (satu divisi = satu project). Jadikan departemen di sebuah divisi untuk membawanya ke struktur baru; sampai saat itu ia hanya terlihat oleh anggota eksplisitnya.",
    legacy_create_first: " Buat divisi dulu di atas.",
    legacy_close: "Tutup",
    legacy_convert: "Jadikan departemen…",
    legacy_bring: "Bawa anggota project ini ke departemen ({a} dari {b})",
    legacy_loading: "Memuat anggota…",
    legacy_make: "Jadikan departemen",
    legacy_kept_note: "Yang tidak dicentang tetap anggota project sebagai pengecualian, tanpa penempatan.",
    legacy_done: "{kode} jadi departemen",
    legacy_done_message: "{a} orang ditempatkan{b}.",
    legacy_done_skipped: ", {n} manager/direktur dilewati",
    legacy_done_all: ".",
    legacy_director_reach: " (menjangkau seluruh perusahaan)",
    legacy_division_placed: " (ditempatkan lewat divisi)",
    legacy_unleveled: "belum berjenjang, jadi Staf",
    failed: "Gagal",
    tree_title: "Peta organisasi",
    tree_hint: "Gambaran seluruh struktur. Klik sebuah kotak untuk lompat ke kartunya di bawah.",
    stat_division: "Divisi",
    stat_department: "Departemen",
    stat_project: "Project",
    stat_manager: "Manager",
    stat_supervisor: "Supervisor",
    stat_staff: "Staf",
    stat_unplaced: "Belum ditempatkan",
    stat_unleveled: "Belum berjenjang",
    directors: "Direktur — menjangkau seluruh perusahaan",
    no_directors: "Belum ada direktur.",
    unplaced_title: "Belum ditempatkan ({n})",
    unplaced_hint:
      "Orang aktif tanpa departemen maupun divisi. Pilih tujuan lalu Tempatkan — jenjang ikut menyesuaikan (ke divisi = manager, ke departemen = staf bila belum berjenjang).",
    unplaced_empty: "Semua orang aktif sudah ditempatkan.",
    search_person: "Cari orang (nama/email)…",
    assign_target: "Pilih tujuan…",
    place: "Tempatkan",
    supervisors: "Supervisor",
    staff: "Staf",
    make_supervisor: "Jadikan supervisor",
    make_staff: "Jadikan staf",
    delete_confirm_q: "Hapus {name}? Tidak bisa dibatalkan.",
    delete_yes: "Ya, hapus",
    dept_of: "Departemen {dept} · divisi {div}",
    div_of: "Divisi {div}",
    no_placement: "Belum ditempatkan",
    extra_supervisors: "Supervisor multi-departemen",
    extra_supervisor_hint: "Ditempatkan di sini sekaligus departemen lain (satu penempatan per departemen).",
    extra_badge: "tambahan",
    remove_extra: "Cabut {name} dari {dept}",
  },
};

export type TGodmodeStrings = typeof id;

const en = {
  lang_label: "Language",
  members: {
    title: "Members",
    description: "Create, deactivate, and manage account access. Self sign-up is off — accounts are only born here.",
    new_account: "New account",
    email_placeholder: "email@paradiseperkasa.com",
    name_placeholder: "Full name",
    password_placeholder: "Initial password (min. 8)",
    smtp_note: "Hand the initial password over directly — SMTP is not running, so no email is sent.",
    create_account: "Create account",
    cancel: "Cancel",
    account_created: "Account created",
    account_created_message: "Hand the initial password over directly — no invitation email can be sent yet.",
    create_failed: "Could not create the account.",
    saved: "Saved",
    save_failed: "Could not save the change.",
    failed: "Failed",
    search_placeholder: "Search name or email…",
    all_status: "All statuses",
    active: "Active",
    inactive: "Inactive",
    sort_by: "Sort",
    sort_name: "Name",
    sort_email: "Email",
    sort_last_active: "Last active",
    sort_last_login: "Last sign-in",
    sort_created: "Newest created",
    load_failed: "Could not load the member list.",
    empty: "No matching members.",
    col_edit: "Edit",
    col_name: "Name",
    col_position: "Position",
    col_role: "Role",
    col_session: "Session",
    col_last_active: "Last active",
    col_last_login: "Last sign-in",
    col_last_logout: "Last sign-out",
    col_active: "Active",
    role_admin: "Admin",
    role_member: "Member",
    role_guest: "Guest",
    edit_hint: "Edit account, position, and divisions",
    no_division: "—",
    staff_position: "Member (staff)",
    divisions_count: "{n} divisions",
    position_divisions: "{jabatan} · {n} divisions",
    accounts_count: "{count} accounts · page {page} of {total}",
    prev: "Previous",
    next: "Next",
  },
  editor: {
    name: "Name",
    email: "Email (login identity)",
    workspace: "Workspace",
    workspace_none: "— Not a workspace member —",
    workspace_role: "Workspace access",
    new_password: "New password",
    password_hint: "empty = unchanged",
    password_too_short: "Password must be at least 8 characters.",
    position: "Position",
    position_member: "Member (staff)",
    position_supervisor: "Supervisor",
    position_manager: "Manager",
    position_director: "Director",
    placement: "Placement",
    director_note: "Directors span the whole company, no placement needed.",
    led_division: "Led division",
    not_placed: "— Not placed yet —",
    manager_note: "Managers see every department in this division.",
    department: "Department",
    supervisor_note: "Supervisors see and manage this department's projects.",
    staff_note: "Staff see every project in this department, and only edit their own work.",
    extra_projects: "Extra projects, explicit exceptions ({n})",
    divisions: "Divisions ({n})",
    not_workspace_member: "Not a workspace member — position and divisions cannot be set.",
    joined: "Joined: {list}.",
    left: "Left: {list}.",
    supervised: "Supervised divisions",
    supervised_empty: "Follow formula (empty)",
    supervised_note:
      "Empty = follow formula (directors see all divisions; others their own). Checked = wins over formula.",
    password_note:
      "Changing password or email ends all of their sessions — they must sign in again. Managers/supervisors automatically become Admin in their divisions; members become regular Members. Hand the new password over directly; SMTP is not running, so no email is sent.",
    superadmin_badge: "Super Admin — full project access.",
    revoke: "Revoke",
    make_superadmin: "Make Super Admin",
    make_superadmin_note: "Access to every project including future ones. Type the phrase below exactly to confirm.",
    confirm_phrase: FRASA_KONFIRMASI_EN,
    confirm_instruction: "Type {phrase} to confirm.",
    grant_superadmin: "Grant Super Admin",
    save: "Save",
    cancel: "Cancel",
    superadmin_granted: "Super Admin granted",
    superadmin_granted_message: "{name} now accesses every project.",
    grant_denied: "Denied",
    grant_failed: "Could not grant Super Admin.",
    saved_ok: "Saved",
    saved_message: "{name}: {jabatan}, {n} divisions.",
    saved_message_sessions: "{name}: {jabatan}, {n} divisions, {sesi} sessions ended.",
    save_failed: "Could not save",
    save_failed_message: "Could not save.",
    delete_zone: "Delete this account",
    delete_zone_note: "Deactivate + scrub identity. History stays intact.",
    delete_open: "Delete…",
    delete_confirm: "Type {name} exactly to confirm. Cannot be undone.",
    delete_now: "Delete permanently",
    account_deleted: "Account deleted",
    account_deleted_message: "{name} deactivated and identity scrubbed ({sesi} sessions ended). History stays intact.",
    delete_failed: "Could not delete",
    delete_failed_message: "Could not delete the account.",
  },
  picker: {
    default_placeholder: "Select…",
    select_all: "Select all",
    clear: "Clear",
    empty: "No matching divisions.",
    search_placeholder: "Search…",
    chosen_count: "{n} divisions selected",
  },
  grant: {
    title: "Make {name} a Super Admin?",
    description:
      "They will access every project, including ones created later, without appearing in any member list. Type the phrase below exactly to continue.",
    confirm_phrase: FRASA_KONFIRMASI_EN,
    confirm_instruction: "Type {phrase} to confirm.",
    confirm: "Grant Super Admin",
    cancel: "Cancel",
    granted: "Super Admin granted",
    granted_message: "{name} now accesses every project, including future ones.",
    denied: "Denied",
    failed: "Could not grant Super Admin.",
  },
  session: {
    active: "In use",
    active_hint: "Requests seen in the last few minutes",
    idle: "Signed in",
    idle_hint: "Session is alive, but no recent activity",
    out: "Signed out",
    out_hint: "No live session",
    kick_confirm: "End all sessions for {name}? They will be asked to sign in again.",
    kicked: "Sessions ended",
    kicked_message: "{n} sessions for {name} ended.",
    failed: "Failed",
    kick_failed: "Could not end the sessions.",
    kick_hint: "End sessions, they must sign in again",
    kick_label: "End sessions for {name}",
  },
  supercell: {
    revoke_hint: "Revoke Super Admin status",
    label: "Super Admin",
    grant_hint: "Make Super Admin, needs typed confirmation",
    grant_label: "Make",
  },
  org: {
    title: "Organization structure",
    description:
      "Divisions hold departments, departments hold projects and people. Staff & supervisors see their department's projects, managers see every department in their division, directors see everything.",
    new_division: "New division",
    division_created: "Division {kode} created",
    division_saved: "Division {kode} saved",
    division_deleted: "Division deleted",
    department_saved: "Department saved",
    department_created: "Department {kode} created",
    department_deleted: "Department deleted",
    new_department: "New department",
    code_placeholder: "Code",
    name_placeholder: "Name",
    save_failed: "Failed",
    save_failed_message: "Could not save.",
    no_division: "No divisions yet. While empty, access keeps following project membership as before.",
    departments_count: "· {n} departments",
    division_manager: "Division managers",
    no_manager: "No managers yet. Candidates must be Manager level (set levels on the Members page).",
    member_moved_from: "{name} (moving from {from})",
    person_placed: "{name} placed",
    person_removed: "{name} removed",
    placed_message: "Their project access has been adjusted.",
    members: "Members",
    no_members: "Nobody in this department yet.",
    add_person: "Add someone…",
    add: "Add",
    not_yet_leveled: "not leveled yet, becomes Staff",
    moved_from: ", moving from {from}",
    moved_from_bare: "moved from {from}",
    move_target_other: "another department",
    move_division_other: "another division",
    remove_person: "Remove {name}",
    projects: "Projects ({n})",
    project_picker: "Select project…",
    save_projects: "Save projects",
    projects_moved_note: "Projects already in another department move here; people's access follows.",
    edit_label: "Edit {kind} {name}",
    delete_label: "Delete {kind} {name}",
    kind_division: "division",
    kind_department: "department",
    save: "Save",
    cancel: "Cancel",
    division_of: "Division",
    division_of_dept: "Department {name} belongs to division",
    legacy_title: "Projects without a department yet ({n})",
    legacy_description:
      "This is the old structure (one division = one project). Turn it into a department inside a division to bring it into the new structure; until then it is only visible to its explicit members.",
    legacy_create_first: " Create a division above first.",
    legacy_close: "Close",
    legacy_convert: "Make department…",
    legacy_bring: "Bring this project's members into the department ({a} of {b})",
    legacy_loading: "Loading members…",
    legacy_make: "Make department",
    legacy_kept_note: "Unchecked ones stay project members as exceptions, without placement.",
    legacy_done: "{kode} is now a department",
    legacy_done_message: "{a} people placed{b}.",
    legacy_done_skipped: ", {n} managers/directors skipped",
    legacy_done_all: ".",
    legacy_director_reach: " (spans the whole company)",
    legacy_division_placed: " (placed via division)",
    legacy_unleveled: "not leveled yet, becomes Staff",
    failed: "Failed",
    tree_title: "Organization map",
    tree_hint: "The whole structure at a glance. Click a box to jump to its card below.",
    stat_division: "Divisions",
    stat_department: "Departments",
    stat_project: "Projects",
    stat_manager: "Managers",
    stat_supervisor: "Supervisors",
    stat_staff: "Staff",
    stat_unplaced: "Unplaced",
    stat_unleveled: "Unleveled",
    directors: "Directors — span the whole company",
    no_directors: "No directors yet.",
    unplaced_title: "Not placed yet ({n})",
    unplaced_hint:
      "Active people with neither department nor division. Pick a destination then Place — level follows (to a division = manager, to a department = staff when unleveled).",
    unplaced_empty: "Everyone active has been placed.",
    search_person: "Search people (name/email)…",
    assign_target: "Pick a destination…",
    place: "Place",
    supervisors: "Supervisors",
    staff: "Staff",
    make_supervisor: "Make supervisor",
    make_staff: "Make staff",
    delete_confirm_q: "Delete {name}? Cannot be undone.",
    delete_yes: "Yes, delete",
    dept_of: "{dept} dept · {div} div",
    div_of: "{div} division",
    no_placement: "Not placed",
    extra_supervisors: "Multi-department supervisors",
    extra_supervisor_hint: "Placed here as well as in other departments (one placement each).",
    extra_badge: "extra",
    remove_extra: "Remove {name} from {dept}",
  },
} satisfies TGodmodeStrings;

const STRINGS: Record<TGodmodeLang, TGodmodeStrings> = { id, en };

const fill = (template: string, vars: Record<string, string | number>): string =>
  template.replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? `{${key}}`));

export function getGodmodeLang(): TGodmodeLang {
  if (typeof window === "undefined") return "id";
  return window.localStorage.getItem(LANG_KEY) === "en" ? "en" : "id";
}

/** String God Mode + pilihan bahasa. Default "id" = perilaku lama. */
export function useGodmodeStrings(): {
  s: TGodmodeStrings;
  lang: TGodmodeLang;
  setLang: (lang: TGodmodeLang) => void;
  /** `{nama}` di templat diganti nilai — pengganti ICU yang tidak ada di admin. */
  fill: (template: string, vars: Record<string, string | number>) => string;
} {
  const [lang, setLangState] = useState<TGodmodeLang>(getGodmodeLang);
  const setLang = useCallback((next: TGodmodeLang) => {
    setLangState(next);
    try {
      window.localStorage.setItem(LANG_KEY, next);
    } catch {
      /* penyimpanan privat: preferensi sesi ini saja */
    }
  }, []);
  return { s: STRINGS[lang], lang, setLang, fill };
}

/** Toggle ID/EN kecil untuk header halaman God Mode. */
export function GodmodeLangToggle({
  lang,
  onChange,
}: {
  lang: TGodmodeLang;
  onChange: (lang: TGodmodeLang) => void;
}): JSX.Element {
  return (
    <div className="flex items-center gap-1 rounded-md border border-subtle p-0.5" role="group" aria-label="Language">
      {(["id", "en"] as const).map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => onChange(l)}
          aria-pressed={lang === l}
          className={`rounded px-2 py-0.5 text-11 font-medium uppercase ${
            lang === l ? "bg-layer-3 text-primary" : "text-tertiary hover:text-secondary"
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );
}
