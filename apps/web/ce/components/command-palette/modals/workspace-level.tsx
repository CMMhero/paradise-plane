/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TWorkspaceLevelModalsProps = {
  workspaceSlug: string;
};

// Paradise: departemen hanya dibuat di God Mode, jadi tidak ada lagi modal buat
// project di level workspace. Komponen dipertahankan sebagai titik pasang CE.
export function WorkspaceLevelModals(_props: TWorkspaceLevelModalsProps) {
  return null;
}
