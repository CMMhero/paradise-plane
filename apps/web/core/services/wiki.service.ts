/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: layanan Wiki mandiri (KEP-94)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { getFileMetaDataForUpload } from "@plane/services";
import type { TLogoProps } from "@plane/types";
import { getFileURL } from "@plane/utils";
// services
import { APIService } from "@/services/api.service";
import { FileUploadService } from "@/services/file-upload.service";

/** Bagaimana sebuah materi harus ditampilkan. Diputuskan server, bukan ditebak klien. */
export type TWikiViewerKind = "pdf" | "image" | "video" | "audio" | "text" | "markdown" | "table" | "document" | "none";

/** Satu lembar tabel (CSV punya satu, Excel satu per lembar). Sel sudah berupa teks. */
export type TWikiSheet = { name: string; rows: string[][]; truncated: boolean };

/** Potongan teks berformat di dalam satu blok dokumen Word. */
export type TWikiRun = {
  text: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  strike?: boolean;
  /** Hanya http, https, atau mailto. Server sudah menyaringnya. */
  href?: string;
};

export type TWikiBlock =
  | { type: "heading"; level: number; runs: TWikiRun[] }
  | { type: "paragraph"; runs: TWikiRun[] }
  | { type: "list_item"; level: number; runs: TWikiRun[] }
  | { type: "table"; rows: string[][]; truncated?: boolean };

export type TWikiFolder = {
  id: string;
  parent_id: string | null;
  nama: string;
  keterangan: string;
  /** HTML halaman lama hasil migrasi. Hanya dibaca, dan wajib disanitasi sebelum dirender. */
  isi_lama_html: string;
  logo_props: TLogoProps | null;
  urutan: number;
  /** Folder unit: divisi. Nama mengikuti God Mode. */
  divisi_id: string | null;
  /** Folder unit: departemen, anak dari folder divisinya. */
  departemen_id: string | null;
  /** Folder Umum: semua anggota boleh mengunggah. */
  umum: boolean;
  archived_at: string | null;
  created_by: string | null;
  created_at: string;
  /** Materi aktif yang langsung berada di folder ini. */
  jumlah_materi: number;
  /**
   * Halaman departemen yang boleh dilihat orang ini, langsung di folder ini
   * (hanya folder departemen yang bisa bukan nol). Disaring server dengan aturan
   * daftar halaman, jadi tidak pernah menghitung halaman privat yang tak boleh
   * dilihat. Hanya diisi pohon (`GET wiki/`). KEP-97.
   */
  jumlah_halaman: number;
  /** Project departemen folder ini, kalau ada. Hanya diisi pohon. KEP-97. */
  project_id: string | null;
  /** Semua izin datang dari server. Klien tidak pernah menghitungnya sendiri. */
  can_upload: boolean;
  can_manage: boolean;
};

export type TWikiTree = {
  is_admin: boolean;
  /** Admin, atau manager/supervisor yang mengelola setidaknya satu folder (KEP-95). */
  can_manage_any: boolean;
  user_id: string;
  folders: TWikiFolder[];
};

/** Halaman project departemen yang ikut tampil di Wiki. Hanya dibaca, tidak disalin. */
export type TWikiDepartmentPage = {
  id: string;
  name: string;
  access: "public" | "private";
  logo_props: TLogoProps | null;
  owned_by: string | null;
  updated_at: string;
  project_id: string;
  departemen_id: string;
  departemen_nama: string;
  /** Apakah halaman itu akan benar-benar terbuka di project-nya (aturan Plane). */
  can_open_in_project: boolean;
};

export type TWikiDepartmentPageList = {
  /** null kalau folder ini bukan folder departemen atau departemennya belum punya project. */
  departemen: { id: string; nama: string; project_id: string } | null;
  /** Sudah disaring server: privat hanya untuk yang berhak. */
  pages: TWikiDepartmentPage[];
};

export type TWikiDepartmentPageDetail = TWikiDepartmentPage & {
  /** HTML halaman. Wajib disanitasi sebelum dirender. */
  description_html: string;
};

export type TWikiMaterial = {
  id: string;
  folder_id: string;
  /** Judul tampilan. Nama berkas asli tetap di `name`. */
  judul: string;
  name: string;
  type: string;
  size: number;
  url: string;
  created_by: string | null;
  created_at: string;
  can_manage: boolean;
  can_delete: boolean;
  has_preview: boolean;
};

export type TWikiTrail = { id: string; nama: string };

/** Materi berikut jalur folder dari akar sampai folder tempatnya berada. */
export type TWikiMaterialWithTrail = TWikiMaterial & { jejak: TWikiTrail[] };

/** Potongan isi di sekitar kata yang cocok, dan kata-kata itu persis seperti tertulis di isinya. */
export type TWikiSearchSnippet = { cuplikan: string; sorot: string[] };

export type TWikiSearchResult = {
  materials: (TWikiMaterialWithTrail & TWikiSearchSnippet)[];
  pages: (TWikiDepartmentPage & TWikiSearchSnippet)[];
};

export type TWikiMaterialList = {
  can_upload: boolean;
  materials: TWikiMaterial[];
};

/** Hanya kunci yang dipakai penampil; sisanya urusan server. */
export type TWikiPreview = {
  kind: TWikiViewerKind;
  /** Alamat siap render. null kalau memang tidak bisa ditampilkan. */
  url: string | null;
  download_url: string | null;
  /** Berkas Office yang sudah dikonversi jadi PDF. */
  converted?: boolean;
  /** Kenapa tidak bisa ditampilkan, kalau url null. */
  reason?: string | null;
  /** kind "text" dan "markdown": isi berkas, dibaca server. */
  text?: string;
  /** kind "table": lembar-lembar yang dibaca server. */
  sheets?: TWikiSheet[];
  /** kind "document": blok hasil baca docx. `fallback` = konversi PDF tidak tersedia. */
  blocks?: TWikiBlock[];
  fallback?: boolean;
  /** Isi dipotong oleh batas server (teks, baris, blok). */
  truncated?: boolean;
  sheets_truncated?: boolean;
};

export type TWikiTrash = {
  folders: (TWikiFolder & { deleted_at: string })[];
  materials: (TWikiMaterial & { deleted_at: string })[];
};

export type TWikiFolderCreate = {
  nama: string;
  parent_id?: string;
  keterangan?: string;
  logo_props?: TLogoProps;
  umum?: boolean;
};

export type TWikiFolderUpdate = Partial<Pick<TWikiFolder, "nama" | "keterangan" | "logo_props" | "umum" | "urutan">>;

type TCreateMaterialResponse = {
  upload_data: { url: string; fields: Record<string, string> };
  material: TWikiMaterial;
};

const fileUploadService = new FileUploadService();

/**
 * Deteksi tipe di `getFileMetaDataForUpload` hanya membaca tanda tangan biner,
 * jadi berkas teks (.txt, .md, .csv) kembali bertipe kosong dan ditolak server.
 * Untuk itu ekstensi dipakai sebagai cadangan. Server menebak dengan tabel yang
 * sama, ini hanya supaya tipe yang dikirim ikut benar.
 */
const TIPE_DARI_EKSTENSI: Record<string, string> = {
  md: "text/markdown",
  markdown: "text/markdown",
  csv: "text/csv",
  txt: "text/plain",
  log: "text/plain",
  json: "application/json",
  xml: "text/xml",
  sql: "application/x-sql",
};

const tipeBerkas = (nama: string, terdeteksi: string): string => {
  if (terdeteksi && terdeteksi !== "application/octet-stream") return terdeteksi;
  const ekstensi = nama.includes(".") ? nama.slice(nama.lastIndexOf(".") + 1).toLowerCase() : "";
  return TIPE_DARI_EKSTENSI[ekstensi] ?? terdeteksi ?? "application/octet-stream";
};

/**
 * Alamat berkas dari server berbentuk `/api/...` (relatif). Di produksi, Caddy
 * memetakan `/api` ke API sehingga itu cukup. Di dev, web (:4000) dan API
 * (:8000) beda asal, dan alamat relatif jatuh ke server web yang menjawab 404.
 * `getFileURL` menempelkan `API_BASE_URL` (kosong di produksi, jadi tak berubah).
 */
function mutlak(alamat: string | null): string | null {
  return alamat ? (getFileURL(alamat) ?? alamat) : alamat;
}

function alamatMutlakMateri<T extends TWikiMaterial>(materi: T): T {
  return { ...materi, url: mutlak(materi.url) ?? materi.url };
}

/**
 * Satu layanan untuk seluruh API Wiki tingkat workspace.
 *
 * Wiki bukan project lagi, jadi semua rute berada di `/api/workspaces/<slug>/wiki/`
 * dan tidak ada lagi id project yang perlu dicari.
 */
export class WikiService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string) {
    return `/api/workspaces/${workspaceSlug}/wiki`;
  }

  private async panggil<T>(call: () => Promise<{ data: T }>): Promise<T> {
    return call()
      .then((response) => response?.data)
      .catch((error) => {
        // Selalu lempar objek. Galat tanpa isi (502 dari proxy, jaringan putus,
        // respons HTML) dulu melempar `undefined`, dan SWR menyimpannya sebagai
        // "tidak ada galat", jadi halaman macet di kerangka pemuat selamanya.
        const isi = error?.response?.data;
        throw isi && typeof isi === "object" ? isi : { error: typeof isi === "string" ? undefined : error?.message };
      });
  }

  fetchTree(workspaceSlug: string): Promise<TWikiTree> {
    return this.panggil(() => this.get(`${this.base(workspaceSlug)}/`));
  }

  createFolder(workspaceSlug: string, data: TWikiFolderCreate): Promise<TWikiFolder> {
    return this.panggil(() => this.post(`${this.base(workspaceSlug)}/folders/`, data));
  }

  updateFolder(workspaceSlug: string, folderId: string, data: TWikiFolderUpdate): Promise<TWikiFolder> {
    return this.panggil(() => this.patch(`${this.base(workspaceSlug)}/folders/${folderId}/`, data));
  }

  archiveFolder(workspaceSlug: string, folderId: string): Promise<void> {
    return this.panggil(() => this.post(`${this.base(workspaceSlug)}/folders/${folderId}/archive/`));
  }

  unarchiveFolder(workspaceSlug: string, folderId: string): Promise<void> {
    return this.panggil(() => this.delete(`${this.base(workspaceSlug)}/folders/${folderId}/archive/`));
  }

  deleteFolder(workspaceSlug: string, folderId: string): Promise<void> {
    return this.panggil(() => this.delete(`${this.base(workspaceSlug)}/folders/${folderId}/`));
  }

  fetchMaterials(workspaceSlug: string, folderId: string): Promise<TWikiMaterialList> {
    return this.panggil<TWikiMaterialList>(() =>
      this.get(`${this.base(workspaceSlug)}/folders/${folderId}/materials/`)
    ).then((daftar) => ({ ...daftar, materials: daftar.materials.map(alamatMutlakMateri) }));
  }

  /**
   * Tiga langkah: minta URL presigned, unggah ke penyimpanan objek, tandai selesai.
   * Berkas baru tampil di daftar hanya sesudah langkah ketiga.
   */
  async upload(
    workspaceSlug: string,
    folderId: string,
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<TWikiMaterial> {
    const terdeteksi = await getFileMetaDataForUpload(file);
    const meta = { ...terdeteksi, type: tipeBerkas(file.name, terdeteksi.type) };
    const { upload_data, material } = await this.panggil<TCreateMaterialResponse>(() =>
      this.post(`${this.base(workspaceSlug)}/folders/${folderId}/materials/`, meta)
    );
    const payload = new FormData();
    Object.entries(upload_data.fields).forEach(([key, value]) => payload.append(key, value));
    payload.append("file", file);
    await fileUploadService.uploadFile(upload_data.url, payload, (event) => {
      if (!onProgress || !event.total) return;
      onProgress(Math.round((event.loaded * 100) / event.total));
    });
    await this.panggil(() => this.post(`${this.base(workspaceSlug)}/materials/${material.id}/uploaded/`));
    return material;
  }

  fetchMaterial(workspaceSlug: string, materialId: string): Promise<TWikiMaterialWithTrail> {
    return this.panggil<TWikiMaterialWithTrail>(() =>
      this.get(`${this.base(workspaceSlug)}/materials/${materialId}/`)
    ).then(alamatMutlakMateri);
  }

  renameMaterial(workspaceSlug: string, materialId: string, judul: string): Promise<TWikiMaterial> {
    return this.panggil(() => this.patch(`${this.base(workspaceSlug)}/materials/${materialId}/`, { judul }));
  }

  /** Pindah ke folder lain. Server menilai hak ubah materi DAN hak unggah di folder tujuan. */
  moveMaterial(workspaceSlug: string, materialId: string, folderId: string): Promise<TWikiMaterial> {
    return this.panggil<TWikiMaterial>(() =>
      this.patch(`${this.base(workspaceSlug)}/materials/${materialId}/`, { folder_id: folderId })
    ).then(alamatMutlakMateri);
  }

  deleteMaterial(workspaceSlug: string, materialId: string): Promise<void> {
    return this.panggil(() => this.delete(`${this.base(workspaceSlug)}/materials/${materialId}/`));
  }

  /**
   * Untuk Word, Excel, dan PowerPoint panggilan PERTAMA ikut menunggu konversi
   * ke PDF di server, jadi ia bisa memakan beberapa detik.
   */
  fetchPreview(workspaceSlug: string, materialId: string): Promise<TWikiPreview> {
    return this.panggil<TWikiPreview>(() =>
      this.get(`${this.base(workspaceSlug)}/materials/${materialId}/preview/`)
    ).then((pratinjau) => ({
      ...pratinjau,
      url: mutlak(pratinjau.url),
      download_url: mutlak(pratinjau.download_url),
    }));
  }

  search(workspaceSlug: string, q: string): Promise<TWikiSearchResult> {
    return this.panggil<TWikiSearchResult>(() =>
      this.get(`${this.base(workspaceSlug)}/search/`, { params: { q } })
    ).then((hasil) => ({ ...hasil, materials: hasil.materials.map(alamatMutlakMateri) }));
  }

  fetchDepartmentPages(workspaceSlug: string, folderId: string): Promise<TWikiDepartmentPageList> {
    return this.panggil(() => this.get(`${this.base(workspaceSlug)}/folders/${folderId}/pages/`));
  }

  fetchDepartmentPage(workspaceSlug: string, pageId: string): Promise<TWikiDepartmentPageDetail> {
    return this.panggil(() => this.get(`${this.base(workspaceSlug)}/pages/${pageId}/`));
  }

  /** `folderId`: hanya folder itu dan semua di bawahnya (tab Materials departemen, KEP-97). */
  fetchTrash(workspaceSlug: string, folderId?: string): Promise<TWikiTrash> {
    return this.panggil(() =>
      this.get(`${this.base(workspaceSlug)}/trash/`, folderId ? { params: { folder: folderId } } : undefined)
    );
  }

  restoreFolder(workspaceSlug: string, folderId: string): Promise<TWikiFolder> {
    return this.panggil(() => this.post(`${this.base(workspaceSlug)}/trash/folders/${folderId}/restore/`));
  }

  restoreMaterial(workspaceSlug: string, materialId: string): Promise<TWikiMaterial> {
    return this.panggil(() => this.post(`${this.base(workspaceSlug)}/trash/materials/${materialId}/restore/`));
  }
}
