/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kerangka daftar obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";

/** Tinggi baris disamakan dengan daftar asli (kanal ~29px, orang 60px). */
const BARIS_KANAL = 3;
const BARIS_ORANG = 8;

/**
 * Pengganti daftar kanal + orang selama `percakapan` atau `daftarKanal` belum
 * tiba. Sebelumnya daftar digambar dari data yang setengah jadi: kanal kosong
 * ("belum ikut kanal apa pun") lalu tumbuh ~100px, dan orang diurutkan per nama
 * lalu diurutkan ulang begitu percakapan tiba. Dua-duanya menggeser baris yang
 * sudah tampil (layout shift 0,3 di HP/tablet). Kerangka diganti utuh sekali.
 */
export function KerangkaDaftar() {
  const { t } = useTranslation();
  return (
    <div aria-busy="true">
      <span className="sr-only">{t("common.loading")}</span>
      <div className="border-b border-subtle pb-1">
        <div className="flex items-center px-3 pt-2.5 pb-1">
          <span className="h-4 w-16 animate-pulse rounded-sm bg-layer-1" />
        </div>
        {Array.from({ length: BARIS_KANAL }, (_, i) => (
          <div key={i} className="flex items-center gap-2 px-3 py-1.5">
            <span className="size-3.5 shrink-0 animate-pulse rounded-sm bg-layer-1" />
            <span className="h-4 w-32 animate-pulse rounded-sm bg-layer-1" />
          </div>
        ))}
      </div>
      {Array.from({ length: BARIS_ORANG }, (_, i) => (
        <div key={i} className="flex items-center gap-2.5 px-3 py-2.5">
          <span className="size-8 shrink-0 animate-pulse rounded-full bg-layer-1" />
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <span className="h-3.5 w-36 animate-pulse rounded-sm bg-layer-1" />
            <span className="h-3 w-48 max-w-full animate-pulse rounded-sm bg-layer-1" />
          </div>
        </div>
      ))}
    </div>
  );
}
