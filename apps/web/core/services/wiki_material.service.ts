/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Materi Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";
import { FileService } from "@/services/file.service";

/** Bagaimana sebuah materi harus ditampilkan. Diputuskan server, bukan ditebak klien. */
export type TJenisMateri = "pdf" | "image" | "video" | "audio" | "text" | "none";

export type TMateriWiki = {
  id: string;
  /** Topik tempat materi ini berada. Jalan pulang penampilnya. */
  topic_id: string | null;
  /** Judul yang bisa disunting, terpisah dari nama berkasnya. */
  title: string;
  name: string;
  type: string;
  size: number;
  kind: TJenisMateri | "konversi";
  created_at: string;
  uploaded_by: { id: string; display_name: string; avatar_url: string | null } | null;
  /** Boleh mengganti judul atau menghapus. Dihitung server. */
  can_manage: boolean;
};

export type TDaftarMateri = {
  materials: TMateriWiki[];
  can_upload: boolean;
};

export type TPratinjauMateri = TMateriWiki & {
  kind: TJenisMateri;
  /** Alamat siap render. null kalau memang tidak bisa ditampilkan. */
  url: string | null;
  download_url: string;
  /** Berkas Office yang sudah dikonversi jadi PDF. */
  converted?: boolean;
  /** Kenapa tidak bisa ditampilkan, kalau url null. */
  reason?: string | null;
};

const fileService = new FileService();

export class WikiMaterialService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchByTopic(workspaceSlug: string, projectId: string, pageId: string): Promise<TDaftarMateri> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/wiki/topics/${pageId}/materials/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Satu langkah: pilih berkas, selesai.
   *
   * Seluruh tarian tiga langkahnya (minta URL presigned, unggah ke MinIO,
   * tandai selesai) sudah dikerjakan `uploadProjectAsset`, jadi di sini tidak
   * ada satu pun kode unggah baru. Yang membedakan materi dari lampiran biasa
   * cuma `entity_type`.
   */
  async upload(
    workspaceSlug: string,
    projectId: string,
    pageId: string,
    file: File,
    onProgress?: (persen: number) => void
  ): Promise<void> {
    await fileService.uploadProjectAsset(
      workspaceSlug,
      projectId,
      { entity_identifier: pageId, entity_type: "WIKI_MATERIAL" as never },
      file,
      (event) => {
        if (!onProgress || !event.total) return;
        onProgress(Math.round((event.loaded * 100) / event.total));
      }
    );
  }

  /** Cari materi di seluruh Wiki. Judul dan nama berkas, bukan isi dokumennya. */
  async search(
    workspaceSlug: string,
    projectId: string,
    q: string
  ): Promise<{ materials: (TMateriWiki & { topic_id: string | null; breadcrumb: string[] })[] }> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/wiki/search/`, { params: { q } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async rename(workspaceSlug: string, projectId: string, assetId: string, title: string): Promise<TMateriWiki> {
    return this.patch(`/api/workspaces/${workspaceSlug}/projects/${projectId}/wiki/materials/${assetId}/`, { title })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Alamat siap render untuk satu materi.
   *
   * Untuk Word, Excel, dan PowerPoint panggilan PERTAMA ikut menunggu konversi
   * ke PDF di server, jadi ia bisa memakan beberapa detik. Panggilan
   * berikutnya memakai hasil yang sudah disimpan.
   */
  async preview(workspaceSlug: string, projectId: string, assetId: string): Promise<TPratinjauMateri> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/wiki/materials/${assetId}/preview/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, projectId: string, assetId: string): Promise<void> {
    return this.delete(`/api/assets/v2/workspaces/${workspaceSlug}/projects/${projectId}/${assetId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

/**
 * Ganti nama dan ikon folder Wiki.
 *
 * Sengaja BUKAN PATCH halaman biasa. Judul halaman yang sebenarnya hidup di
 * binary Yjs dan server Live mendorongnya balik, jadi rename lewat jalur biasa
 * akan tampak berhasil lalu terbalik sendiri. Endpoint ini sekalian
 * mengosongkan binary-nya supaya nama barunya bertahan.
 */
export class WikiFolderService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private async ubah(workspaceSlug: string, projectId: string, pageId: string, data: Record<string, unknown>) {
    return this.patch(`/api/workspaces/${workspaceSlug}/projects/${projectId}/wiki/folders/${pageId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async rename(workspaceSlug: string, projectId: string, pageId: string, name: string) {
    return this.ubah(workspaceSlug, projectId, pageId, { name });
  }

  async setLogo(workspaceSlug: string, projectId: string, pageId: string, logo_props: unknown) {
    return this.ubah(workspaceSlug, projectId, pageId, { logo_props });
  }
}
