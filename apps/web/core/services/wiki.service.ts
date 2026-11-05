/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: layanan Wiki mandiri (KEP-94)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { getFileMetaDataForUpload } from "@plane/services";
import type { TLogoProps } from "@plane/types";
// services
import { APIService } from "@/services/api.service";
import { FileUploadService } from "@/services/file-upload.service";

/** Bagaimana sebuah materi harus ditampilkan. Diputuskan server, bukan ditebak klien. */
export type TWikiViewerKind = "pdf" | "image" | "video" | "audio" | "text" | "none";

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
  /** Semua izin datang dari server. Klien tidak pernah menghitungnya sendiri. */
  can_upload: boolean;
  can_manage: boolean;
};

export type TWikiTree = {
  is_admin: boolean;
  user_id: string;
  folders: TWikiFolder[];
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
        throw error?.response?.data;
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
    return this.panggil(() => this.get(`${this.base(workspaceSlug)}/folders/${folderId}/materials/`));
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
    const meta = await getFileMetaDataForUpload(file);
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
    return this.panggil(() => this.get(`${this.base(workspaceSlug)}/materials/${materialId}/`));
  }

  renameMaterial(workspaceSlug: string, materialId: string, judul: string): Promise<TWikiMaterial> {
    return this.panggil(() => this.patch(`${this.base(workspaceSlug)}/materials/${materialId}/`, { judul }));
  }

  deleteMaterial(workspaceSlug: string, materialId: string): Promise<void> {
    return this.panggil(() => this.delete(`${this.base(workspaceSlug)}/materials/${materialId}/`));
  }

  /**
   * Untuk Word, Excel, dan PowerPoint panggilan PERTAMA ikut menunggu konversi
   * ke PDF di server, jadi ia bisa memakan beberapa detik.
   */
  fetchPreview(workspaceSlug: string, materialId: string): Promise<TWikiPreview> {
    return this.panggil(() => this.get(`${this.base(workspaceSlug)}/materials/${materialId}/preview/`));
  }

  search(workspaceSlug: string, q: string): Promise<TWikiMaterialWithTrail[]> {
    return this.panggil(() => this.get(`${this.base(workspaceSlug)}/search/`, { params: { q } }));
  }

  fetchTrash(workspaceSlug: string): Promise<TWikiTrash> {
    return this.panggil(() => this.get(`${this.base(workspaceSlug)}/trash/`));
  }

  restoreFolder(workspaceSlug: string, folderId: string): Promise<TWikiFolder> {
    return this.panggil(() => this.post(`${this.base(workspaceSlug)}/trash/folders/${folderId}/restore/`));
  }

  restoreMaterial(workspaceSlug: string, materialId: string): Promise<TWikiMaterial> {
    return this.panggil(() => this.post(`${this.base(workspaceSlug)}/trash/materials/${materialId}/restore/`));
  }
}
