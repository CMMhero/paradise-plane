/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: aturan kepemilikan tugas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
import { useParams } from "next/navigation";
import useSWR, { type SWRConfiguration } from "swr";
import { EUserPermissionsLevel } from "@plane/constants";
import type { TIssue, TIssueServiceType } from "@plane/types";
import { EUserProjectRoles } from "@plane/types";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { StoreContext } from "@/lib/store-context";
// services
import { IssueService } from "@/services/issue";
import {
  ATURAN_TUGAS_BAWAAN,
  PersetujuanService,
  type TAturanTugas,
  type TBisaDitugaskan,
} from "@/services/persetujuan.service";
import { UserService } from "@/services/user.service";

/**
 * Opsi SWR untuk hak akses yang dibaca per kartu/baris papan.
 *
 * Satu papan bisa memasang puluhan langganan ke kunci yang sama, dan kartu
 * di dalam `RenderIfVisible` dipasang ulang saat digulir. Dengan opsi global
 * (revalidate saat mount + saat fokus) itu berarti request baru tiap kali
 * jendela dedupe 2 detik lewat, dan satu request per project tiap tab kembali
 * difokus. Hak akses jarang berubah, jadi cukup diambil sekali lalu dipakai
 * bersama; perubahan jabatan terbaca sesudah muat ulang.
 */
const OPSI_HAK_AKSES: SWRConfiguration = {
  revalidateOnMount: undefined,
  revalidateIfStale: false,
  revalidateOnFocus: false,
};

const userService = new UserService();
const issueService = new IssueService();
const persetujuanService = new PersetujuanService();

/** Batas supervisor di tangga jenjang (10 member · 20 supervisor · 30 manager · 40 direktur). */
export const TINGKAT_SUPERVISOR = 20;

/**
 * Aturan kepemilikan tugas + jenjang saya, sisi tampilan.
 *
 * Bawaan (God Mode KEP-83 tidak diubah, atau server lama tanpa `aturan`):
 *
 *     hapus / arsipkan   sama dengan ubah (pemilik/assignee atau atasan) + Super Admin
 *     ganti Due Date     HANYA pembuatnya atau Super Admin
 *     assignee staf      HANYA dirinya sendiri (+ approval atasan di server)
 *     sisanya            bebas untuk semua anggota
 *
 * Super Admin bisa mengubah lima aturan itu di God Mode; nilainya datang dari
 * `aturan` di balasan `bisa-ditugaskan/` (`TAturanTugas`) dan dibaca di sini.
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

/** Satu kunci + satu fetcher untuk `bisa-ditugaskan/`: dipakai bersama `useTingkatSaya` dan `useBisaDitugaskan`. */
const kunciBisaDitugaskan = (workspaceSlug: string | undefined, projectId: string | null | undefined) =>
  workspaceSlug && projectId ? `BISA_DITUGASKAN:${workspaceSlug}:${projectId}` : null;
const ambilBisaDitugaskan = (workspaceSlug: string, projectId: string): Promise<TBisaDitugaskan | null> =>
  persetujuanService.bisaDitugaskan(workspaceSlug, projectId).catch(() => null);

/**
 * Jenjang saya di sebuah divisi (10/20/30/40 · null = belum dimuat · -1 = belum diisi).
 *
 * Dibaca dari `GET bisa-ditugaskan/` (kunci SWR yang SAMA dengan
 * `useBisaDitugaskan`, jadi satu request per project untuk keduanya). Dulu
 * dari `GET persetujuan-penugasan/` tanpa saringan: seluruh antrean
 * persetujuan project ikut terambil hanya untuk membaca satu angka.
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
  const kunci = kunciBisaDitugaskan(workspaceSlug, projectId);
  const { data, isLoading } = useSWR(
    kunci,
    () => ambilBisaDitugaskan(workspaceSlug as string, projectId as string),
    OPSI_HAK_AKSES
  );
  if (!kunci || isLoading) return null;
  return data?.tingkat_saya ?? BELUM_DIISI;
};

/** Bentuk minimum yang cukup untuk menilai "apakah saya pembuatnya". */
type PembuatTugas = { created_by?: string | null; assignee_ids?: string[] | null; project_id?: string | null };

/**
 * True kalau pembuka layar dipastikan staf (termasuk jenjang belum diisi).
 * null = belum dimuat — pemanggil memilih: kunci sementara (form create) atau
 * terbuka dulu (detail baca, server yang menolak).
 */
export const stafSaja = (tingkat: number | null, ambang: number = TINGKAT_SUPERVISOR): boolean =>
  tingkat != null && tingkat < ambang;

/** Nilai pilihan `ganti_tenggat` / `hapus_tugas`; cermin konstanta `saklar_instance.py`. */
const ATURAN_TENGGAT_PLUS_ADMIN_PROJECT = 1;
const ATURAN_TENGGAT_YANG_BOLEH_UBAH = 2;
const ATURAN_HAPUS_PEMBUAT_SAJA = 1;
const ATURAN_HAPUS_YANG_BOLEH_UBAH = 2;

/** Gabungkan `aturan` server dengan bawaan (kunci yang hilang = perilaku lama). */
const gabungAturan = (aturan: Partial<TAturanTugas> | undefined | null): TAturanTugas => ({
  ...ATURAN_TUGAS_BAWAAN,
  ...aturan,
});

/**
 * Menunggu persetujuan TIDAK lagi mengunci (keputusan user 2026-10-24:
 * persetujuan hanya di gerbang selesai). Tugas bebas dipindah/diubah/dihapus
 * sebelum disetujui; yang diblokir server (`galat_selesai_tugas`) hanyalah
 * MASUK status selesai tanpa persetujuan yang disetujui.
 */

/** Bagian tugas yang berubah karena keputusan persetujuan. */
export type TPerubahanKeputusan = Pick<Partial<TIssue>, "approval_status" | "state_id" | "completed_at">;

/**
 * Samakan tugas di store sesudah keputusan (setujui/tolak/ajukan ulang),
 * supaya badge DAN kolom kartu berubah tanpa refresh (KEP-55: setujui
 * memindahkan tugas ke Done, tolak ke In Progress, dua-duanya di server).
 *
 * `issues.updateIssue` hanya mengubah data tugas. Kartu kanban/list baru
 * pindah kolom kalau `groupedIssueIds` tiap store daftar ikut digeser, jadi
 * semua store daftar diminta `pindahkanGrupTugas`; yang tidak memuat tugas
 * ini mengabaikannya. Tugas yang belum ada di store diabaikan.
 */
export const useSetelStatusPersetujuan = () => {
  const store = useContext(StoreContext);
  return (issueId: string | null | undefined, perubahan: TPerubahanKeputusan) => {
    const akar = store?.issue;
    if (!issueId || !akar) return;
    const sebelum = akar.issues.getIssueById(issueId);
    if (!sebelum) return;
    const salinanSebelum = { ...sebelum };
    akar.issues.updateIssue(issueId, perubahan);
    const sesudah = akar.issues.getIssueById(issueId);
    if (!sesudah || perubahan.state_id === undefined || perubahan.state_id === salinanSebelum.state_id) return;
    const daftar = [
      akar.projectIssues,
      akar.cycleIssues,
      akar.moduleIssues,
      akar.projectViewIssues,
      akar.workspaceIssues,
      akar.profileIssues,
      akar.teamIssues,
      akar.teamViewIssues,
      akar.teamProjectWorkItems,
      akar.archivedIssues,
    ];
    for (const storeDaftar of daftar) storeDaftar?.pindahkanGrupTugas?.(sesudah, salinanSebelum);
  };
};

/**
 * Ambil ulang status tugas dari server, untuk balasan keputusan yang belum
 * membawa `tugas.state_id` (server lama). Gagal diam-diam: keputusannya sudah
 * tersimpan, paling buruk kartu baru pindah sesudah muat ulang.
 */
export const ambilPerubahanKeputusan = async (
  workspaceSlug: string,
  projectId: string,
  issueId: string
): Promise<TPerubahanKeputusan | null> => {
  try {
    const tugas = await issueService.retrieve(workspaceSlug, projectId, issueId);
    return {
      state_id: tugas.state_id,
      completed_at: tugas.completed_at,
      approval_status: tugas.approval_status,
    };
  } catch {
    return null;
  }
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
): {
  mode: string | null;
  userIds: string[];
  memuat: boolean;
  tingkat: number | null;
  gerbangAktif: boolean;
  bawahanIds: string[];
  aturan: TAturanTugas;
} => {
  const kunci = kunciBisaDitugaskan(workspaceSlug, projectId);
  const { data, isLoading } = useSWR(
    kunci,
    () => ambilBisaDitugaskan(workspaceSlug as string, projectId as string),
    OPSI_HAK_AKSES
  );
  if (!kunci || isLoading || !data)
    return {
      mode: null,
      userIds: [],
      memuat: true,
      tingkat: null,
      gerbangAktif: true,
      bawahanIds: [],
      aturan: gabungAturan(data?.aturan),
    };
  const users = (data.users ?? []).map((u) => u.id);
  const ids = users.length > 0 ? users : (data.user_ids ?? []);
  return {
    mode: data.mode,
    userIds: ids,
    memuat: false,
    tingkat: data.tingkat_saya ?? null,
    // Server lama yang belum membalas kunci ini: anggap gerbang menyala (aman).
    gerbangAktif: data.gerbang_aktif ?? true,
    bawahanIds: data.bawahan_ids ?? [],
    aturan: gabungAturan(data.aturan),
  };
};

/**
 * Project yang dipakai untuk membaca `aturan`. Aturannya berlaku se-instance,
 * tapi dibawa balasan `bisa-ditugaskan/` per project: pakai yang diberikan,
 * lalu project di URL, lalu project pertama yang saya ikuti (layar lintas project).
 */
const useKonteksAturan = (
  workspaceSlug?: string,
  projectId?: string | null
): { slug: string | undefined; projectId: string | undefined } => {
  const params = useParams();
  const { joinedProjectIds } = useProject();
  const slugRute = params?.workspaceSlug?.toString();
  const projectRute = params?.projectId?.toString();
  return {
    slug: workspaceSlug ?? slugRute,
    projectId: projectId ?? projectRute ?? joinedProjectIds[0],
  };
};

/** Lima aturan God Mode untuk tampilan; bawaan = perilaku lama selama belum dimuat. */
export const useAturanInstance = (workspaceSlug?: string, projectId?: string | null): TAturanTugas => {
  const konteks = useKonteksAturan(workspaceSlug, projectId);
  return useBisaDitugaskan(konteks.slug, konteks.projectId).aturan;
};

/** Bentuk minimum tugas untuk menilai hak ubah/hapus. */
type TugasKepemilikan = { assignee_ids?: string[] | null; created_by?: string | null; approval_status?: string | null };

/**
 * Bolehkah saya MENGUBAH tugas ini? Cerminan PERSIS `galat_ubah_tugas()` server
 * (KEP-25), dan satu-satunya sumber jawaban "boleh sunting" di tampilan.
 *
 *     Super Admin                       boleh
 *     pembuat (pemberi tugas)/assignee  boleh
 *     gerbang hierarki mati             boleh (katup darurat, server juga melepas)
 *     supervisor+                       boleh kalau SEMUA assignee bawahannya
 *                                       (tanpa assignee: boleh, sama dengan server)
 *     sisanya                           hanya lihat
 *
 * Belum dimuat: pembuat/assignee langsung boleh (tidak berkedip untuk pemilik),
 * orang lain TERTUTUP dulu. Dulu kebalikannya (terbuka dulu, atasan selalu
 * lolos), dan itulah sebab detail tugas orang lain tampak bisa disunting
 * (laporan user 2 Nov 2026).
 */
export const useBolehUbahTugas = (
  workspaceSlug: string | undefined,
  projectId: string | null | undefined,
  issue: TugasKepemilikan | undefined | null
): boolean => usePenilaiUbahTugas(workspaceSlug, projectId)(issue);

/**
 * Apakah saya pembuat atau assignee salah satu sub-work item langsung dari
 * tugas ini? Cerminan `terlibat_di_anak()` server: orang yang sudah mengerjakan
 * sebagian dari sebuah tugas boleh menambah sub-work item di induknya, walau
 * induknya bukan buatan atau tugasnya (hanya itu; judul, deskripsi, dan
 * assignee induk tetap hanya-lihat bagi mereka).
 */
export const useTerlibatDiAnak = (issueId: string | null | undefined, serviceType?: TIssueServiceType): boolean => {
  const { data: currentUser } = useUser();
  const {
    issue: { getIssueById },
    subIssues: { subIssuesByIssueId },
  } = useIssueDetail(serviceType);
  const idSaya = currentUser?.id;
  if (!idSaya || !issueId) return false;
  return (subIssuesByIssueId(issueId) ?? []).some((anakId) => {
    const anak = getIssueById(anakId);
    return !!anak && (anak.created_by === idSaya || (anak.assignee_ids ?? []).includes(idSaya));
  });
};

/**
 * Bentuk fungsi dari `useBolehUbahTugas`, untuk layar yang menilai BANYAK tugas
 * sekaligus lewat callback (blok Gantt). Aturannya satu, ditulis di sini saja.
 * Tugas dari project lain (tampilan lintas project) dinilai tanpa data atasan:
 * pemilik tetap boleh, selainnya terkunci; server tetap penegaknya.
 */
export const usePenilaiUbahTugas = (
  workspaceSlug: string | undefined,
  projectId: string | null | undefined
): ((issue: (TugasKepemilikan & { project_id?: string | null }) | undefined | null) => boolean) => {
  const { data: currentUser } = useUser();
  const { data: statusAdmin } = useSWR(
    currentUser?.id ? "STATUS_SUPER_ADMIN" : null,
    () => userService.currentUserInstanceAdminStatus(),
    OPSI_HAK_AKSES
  );
  const wewenang = useBisaDitugaskan(workspaceSlug, projectId);
  const bawahan = new Set(wewenang.bawahanIds);
  return (issue) => {
    if (!issue) return false;
    if (statusAdmin?.is_instance_admin) return true;
    const idSaya = currentUser?.id;
    if (!idSaya) return false;
    const assignees = issue.assignee_ids ?? [];
    if (issue.created_by === idSaya || assignees.includes(idSaya)) return true;
    if (issue.project_id && projectId && issue.project_id !== projectId) return false;
    if (wewenang.memuat) return false;
    if (!wewenang.gerbangAktif) return true;
    if (wewenang.tingkat == null || wewenang.tingkat < TINGKAT_SUPERVISOR) return false;
    return assignees.every((id) => bawahan.has(id));
  };
};

/**
 * Pilihan dropdown assignee untuk tugas YANG SUDAH ADA (sidebar detail, peek).
 *
 * `memberIds` = daftar dari server (diri + bawahan/rekan/semua) digabung
 * dengan assignee yang sudah ada, supaya yang sudah ditunjuk tetap terlihat.
 * `rapikan` untuk staf: assignee lama tidak bisa dilepas (hanya menambah rekan),
 * jadi pilihan yang membuangnya dikembalikan alih-alih ditolak server.
 */
export const useOpsiAssignee = (
  workspaceSlug: string | undefined,
  projectId: string | null | undefined,
  assigneeIds: string[] | null | undefined
): { memberIds: string[] | undefined; rapikan: (val: string[]) => string[] } => {
  const daftar = useBisaDitugaskan(workspaceSlug, projectId);
  const tingkat = useTingkatSaya(workspaceSlug, projectId);
  const staf = stafSaja(tingkat, daftar.aturan.persetujuan_di_bawah);
  const lama = assigneeIds ?? [];
  return {
    memberIds: daftar.memuat ? undefined : Array.from(new Set([...daftar.userIds, ...lama])),
    rapikan: (val) => (staf ? Array.from(new Set([...lama, ...val])) : val),
  };
};

export const useAturanTugas = (workspaceSlug?: string, projectId?: string | null) => {
  const konteks = useKonteksAturan(workspaceSlug, projectId);
  const { aturan } = useBisaDitugaskan(konteks.slug, konteks.projectId);
  const bolehUbah = usePenilaiUbahTugas(konteks.slug, konteks.projectId);
  const { data: currentUser } = useUser();
  const { allowPermissions } = useUserPermissions();

  // Status Super Admin tidak ikut di payload `me`, jadi diambil dari endpoint
  // khususnya. Kuncinya tetap, jadi SWR menyimpannya untuk seluruh sesi dan
  // ini bukan permintaan per layar.
  const { data: statusAdmin } = useSWR(
    currentUser?.id ? "STATUS_SUPER_ADMIN" : null,
    () => userService.currentUserInstanceAdminStatus(),
    OPSI_HAK_AKSES
  );

  const adalahPembuat = (issue: PembuatTugas | undefined | null) =>
    !!issue && !!currentUser?.id && issue.created_by === currentUser.id;

  // Super Admin instance. Di aplikasi web namanya `is_instance_admin`, dan itu
  // orang yang sama dengan yang dijawab `super_admin_user_ids()` di server.
  const adalahSuperAdmin = !!statusAdmin?.is_instance_admin;

  /**
   * Boleh menggeser Due Date. Cerminan `bisa_ganti_tenggat` server, per aturan God Mode:
   *
   *     0 (bawaan)   pembuat atau Super Admin (admin project TIDAK termasuk)
   *     1            + admin project dari project tugas itu
   *     2            + siapa pun yang boleh MENGUBAH tugas itu
   *
   * Parameternya sengaja hanya butuh `created_by`, bukan `TIssue` utuh:
   * beberapa layar (inbox triage) memegang objek `Partial<TIssue>`.
   */
  const bisaGantiTenggat = (issue: PembuatTugas | undefined | null) => {
    if (adalahPembuat(issue) || adalahSuperAdmin) return true;
    if (!issue) return false;
    if (aturan.ganti_tenggat === ATURAN_TENGGAT_PLUS_ADMIN_PROJECT) {
      const idProject = issue.project_id ?? konteks.projectId;
      return (
        !!idProject &&
        allowPermissions([EUserProjectRoles.ADMIN], EUserPermissionsLevel.PROJECT, konteks.slug, idProject)
      );
    }
    if (aturan.ganti_tenggat === ATURAN_TENGGAT_YANG_BOLEH_UBAH) return bolehUbah(issue);
    return false;
  };

  return {
    /** Lihat `bisaGantiTenggat` di atas — bawaan hanya pembuat atau Super Admin. */
    bisaGantiTenggat,

    /**
     * Boleh menggeser Due Date di PINTU INTAKE (antrean triage).
     *
     * Cerminan `bisa_ganti_tenggat_intake()` server. Keputusan user 2026-10-29:
     * di antrean triage-lah tenggat dijanjikan pertama kali, jadi penanggung
     * jawab intake (admin project) ikut boleh — bukan hanya pembuat. Tanpa ini,
     * tugas yang datang dari orang lain (atau dari divisi lain, `created_by`
     * NULL) tidak akan pernah bisa diberi tenggat oleh siapa pun.
     *
     * Begitu tugasnya diterima ke papan (`sudahDiterima`), pengecualian ini
     * berhenti dan `bisaGantiTenggat` yang berlaku.
     */
    bisaGantiTenggatIntake: (
      issue: PembuatTugas | undefined | null,
      idProject: string | undefined,
      sudahDiterima: boolean
    ) =>
      bisaGantiTenggat(issue) ||
      (!sudahDiterima &&
        allowPermissions([EUserProjectRoles.ADMIN], EUserPermissionsLevel.PROJECT, undefined, idProject)),

    /** Lima aturan God Mode (bawaan = perilaku lama selama belum dimuat). */
    aturan,

    /** Id user saat ini — dipakai dropdown assignee untuk mode "hanya diri sendiri". */
    idSaya: currentUser?.id ?? null,
  };
};

/**
 * Bolehkan menu Arsip/Hapus untuk tugas ini? Tombolnya HILANG kalau tidak
 * boleh (bukan error sesudah klik). Cerminan `bisa_hapus_tugas` server, per
 * aturan `hapus_tugas` di God Mode (Super Admin selalu boleh):
 *
 *     1  pembuat saja
 *     2  siapa pun yang boleh MENGUBAH tugas itu -> `useBolehUbahTugas`
 *     0  (bawaan)
 *     gerbang hierarki aktif   sama dengan hak UBAH (KEP-27) -> `useBolehUbahTugas`
 *     gerbang mati             pembuat, admin project, atau Super Admin
 *
 * `terkunci` selalu False sejak 2026-10-24 (tidak ada lagi kunci menunggu;
 * dipertahankan di bentuk balik supaya 6 pemanggil dropdown tak perlu diubah).
 */
export const useBolehHapus = (
  workspaceSlug: string | undefined,
  projectId: string | null | undefined,
  issue: TugasKepemilikan | undefined | null
): { boleh: boolean; terkunci: boolean } => {
  const { allowPermissions } = useUserPermissions();
  const { data: currentUser } = useUser();
  const { data: statusAdmin } = useSWR(
    currentUser?.id ? "STATUS_SUPER_ADMIN" : null,
    () => userService.currentUserInstanceAdminStatus(),
    OPSI_HAK_AKSES
  );
  const bolehUbah = useBolehUbahTugas(workspaceSlug, projectId, issue);
  const { memuat, gerbangAktif, aturan } = useBisaDitugaskan(workspaceSlug, projectId);
  if (!issue) return { boleh: false, terkunci: false };
  const adalahPembuat = !!currentUser?.id && issue.created_by === currentUser.id;
  if (aturan.hapus_tugas === ATURAN_HAPUS_PEMBUAT_SAJA)
    return { boleh: !!statusAdmin?.is_instance_admin || adalahPembuat, terkunci: false };
  if (aturan.hapus_tugas === ATURAN_HAPUS_YANG_BOLEH_UBAH) return { boleh: bolehUbah, terkunci: false };
  if (memuat || gerbangAktif) return { boleh: bolehUbah, terkunci: false };
  const boleh =
    !!statusAdmin?.is_instance_admin ||
    adalahPembuat ||
    allowPermissions([EUserProjectRoles.ADMIN], EUserPermissionsLevel.PROJECT, workspaceSlug, projectId ?? undefined);
  return { boleh, terkunci: false };
};
