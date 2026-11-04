/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: siapa yang boleh membuat project
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import useSWR from "swr";
import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

class BolehBuatProjectService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async ambil(workspaceSlug: string): Promise<{ boleh: boolean }> {
    return this.get(`/api/workspaces/${workspaceSlug}/boleh-buat-project/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}

const layanan = new BolehBuatProjectService();

/**
 * Bolehkah saya membuat project di workspace ini?
 *
 * Aturannya di server (`plane/utils/izin_buat_project.py`): Super Admin, admin
 * workspace, dan Supervisor ke atas boleh; staf / member biasa tidak. Hook ini
 * hanya menyembunyikan tombol yang pasti ditolak. Selama belum dimuat atau
 * gagal dimuat jawabannya `false`: tombol yang muncul lalu hilang lebih buruk
 * daripada tombol yang muncul sesaat kemudian.
 */
export const useBolehBuatProject = (workspaceSlugArg?: string): boolean => {
  const params = useParams();
  const workspaceSlug = workspaceSlugArg ?? (params?.workspaceSlug as string | undefined);
  const { data } = useSWR(
    workspaceSlug ? `BOLEH_BUAT_PROJECT:${workspaceSlug}` : null,
    () => layanan.ambil(workspaceSlug as string).catch(() => ({ boleh: false })),
    { revalidateOnFocus: false, revalidateIfStale: false }
  );
  return data?.boleh ?? false;
};
