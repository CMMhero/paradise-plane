/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: cek izin edit halaman
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { logger } from "@plane/logger";
import { AppError } from "@/lib/errors";
import { APIService } from "@/services/api.service";

export class PagePermissionService extends APIService {
  /**
   * Tanya backend: bolehkah user (pemilik cookie ini) mengedit halaman tsb?
   *
   * GAGAL = TIDAK BOLEH (fail closed). Ini gerbang izin: kalau jawabannya tidak
   * bisa dipastikan, koneksi dibuat read-only. Fail open akan membuat gangguan
   * API sekejap berubah jadi jalan pintas menembus ACL folder.
   */
  async canEdit({
    cookie,
    workspaceSlug,
    projectId,
    pageId,
  }: {
    cookie: string;
    workspaceSlug: string;
    projectId: string;
    pageId: string;
  }): Promise<boolean> {
    try {
      const response = await this.get(
        `/api/workspaces/${workspaceSlug}/projects/${projectId}/pages/${pageId}/can-edit/`,
        { headers: { Cookie: cookie } }
      );
      return response?.data?.can_edit === true;
    } catch (error) {
      const appError = new AppError(error, {
        context: { operation: "canEdit", workspaceSlug, projectId, pageId },
      });
      logger.error("Cek izin edit halaman gagal, koneksi dijadikan read-only", appError);
      return false;
    }
  }
}
