/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: aturan kepemilikan tugas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
import useSWR from "swr";
import { EUserPermissionsLevel } from "@plane/constants";
import type { TIssue } from "@plane/types";
import { EUserProjectRoles } from "@plane/types";
// hooks
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { StoreContext } from "@/lib/store-context";
// services
import { PersetujuanService } from "@/services/persetujuan.service";
import { UserService } from "@/services/user.service";

const userService = new UserService();
const persetujuanService = new PersetujuanService();

/** Batas supervisor di tangga jenjang (10 member · 20 supervisor · 30 manager · 40 direktur). */
export const TINGKAT_SUPERVISOR = 20;

/**
 * Aturan kepemilikan tugas + jenjang saya, sisi tampilan.
 *
 *     hapus / arsipkan   sama dengan ubah (pemilik/assignee atau atasan) + Super Admin
 *     ganti Due Date     HANYA pembuatnya atau Super Admin
 *     assignee staf      HANYA dirinya sendiri (+ approval atasan di server)
 *     sisanya            bebas untuk semua anggota
 *
 * Penegak yang sebenarnya ada di server (`plane/utils/task_access.py` +
 * gerbang hierarki `plane/utils/hierarki.py`), dan ini TIDAK menggantikannya.
 * Gunanya cuma satu: jangan menampilkan kontrol yang pasti ditolak. Tombol
 * yang terlihat aktif lalu gagal adalah cara paling cepat membuat orang
 * berhenti percaya pada aplikasinya.
 *
 * Karena itu, kalau syarat di sini dan di server sampai berbeda, yang harus
 * diubah adalah YANG DI SINI. Server tetap pemegang keputusan.
 */

/**
 * Jenjang saya di sebuah divisi (10/20/30/40 · null = belum dimuat · -1 = belum diisi).
 *
 * Dibaca dari `GET persetujuan-penugasan/` yang memang sudah membalas
 * `tingkat_saya` — tanpa endpoint baru, di-cache per project oleh SWR.
 * Hook sendiri (bukan method di dalam hook lain) supaya `useSWR`-nya sah.
 *
 * Tiga keadaan sengaja dibedakan: null (belum tahu — tampilkan loading/tertutup
 * sementara), -1 (sudah tahu: jenjang belum diisi — perlakukan sebagai staf),
 * dan angka (jenjang nyata). Menyamakan "belum dimuat" dengan "staf" membuat
 * dropdown berkedip tiap buka layar; menyamakannya dengan "bebas" membuka
 * celah saat request lambat.
 */
export const BELUM_DIMUAT = null;
export const BELUM_DIISI = -1;
export const useTingkatSaya = (workspaceSlug: string | undefined, projectId: string | null | undefined) => {
  const kunci = workspaceSlug && projectId ? `TINGKAT_SAYA:${workspaceSlug}:${projectId}` : null;
  const { data, isLoading } = useSWR(kunci, () =>
    persetujuanService.daftar(workspaceSlug as string, projectId as string).then((res) => res?.tingkat_saya ?? -1)
  );
  if (!kunci || isLoading) return null;
  return data ?? -1;
};

/**
 * True kalau pembuka layar dipastikan staf (termasuk jenjang belum diisi).
 * null = belum dimuat — pemanggil memilih: kunci sementara (form create) atau
 * terbuka dulu (detail baca, server yang menolak).
 */
export const stafSaja = (tingkat: number | null): boolean => tingkat != null && tingkat < TINGKAT_SUPERVISOR;

/**
 * Menunggu persetujuan TIDAK lagi mengunci (keputusan user 2026-10-24:
 * persetujuan hanya di gerbang selesai). Tugas bebas dipindah/diubah/dihapus
 * sebelum disetujui; yang diblokir server (`galat_selesai_tugas`) hanyalah
 * MASUK status selesai tanpa persetujuan yang disetujui.
 */

/**
 * Samakan `approval_status` tugas di store sesudah keputusan (setujui/tolak/
 * ajukan ulang), supaya kunci & badge di papan berubah tanpa refresh.
 * Tugas yang belum ada di store diabaikan (`updateIssue` sudah no-op).
 */
export const useSetelStatusPersetujuan = () => {
  const store = useContext(StoreContext);
  return (issueId: string | null | undefined, status: TIssue["approval_status"]) => {
    if (issueId) store?.issue.issues.updateIssue(issueId, { approval_status: status });
  };
};

/**
 * Bolehkah saya MENGUBAH tugas ini? Cerminan `galat_ubah_tugas()` server.
 *
 * - Staf: hanya kalau saya assignee-nya (atau pembuatnya).
 * - Atasan: selalu boleh di sini (server yang menilai bawahan-vs-bukan; tampilan
 *   tidak punya peta tingkat semua orang tanpa request tambahan).
 * - null (belum dimuat): TERBUKA dulu — server 403 kalau dipaksa. Mengunci saat
 *   loading membuat seluruh formulir mati sesaat tiap buka layar.
 */
export const bolehUbahTugas = (
  issue: { assignee_ids?: string[] | null; created_by?: string; approval_status?: string | null } | undefined | null,
  idSaya: string | null,
  tingkatSaya: number | null
): boolean => {
  if (!issue) return false;
  if (tingkatSaya == null) return true;
  if (tingkatSaya >= TINGKAT_SUPERVISOR) return true;
  if (!idSaya) return false;
  return (issue.assignee_ids ?? []).includes(idSaya) || issue.created_by === idSaya;
};
/**
 * Daftar user yang boleh masuk dropdown assignee saya di sebuah project.
 * Dibaca dari `GET bisa-ditugaskan/` — staf → [diri sendiri], atasan → diri +
 * bawahan, direktur → seluruh anggota. null = belum dimuat (dropdown tertutup
 * sementara, bukan terbuka lebar).
 */
export const useBisaDitugaskan = (
  workspaceSlug: string | undefined,
  projectId: string | null | undefined
): { mode: string | null; userIds: string[]; memuat: boolean } => {
  const kunci = workspaceSlug && projectId ? `BISA_DITUGASKAN:${workspaceSlug}:${projectId}` : null;
  const { data, isLoading } = useSWR(kunci, () =>
    persetujuanService
      .bisaDitugaskan(workspaceSlug as string, projectId as string)
      .then((res) => res)
      .catch(() => null)
  );
  if (!kunci || isLoading || !data) return { mode: null, userIds: [], memuat: true };
  const users = (data.users ?? []).map((u) => u.id);
  const ids = users.length > 0 ? users : (data.user_ids ?? []);
  return { mode: data.mode, userIds: ids, memuat: false };
};

export const useAturanTugas = () => {
  const { data: currentUser } = useUser();
  const { allowPermissions } = useUserPermissions();

  // Status Super Admin tidak ikut di payload `me`, jadi diambil dari endpoint
  // khususnya. Kuncinya tetap, jadi SWR menyimpannya untuk seluruh sesi dan
  // ini bukan permintaan per layar.
  const { data: statusAdmin } = useSWR(currentUser?.id ? "STATUS_SUPER_ADMIN" : null, () =>
    userService.currentUserInstanceAdminStatus()
  );

  const adalahPembuat =
    (issue: TIssue | undefined | null) => !!issue && !!currentUser?.id && issue.created_by === currentUser.id;

  // Super Admin instance. Di aplikasi web namanya `is_instance_admin`, dan itu
  // orang yang sama dengan yang dijawab `super_admin_user_ids()` di server.
  const adalahSuperAdmin = !!statusAdmin?.is_instance_admin;

  return {
    /** Boleh menggeser Due Date. Sengaja tidak termasuk admin project. */
    bisaGantiTenggat: (issue: TIssue | undefined | null) => adalahPembuat(issue) || adalahSuperAdmin,

    /**
     * Boleh menghapus atau mengarsipkan. Jenjang sudah dimuat: sama dengan
     * `bolehUbahTugas` (pemilik/assignee atau atasan), cermin `bisa_hapus_tugas`
     * server. Belum dimuat: aturan lama (pembuat/admin project).
     */
    bisaHapusTugas: (issue: TIssue | undefined | null, projectId?: string, tingkatSaya: number | null = null) => {
      if (adalahSuperAdmin) return true;
      if (tingkatSaya != null) return bolehUbahTugas(issue, currentUser?.id ?? null, tingkatSaya);
      return (
        adalahPembuat(issue) ||
        allowPermissions([EUserProjectRoles.ADMIN], EUserPermissionsLevel.PROJECT, undefined, projectId)
      );
    },

    /** Id user saat ini — dipakai dropdown assignee untuk mode "hanya diri sendiri". */
    idSaya: currentUser?.id ?? null,
  };
};

/**
 * Bolehkan menu Arsip/Hapus untuk tugas ini? Aturan TEGAS khusus tindakan
 * destruktif: tombolnya HILANG kalau tidak boleh (bukan error sesudah klik).
 *
 * - Wewenang belum dimuat -> sembunyi (fail-closed; kebalikan dari
 *   bolehUbahTugas yang terbuka dulu supaya formulir tidak berkedip).
 * - Super Admin -> selalu boleh.
 * - Sisanya: pembuatnya, atau ada assignee yang masuk daftar kuasa saya
 *   (diri sendiri + bawahan; direktur melihat semua anggota).
 * - Tanpa assignee: hanya pembuat, atau yang kuasanya lebih dari diri
 *   sendiri (mencerminkan "himpunan kosong subset dari apa pun" di server).
 *
 * Ini cerminan `bisa_hapus_tugas` server untuk KASUS HAPUS/ARSIP. Sengaja
 * terpisah dari `bolehUbahTugas` (aturan ubah lebih longgar untuk atasan).
 *
 * `terkunci` selalu False sejak 2026-10-24 (tidak ada lagi kunci menunggu;
 * dipertahankan di bentuk balik supaya 6 pemanggil dropdown tak perlu diubah).
 */
export const useBolehHapus = (
  workspaceSlug: string | undefined,
  projectId: string | null | undefined,
  issue: { assignee_ids?: string[] | null; created_by?: string; approval_status?: string | null } | undefined | null
): { boleh: boolean; terkunci: boolean } => {
  const { data: currentUser } = useUser();
  const { data: statusAdmin } = useSWR(currentUser?.id ? "STATUS_SUPER_ADMIN" : null, () =>
    userService.currentUserInstanceAdminStatus()
  );
  const { userIds: kuasaIds, memuat } = useBisaDitugaskan(workspaceSlug, projectId);
  const adalahSuperAdmin = !!statusAdmin?.is_instance_admin;
  if (memuat && !adalahSuperAdmin) return { boleh: false, terkunci: false };
  if (adalahSuperAdmin) return { boleh: true, terkunci: false };
  const idSaya = currentUser?.id;
  if (!issue || !idSaya) return { boleh: false, terkunci: false };
  if (issue.created_by === idSaya) return { boleh: true, terkunci: false };
  const assignees = issue.assignee_ids ?? [];
  if (assignees.length === 0) return { boleh: kuasaIds.length > 1, terkunci: false };
  const kuasa = new Set(kuasaIds);
  return { boleh: assignees.some((id) => kuasa.has(id)), terkunci: false };
};
